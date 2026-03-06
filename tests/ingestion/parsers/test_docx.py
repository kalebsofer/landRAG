from unittest.mock import MagicMock, patch

from landrag.ingestion.parsers.docx import extract_docx


def _mock_docx_document(paragraphs: list[tuple[str, str]]):
    """paragraphs: list of (style_name, text) tuples"""
    doc = MagicMock()
    mock_paras = []
    for style_name, text in paragraphs:
        para = MagicMock()
        para.text = text
        para.style.name = style_name
        mock_paras.append(para)
    doc.paragraphs = mock_paras
    return doc


@patch("landrag.ingestion.parsers.docx.DocxDocument")
def test_extract_docx_basic(mock_docx_cls):
    mock_docx_cls.return_value = _mock_docx_document([
        ("Normal", "First paragraph."),
        ("Normal", "Second paragraph."),
    ])
    result = extract_docx("/fake/path.docx")
    assert "First paragraph." in result.text
    assert "Second paragraph." in result.text


@patch("landrag.ingestion.parsers.docx.DocxDocument")
def test_extract_docx_with_headings(mock_docx_cls):
    mock_docx_cls.return_value = _mock_docx_document([
        ("Heading 1", "Section One"),
        ("Normal", "Content of section one."),
        ("Heading 1", "Section Two"),
        ("Normal", "Content of section two."),
    ])
    result = extract_docx("/fake/path.docx")
    assert len(result.sections) == 2
    assert result.sections[0].heading == "Section One"
