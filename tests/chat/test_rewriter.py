import json
from unittest.mock import MagicMock, patch

import pytest

from landrag.chat.rewriter import rewrite_query
from landrag.core.config import get_settings
from landrag.models.schemas import ChatMessage


@pytest.fixture(autouse=True)
def _clear_settings_cache():
    """Clear lru_cache on get_settings so tests pick up new fields."""
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _mock_anthropic_response(text: str):
    mock_response = MagicMock()
    mock_content = MagicMock()
    mock_content.text = text
    mock_response.content = [mock_content]
    return mock_response


@patch("landrag.chat.rewriter.Anthropic")
def test_rewrite_resolves_pronouns(mock_anthropic_cls):
    mock_client = MagicMock()
    mock_anthropic_cls.return_value = mock_client
    mock_client.messages.create.return_value = _mock_anthropic_response(
        json.dumps(
            {"query": "noise conditions Hornsea Project Three", "filters": {"topic": ["noise"]}}
        )
    )
    history = [
        ChatMessage(role="user", content="Tell me about Hornsea Project Three"),
        ChatMessage(role="assistant", content="Hornsea Three is an offshore wind farm..."),
    ]
    result = rewrite_query("What about noise conditions?", history)
    assert result["query"] == "noise conditions Hornsea Project Three"
    assert result["filters"]["topic"] == ["noise"]


@patch("landrag.chat.rewriter.Anthropic")
def test_rewrite_with_empty_history(mock_anthropic_cls):
    mock_client = MagicMock()
    mock_anthropic_cls.return_value = mock_client
    mock_client.messages.create.return_value = _mock_anthropic_response(
        json.dumps(
            {
                "query": "offshore wind noise limits",
                "filters": {"project_type": ["offshore_wind"], "topic": ["noise"]},
            }
        )
    )
    result = rewrite_query("offshore wind noise limits", [])
    assert result["query"] == "offshore wind noise limits"


@patch("landrag.chat.rewriter.Anthropic")
def test_rewrite_fallback_on_malformed_json(mock_anthropic_cls):
    mock_client = MagicMock()
    mock_anthropic_cls.return_value = mock_client
    mock_client.messages.create.return_value = _mock_anthropic_response("not valid json {{{")
    result = rewrite_query("test query", [])
    assert result["query"] == "test query"
    assert result["filters"] == {}
