from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from landrag.api.app import create_app


@patch("landrag.api.routes.corpus.get_async_session_factory")
def test_corpus_status_returns_sources(mock_factory):
    # Create the mock result with test data
    test_rows = [
        ("pins", 2341, datetime(2026, 3, 12, 14, 30, tzinfo=UTC)),
        ("lpa", 892, datetime(2026, 3, 10, 9, 15, tzinfo=UTC)),
    ]

    # Create the mock result object
    mock_result = MagicMock()
    mock_result.all.return_value = test_rows

    # Create the session with an async execute method
    mock_session = MagicMock()
    mock_session.execute = AsyncMock(return_value=mock_result)

    # Create a context manager mock for the session
    async_cm = MagicMock()
    async_cm.__aenter__ = AsyncMock(return_value=mock_session)
    async_cm.__aexit__ = AsyncMock(return_value=None)

    # The session_factory() call should return the context manager
    mock_session_factory = MagicMock(return_value=async_cm)
    mock_factory.return_value = mock_session_factory

    app = create_app()
    client = TestClient(app)
    response = client.get("/v1/corpus-status")
    assert response.status_code == 200
    data = response.json()
    assert "sources" in data
    assert "total_documents" in data
    assert data["total_documents"] == 3233
