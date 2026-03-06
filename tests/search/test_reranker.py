from unittest.mock import MagicMock, patch

from landrag.search.reranker import rerank


@patch("landrag.search.reranker.get_cohere_client")
def test_rerank_returns_reordered_results(mock_get_client):
    mock_client = MagicMock()
    mock_result_0 = MagicMock()
    mock_result_0.index = 1
    mock_result_0.relevance_score = 0.95
    mock_result_1 = MagicMock()
    mock_result_1.index = 0
    mock_result_1.relevance_score = 0.80
    mock_response = MagicMock()
    mock_response.results = [mock_result_0, mock_result_1]
    mock_client.rerank.return_value = mock_response
    mock_get_client.return_value = mock_client

    texts = ["text about ecology", "text about noise conditions"]
    results = rerank("noise conditions", texts, top_n=2)
    assert len(results) == 2
    assert results[0]["index"] == 1  # noise text ranked first
    assert results[0]["score"] == 0.95
