from fastapi.testclient import TestClient

from landrag.api.app import create_app


def test_home_serves_chat_page():
    app = create_app()
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert "landRAG" in response.text
