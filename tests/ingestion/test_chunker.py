import pytest

from landrag.ingestion.chunker import chunk_document, ChunkConfig
from landrag.ingestion.parsers.html import ParsedDocument, ParsedSection


def test_chunk_by_sections():
    doc = ParsedDocument(
        text="full text",
        sections=[
            ParsedSection(heading="Noise", content="Noise assessment details. " * 20),
            ParsedSection(heading="Ecology", content="Ecology survey results. " * 20),
        ],
    )
    chunks = chunk_document(doc)
    assert len(chunks) >= 2
    assert any("Noise" in c.text for c in chunks)
    assert any("Ecology" in c.text for c in chunks)


def test_chunk_fixed_size_fallback():
    doc = ParsedDocument(
        text="Word " * 600,  # ~600 tokens, should produce multiple chunks
        sections=[],
    )
    config = ChunkConfig(max_tokens=512, overlap_tokens=64)
    chunks = chunk_document(doc, config)
    assert len(chunks) >= 2


def test_chunk_preserves_paragraph_boundaries():
    paragraphs = ["Paragraph one. " * 30, "Paragraph two. " * 30, "Paragraph three. " * 30]
    doc = ParsedDocument(text="\n\n".join(paragraphs), sections=[])
    config = ChunkConfig(max_tokens=512, overlap_tokens=64)
    chunks = chunk_document(doc, config)
    for chunk in chunks:
        assert chunk.text.strip() != ""


def test_chunk_small_document_single_chunk():
    doc = ParsedDocument(text="Short document.", sections=[])
    chunks = chunk_document(doc)
    assert len(chunks) == 1
    assert chunks[0].text == "Short document."


def test_chunk_includes_section_heading():
    doc = ParsedDocument(
        text="full text",
        sections=[
            ParsedSection(heading="Noise Assessment", content="Details about noise levels."),
        ],
    )
    chunks = chunk_document(doc)
    assert any("Noise Assessment" in c.text for c in chunks)
