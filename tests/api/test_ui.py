from unittest.mock import patch

from fastapi.testclient import TestClient

from landrag.api.app import create_app


def test_home_page_renders():
    app = create_app()
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert "landRAG" in response.text
    assert "<form" in response.text


@patch("landrag.api.routes.ui.execute_search")
def test_search_page_renders_results(mock_search):
    mock_search.return_value = {
        "results": [
            {
                "chunk_id": "abc",
                "content": "Sample noise text",
                "score": 0.9,
                "highlight": "Sample noise text",
                "document_title": "Decision Letter",
                "document_type": "decision_letter",
                "project_name": "Wind Farm X",
                "project_reference": "EN010099",
                "project_type": "onshore_wind",
                "topic": "noise",
                "source_url": "https://example.com/doc.pdf",
                "page_start": 1,
                "page_end": 2,
            }
        ],
        "total_estimate": 1,
    }
    app = create_app()
    client = TestClient(app)
    response = client.get("/search?query=noise+conditions")
    assert response.status_code == 200
    assert "Wind Farm X" in response.text
    assert "noise" in response.text
