from landrag.core.config import Settings, get_settings


def test_settings_defaults():
    s = Settings(
        pinecone_api_key="k",
        openai_api_key="k",
        cohere_api_key="k",
        anthropic_api_key="k",
    )
    assert s.app_env == "development"
    assert s.pinecone_index_name == "landrag-dev"
    assert "5432" in s.database_url


def test_get_settings_returns_instance():
    s = get_settings()
    assert isinstance(s, Settings)
