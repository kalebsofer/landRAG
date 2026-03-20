from unittest.mock import patch

from fastapi.testclient import TestClient

from landrag.api.app import create_app


def _mock_chat_stream(*args, **kwargs):
    """Return an async generator that yields test SSE events."""

    async def _gen():
        import json

        source = json.dumps(
            [
                {
                    "ref": 1,
                    "chunk_id": "abc",
                    "document_title": "Test Doc",
                    "document_type": "decision_letter",
                    "project_name": "Test",
                    "project_reference": "EN010099",
                    "project_type": "onshore_wind",
                    "topic": "noise",
                    "source_url": "https://example.com",
                    "content": "Test content",
                    "score": 0.9,
                    "page_start": 1,
                    "page_end": 5,
                }
            ]
        )
        yield f"event: sources\ndata: {source}\n\n"
        yield 'event: token\ndata: {"text": "The noise"}\n\n'
        yield 'event: token\ndata: {"text": " conditions"}\n\n'
        yield 'event: done\ndata: {"suggested_filters": {}}\n\n'

    return _gen()


@patch("landrag.api.routes.chat.chat_stream", side_effect=_mock_chat_stream)
def test_chat_endpoint_streams_sse(mock_stream):
    app = create_app()
    client = TestClient(app)
    response = client.post(
        "/v1/chat",
        json={"message": "What noise conditions?"},
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    body = response.text
    assert "event: sources" in body
    assert "event: token" in body
    assert "event: done" in body


def test_chat_endpoint_rejects_empty_message():
    app = create_app()
    client = TestClient(app)
    response = client.post("/v1/chat", json={"message": ""})
    assert response.status_code == 422
