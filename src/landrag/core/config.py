from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    # Database
    database_url: str = "postgresql+asyncpg://landrag:landrag@localhost:5432/landrag"
    database_url_sync: str = "postgresql+psycopg2://landrag:landrag@localhost:5432/landrag"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Pinecone
    pinecone_api_key: str = ""
    pinecone_index_name: str = "landrag-dev"

    # OpenAI
    openai_api_key: str = ""

    # Cohere
    cohere_api_key: str = ""

    # Anthropic
    anthropic_api_key: str = ""

    # GCS
    gcs_bucket_name: str = "landrag-documents"

    # App
    app_env: str = "development"
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()
