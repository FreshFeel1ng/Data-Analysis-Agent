import logging
import os
from typing import Optional, List
from pymilvus import MilvusClient, DataType
from app.config import settings

logger = logging.getLogger(__name__)

COLLECTION_NAME = settings.MILVUS_COLLECTION
DATABASE_NAME = settings.MILVUS_DATABASE

_LOCAL_DIM = 512
_OPENAI_DIM = 1536
_OLLAMA_DIM = 4096  # nomic-embed-text default


def _get_dimension() -> int:
    if settings.EMBEDDING_PROVIDER == "local":
        return settings.EMBEDDING_DIMENSION or _LOCAL_DIM
    elif settings.EMBEDDING_PROVIDER == "ollama":
        return settings.EMBEDDING_DIMENSION or _OLLAMA_DIM
    return _OPENAI_DIM


DIMENSION = _get_dimension()


class MilvusService:
    _instance: Optional["MilvusService"] = None
    _client: Optional[MilvusClient] = None
    _embeddings = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def _init_embeddings(self):
        if settings.EMBEDDING_PROVIDER == "local":
            # Use HF mirror for mainland China
            if not os.environ.get("HF_ENDPOINT"):
                os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

            from langchain_huggingface import HuggingFaceEmbeddings
            self._embeddings = HuggingFaceEmbeddings(
                model_name=settings.EMBEDDING_MODEL,
                model_kwargs={"device": "cpu"},
                encode_kwargs={"normalize_embeddings": True},
            )
            logger.info(f"Loaded local embedding model: {settings.EMBEDDING_MODEL}")
        elif settings.EMBEDDING_PROVIDER == "ollama":
            from langchain_ollama import OllamaEmbeddings
            self._embeddings = OllamaEmbeddings(
                model=settings.EMBEDDING_MODEL,
                base_url=settings.LLM_BASE_URL.replace("/v1", ""),
            )
            logger.info(f"Using Ollama embeddings: {settings.EMBEDDING_MODEL}")
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
            uri = f"http://{settings.MILVUS_HOST}:{settings.MILVUS_PORT}"
            self._client = MilvusClient(uri=uri, db_name=DATABASE_NAME)
            logger.info(f"Connected to Milvus at {uri}, db={DATABASE_NAME}")
            self._init_embeddings()
            self._ensure_collection()
            self._initialized = True
        except Exception as e:
            logger.warning(f"Milvus connection failed: {e}. Will operate without vector store.")
            self._initialized = True

    def _ensure_collection(self):
        if self._client.has_collection(COLLECTION_NAME):
            return
        schema = self._client.create_schema(enable_dynamic_field=False)
        schema.add_field("id", DataType.INT64, is_primary=True, auto_id=True)
        schema.add_field("question", DataType.VARCHAR, max_length=4096)
        schema.add_field("tool_name", DataType.VARCHAR, max_length=255)
        schema.add_field("tool_params", DataType.VARCHAR, max_length=8192)
        schema.add_field("user_id", DataType.INT64)
        schema.add_field("username", DataType.VARCHAR, max_length=255)
        schema.add_field("success", DataType.BOOL)
        schema.add_field("created_at", DataType.VARCHAR, max_length=64)
        schema.add_field("embedding", DataType.FLOAT_VECTOR, dim=DIMENSION)

        index_params = self._client.prepare_index_params()
        index_params.add_index(field_name="embedding", index_type="IVF_FLAT", metric_type="COSINE", params={"nlist": 128})

        self._client.create_collection(
            collection_name=COLLECTION_NAME,
            schema=schema,
            index_params=index_params,
            description="Tool usage examples",
        )
        logger.info(f"Milvus collection '{COLLECTION_NAME}' created")

    async def store_tool_usage(
        self,
        question: str,
        tool_name: str,
        tool_params: dict,
        user_id: int,
        username: str,
        success: bool = True,
    ):
        try:
            self._connect()
            if self._embeddings is None or self._client is None:
                return

            embedding = await self._embeddings.aembed_query(question)

            import json
            from datetime import datetime

            data = [{
                "question": question,
                "tool_name": tool_name,
                "tool_params": json.dumps(tool_params, ensure_ascii=False),
                "user_id": user_id,
                "username": username,
                "success": success,
                "created_at": datetime.now().isoformat(),
                "embedding": embedding,
            }]
            self._client.insert(collection_name=COLLECTION_NAME, data=data)
            logger.info(f"Stored tool usage in Milvus: {tool_name}")
        except Exception as e:
            logger.error(f"Failed to store in Milvus: {e}")

    async def search_similar_examples(
        self, question: str, top_k: int = 5
    ) -> List[dict]:
        try:
            self._connect()
            if self._embeddings is None or self._client is None:
                return []

            embedding = await self._embeddings.aembed_query(question)
            results = self._client.search(
                collection_name=COLLECTION_NAME,
                data=[embedding],
                limit=top_k,
                output_fields=["question", "tool_name", "tool_params", "success"],
            )

            examples = []
            for hits in results:
                for hit in hits:
                    entity = hit.get("entity", {})
                    if entity.get("success"):
                        examples.append({
                            "question": entity.get("question"),
                            "tool_name": entity.get("tool_name"),
                            "tool_params": entity.get("tool_params"),
                            "score": hit.get("distance", 0),
                        })
            return examples
        except Exception as e:
            logger.error(f"Milvus search failed: {e}")
            return []


milvus_service = MilvusService()
