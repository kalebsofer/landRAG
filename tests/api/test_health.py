from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from landrag.api.app import create_app


def test_health_endpoint():
    app = create_app()
    client = TestClient(app)

    # Mock get_sync_engine so the health check sees a working DB
    mock_engine = MagicMock()
    mock_conn = MagicMock()
    mock_conn.__enter__ = MagicMock(return_value=mock_conn)
    mock_conn.__exit__ = MagicMock(return_value=False)
    mock_conn.execute.return_value = None
    mock_engine.connect.return_value = mock_conn

    with patch("landrag.api.routes.health.get_sync_engine", return_value=mock_engine):
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["database"] == "ok"


def test_cors_headers_present():
    """Preflight OPTIONS request should return CORS headers."""
    client = TestClient(create_app())
    response = client.options(
        "/health",
        headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "GET"},
    )
    assert response.headers.get("access-control-allow-origin") is not None


def test_health_returns_db_status():
    """Health endpoint should report database connectivity."""
    client = TestClient(create_app())

    # Mock the sync engine to simulate a working DB
    mock_engine = MagicMock()
    mock_conn = MagicMock()
    mock_conn.__enter__ = MagicMock(return_value=mock_conn)
    mock_conn.__exit__ = MagicMock(return_value=False)
    mock_conn.execute.return_value = None
    mock_engine.connect.return_value = mock_conn

    with patch("landrag.api.routes.health.get_sync_engine", return_value=mock_engine):
        response = client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert "database" in data
    assert data["database"] == "ok"


def test_health_reports_db_failure():
    """Health endpoint should report database failure gracefully."""
    client = TestClient(create_app())

    with patch(
        "landrag.api.routes.health.get_sync_engine",
        side_effect=Exception("connection refused"),
    ):
        response = client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "degraded"
    assert data["database"] == "error"
