from unittest.mock import MagicMock, patch

from landrag.ingestion.parsers.pdf import PdfQualityResult, extract_pdf


def _mock_pdf_reader(pages: list[str]):
    reader = MagicMock()
    mock_pages = []
    for text in pages:
        page = MagicMock()
        page.extract_text.return_value = text
        mock_pages.append(page)
    reader.pages = mock_pages
    return reader


@patch("landrag.ingestion.parsers.pdf.PdfReader")
def test_extract_pdf_native(mock_reader_cls):
    mock_reader_cls.return_value = _mock_pdf_reader(["Page one content.", "Page two content."])
    result = extract_pdf("/fake/path.pdf")
    assert "Page one content." in result.text
    assert "Page two content." in result.text
    assert result.page_count == 2


@patch("landrag.ingestion.parsers.pdf.PdfReader")
def test_extract_pdf_detects_low_quality(mock_reader_cls):
    mock_reader_cls.return_value = _mock_pdf_reader(["", "  ", "x"])
    result = extract_pdf("/fake/path.pdf")
    assert result.quality == PdfQualityResult.LOW


@patch("landrag.ingestion.parsers.pdf.PdfReader")
def test_extract_pdf_good_quality(mock_reader_cls):
    mock_reader_cls.return_value = _mock_pdf_reader(["A" * 200, "B" * 200])
    result = extract_pdf("/fake/path.pdf")
    assert result.quality == PdfQualityResult.GOOD
