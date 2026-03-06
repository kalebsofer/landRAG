from unittest.mock import MagicMock, patch

from landrag.ingestion.embedder import embed_texts, embed_query


@patch("landrag.ingestion.embedder.get_openai_client")
def test_embed_texts_returns_vectors(mock_get_client):
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.data = [
        MagicMock(embedding=[0.1] * 3072, index=0),
        MagicMock(embedding=[0.2] * 3072, index=1),
    ]
    mock_client.embeddings.create.return_value = mock_response
    mock_get_client.return_value = mock_client

    results = embed_texts(["text one", "text two"])
    assert len(results) == 2
    assert len(results[0]) == 3072
    mock_client.embeddings.create.assert_called_once()


@patch("landrag.ingestion.embedder.get_openai_client")
def test_embed_query_returns_single_vector(mock_get_client):
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.data = [MagicMock(embedding=[0.5] * 3072, index=0)]
    mock_client.embeddings.create.return_value = mock_response
    mock_get_client.return_value = mock_client

    result = embed_query("noise conditions on wind farms")
    assert len(result) == 3072


@patch("landrag.ingestion.embedder.get_openai_client")
def test_embed_texts_batches_large_input(mock_get_client):
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.data = [MagicMock(embedding=[0.1] * 3072, index=i) for i in range(100)]
    mock_client.embeddings.create.return_value = mock_response
    mock_get_client.return_value = mock_client

    texts = [f"text {i}" for i in range(100)]
    results = embed_texts(texts)
    assert len(results) == 100
