import pytest

from landrag.core.config import Settings


@pytest.fixture
def settings() -> Settings:
    return Settings(
        database_url="postgresql+asyncpg://landrag:landrag@localhost:5432/landrag_test",
        database_url_sync="postgresql+psycopg2://landrag:landrag@localhost:5432/landrag_test",
        pinecone_api_key="test-key",
        pinecone_index_name="landrag-test",
        openai_api_key="test-key",
        cohere_api_key="test-key",
        anthropic_api_key="test-key",
    )
