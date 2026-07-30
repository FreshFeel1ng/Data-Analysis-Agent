from pydantic_settings import BaseSettings
from typing import Optional, Literal


class Settings(BaseSettings):
    APP_NAME: str = "DataAnalysisAgent"
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    ALGORITHM: str = "HS256"

    # PostgreSQL (app data)
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "data_agent"

    # Milvus
    MILVUS_HOST: str = "localhost"
    MILVUS_PORT: int = 19530
    MILVUS_DATABASE: str = "tool_usage"
    MILVUS_COLLECTION: str = "tool_usage"

    # LLM Provider: deepseek | openai
    LLM_PROVIDER: Literal["deepseek", "openai"] = "deepseek"
    LLM_MODEL: str = "deepseek-chat"
    LLM_API_KEY: str = ""
    LLM_BASE_URL: str = "https://api.deepseek.com/v1"
    LLM_TEMPERATURE: float = 0.0
    LLM_MAX_TOKENS: int = 8192

    # Embedding Provider: local | openai
    EMBEDDING_PROVIDER: Literal["local", "openai"] = "local"
    EMBEDDING_MODEL: str = "BAAI/bge-small-zh-v1.5"

    # OpenAI (fallback/compat)
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o"

    LOG_LEVEL: str = "INFO"

    @property
    def postgres_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def effective_api_key(self) -> str:
        return self.LLM_API_KEY or self.OPENAI_API_KEY

    class Config:
        env_file = ".env"
        extra = "allow"


settings = Settings()
