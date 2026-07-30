import logging
from typing import Optional, List
from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType, utility
from app.config import settings

logger = logging.getLogger(__name__)

COLLECTION_NAME = settings.MILVUS_COLLECTION

# Embedding dimension: local bge-small-zh = 512, OpenAI ada-002 = 1536
_LOCAL_DIM = 512
_OPENAI_DIM = 1536


def _get_dimension() -> int:
    return _LOCAL_DIM if settings.EMBEDDING_PROVIDER == "local" else _OPENAI_DIM


DIMENSION = _get_dimension()


class MilvusService:
    _instance: Optional["MilvusService"] = None
    _embeddings = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def _init_embeddings(self):
        if settings.EMBEDDING_PROVIDER == "local":
            from langchain_huggingface import HuggingFaceEmbeddings
            self._embeddings = HuggingFaceEmbeddings(
                model_name=settings.EMBEDDING_MODEL,
                model_kwargs={"device": "cpu"},
                encode_kwargs={"normalize_embeddings": True},
            )
            logger.info(f"Loaded local embedding model: {settings.EMBEDDING_MODEL}")
        else:
            from langchain_openai import OpenAIEmbeddings
            api_key = settings.LLM_API_KEY or settings.OPENAI_API_KEY
            self._embeddings = OpenAIEmbeddings(
                model="text-embedding-ada-002",
                openai_api_key=api_key,
                dimensions=_OPENAI_DIM,
            )
            logger.info("Using OpenAI embeddings (text-embedding-ada-002)")

    def _connect(self):
        if self._initialized:
            return
        try:
            connections.connect(host=settings.MILVUS_HOST, port=str(settings.MILVUS_PORT))
            logger.info(f"Connected to Milvus at {settings.MILVUS_HOST}:{settings.MILVUS_PORT}")
            self._init_embeddings()
            self._ensure_collection()
            self._initialized = True
        except Exception as e:
            logger.warning(f"Milvus connection failed: {e}. Will operate without vector store.")
            self._initialized = True

    def _ensure_collection(self):
        if utility.has_collection(COLLECTION_NAME):
            return
        fields = [
            FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
            FieldSchema(name="question", dtype=DataType.VARCHAR, max_length=4096),
            FieldSchema(name="tool_name", dtype=DataType.VARCHAR, max_length=255),
            FieldSchema(name="tool_params", dtype=DataType.VARCHAR, max_length=8192),
            FieldSchema(name="user_id", dtype=DataType.INT64),
            FieldSchema(name="username", dtype=DataType.VARCHAR, max_length=255),
            FieldSchema(name="success", dtype=DataType.BOOL),
            FieldSchema(name="created_at", dtype=DataType.VARCHAR, max_length=64),
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=DIMENSION),
        ]
        schema = CollectionSchema(fields, description="Tool usage examples")
        Collection(name=COLLECTION_NAME, schema=schema)
        logger.info(f"Milvus collection '{COLLECTION_NAME}' created")

    def _get_collection(self) -> Collection:
        self._connect()
        return Collection(name=COLLECTION_NAME)

    async def store_tool_usage(
        self,
        question: str,
        tool_name: str,
        tool_params: dict,
        user_id: int,
        username: str,
        success: bool = True,
    ):
        """Store successful tool usage as a vector example."""
        try:
            self._connect()
            if self._embeddings is None:
                return

            embedding = await self._embeddings.aembed_query(question)
            collection = self._get_collection()

            import json
            from datetime import datetime

            data = [
                [question],
                [tool_name],
                [json.dumps(tool_params, ensure_ascii=False)],
                [user_id],
                [username],
                [success],
                [datetime.now().isoformat()],
                [embedding],
            ]
            collection.insert(data)
            collection.flush()
            logger.info(f"Stored tool usage in Milvus: {tool_name}")
        except Exception as e:
            logger.error(f"Failed to store in Milvus: {e}")

    async def search_similar_examples(
        self, question: str, top_k: int = 5
    ) -> List[dict]:
        """Search for similar past tool usages by semantic similarity."""
        try:
            self._connect()
            if self._embeddings is None:
                return []

            embedding = await self._embeddings.aembed_query(question)
            collection = self._get_collection()

            collection.load()
            search_params = {"metric_type": "COSINE", "params": {"nprobe": 10}}
            results = collection.search(
                data=[embedding],
                anns_field="embedding",
                param=search_params,
                limit=top_k,
                output_fields=["question", "tool_name", "tool_params", "success"],
            )

            examples = []
            for hits in results:
                for hit in hits:
                    if hit.entity.get("success"):
                        examples.append({
                            "question": hit.entity.get("question"),
                            "tool_name": hit.entity.get("tool_name"),
                            "tool_params": hit.entity.get("tool_params"),
                            "score": float(hit.distance),
                        })
            return examples
        except Exception as e:
            logger.error(f"Milvus search failed: {e}")
            return []


milvus_service = MilvusService()
