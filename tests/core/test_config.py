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


def test_get_settings_is_cached():
    """get_settings() should return the same instance on repeated calls."""
    from landrag.core.config import get_settings

    s1 = get_settings()
    s2 = get_settings()
    assert s1 is s2
