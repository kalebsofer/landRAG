from unittest.mock import patch, MagicMock, mock_open

from landrag.workers.tasks import parse_document


@patch("landrag.workers.tasks.extract_pdf")
def test_parse_document_calls_pdf_parser(mock_extract):
    mock_extract.return_value = MagicMock(text="Extracted text", sections=[], page_count=5)
    result = parse_document("/fake/path.pdf", "pdf")
    mock_extract.assert_called_once_with("/fake/path.pdf")
    assert result["text"] == "Extracted text"
    assert result["page_count"] == 5


@patch("landrag.workers.tasks.extract_html")
def test_parse_document_calls_html_parser(mock_extract):
    mock_extract.return_value = MagicMock(text="HTML content", sections=[], page_count=None)
    with patch("builtins.open", mock_open(read_data="<html>content</html>")):
        result = parse_document("/fake/path.html", "html")
    mock_extract.assert_called_once()
    assert result["text"] == "HTML content"
