from landrag.ingestion.parsers.html import extract_html


def test_extract_html_basic():
    html = "<html><body><h1>Title</h1><p>Paragraph one.</p><p>Paragraph two.</p></body></html>"
    result = extract_html(html)
    assert "Title" in result.text
    assert "Paragraph one." in result.text
    assert "Paragraph two." in result.text


def test_extract_html_strips_scripts_and_styles():
    html = "<html><head><style>body{color:red}</style></head><body><script>alert(1)</script><p>Content</p></body></html>"
    result = extract_html(html)
    assert "alert" not in result.text
    assert "color:red" not in result.text
    assert "Content" in result.text


def test_extract_html_preserves_structure():
    html = "<html><body><h2>Section 1</h2><p>Text.</p><h2>Section 2</h2><p>More text.</p></body></html>"
    result = extract_html(html)
    assert result.sections is not None
    assert len(result.sections) >= 2
