from landrag.core.config import Settings, get_settings


def test_settings_defaults(monkeypatch):
    # Prevent pydantic-settings from reading .env so we test true defaults
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("PINECONE_INDEX_NAME", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    s = Settings(
        _env_file=None,
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


def test_chat_model_defaults(monkeypatch):
    monkeypatch.delenv("CHAT_MODEL", raising=False)
    monkeypatch.delenv("REWRITER_MODEL", raising=False)
    s = Settings(
        _env_file=None,
        pinecone_api_key="k",
        openai_api_key="k",
        cohere_api_key="k",
        anthropic_api_key="k",
    )
    assert s.chat_model == "claude-sonnet-4-20250514"
    assert s.chat_max_tokens == 4096
    assert s.rewriter_model == "claude-haiku-4-5-20251001"
