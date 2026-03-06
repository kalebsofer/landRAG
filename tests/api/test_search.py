from unittest.mock import patch

from fastapi.testclient import TestClient

from landrag.api.app import create_app


@patch("landrag.api.routes.search.execute_search")
def test_search_endpoint_returns_results(mock_search):
    mock_search.return_value = {
        "results": [
            {
                "chunk_id": "abc-123",
                "content": "Noise condition text",
                "score": 0.92,
                "highlight": "**Noise** condition text",
                "document_title": "Decision Letter",
                "document_type": "decision_letter",
                "project_name": "Test Wind Farm",
                "project_reference": "EN010099",
                "project_type": "onshore_wind",
                "topic": "noise",
                "source_url": "https://example.com/doc.pdf",
                "page_start": 12,
                "page_end": 13,
            }
        ],
        "total_estimate": 1,
    }

    app = create_app()
    client = TestClient(app)
    response = client.post("/v1/search", json={"query": "noise conditions on wind farms"})
    assert response.status_code == 200
    data = response.json()
    assert len(data["results"]) == 1
    assert data["results"][0]["chunk_id"] == "abc-123"


def test_search_endpoint_validates_empty_query():
    app = create_app()
    client = TestClient(app)
    response = client.post("/v1/search", json={"query": ""})
    assert response.status_code == 422


def test_search_endpoint_validates_limit():
    app = create_app()
    client = TestClient(app)
    response = client.post("/v1/search", json={"query": "test", "limit": 100})
    assert response.status_code == 422
