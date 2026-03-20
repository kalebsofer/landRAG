from landrag.chat.dedup import deduplicate_chunks
from landrag.models.schemas import ChunkResult


def _make_chunk(
    chunk_id: str, doc_title: str, page_start: int | None, page_end: int | None, score: float
) -> ChunkResult:
    return ChunkResult(
        chunk_id=chunk_id,
        content=f"Content for {chunk_id}",
        score=score,
        highlight=f"Content for {chunk_id}"[:200],
        document_title=doc_title,
        document_type="decision_letter",
        project_name="Test Project",
        project_reference="EN010099",
        project_type="onshore_wind",
        topic="noise",
        source_url="https://example.com/doc.pdf",
        page_start=page_start,
        page_end=page_end,
    )


def test_no_duplicates_passes_through():
    chunks = [
        _make_chunk("a", "Doc A", 1, 5, 0.9),
        _make_chunk("b", "Doc B", 10, 15, 0.8),
    ]
    result = deduplicate_chunks(chunks)
    assert len(result) == 2


def test_same_doc_overlapping_pages_keeps_highest_score():
    chunks = [
        _make_chunk("a", "Doc A", 1, 5, 0.9),
        _make_chunk("b", "Doc A", 3, 8, 0.7),
    ]
    result = deduplicate_chunks(chunks)
    assert len(result) == 1
    assert result[0].chunk_id == "a"


def test_same_doc_non_overlapping_pages_kept():
    chunks = [
        _make_chunk("a", "Doc A", 1, 5, 0.9),
        _make_chunk("b", "Doc A", 10, 15, 0.8),
    ]
    result = deduplicate_chunks(chunks)
    assert len(result) == 2


def test_none_pages_never_deduped():
    chunks = [
        _make_chunk("a", "Doc A", None, None, 0.9),
        _make_chunk("b", "Doc A", None, None, 0.8),
    ]
    result = deduplicate_chunks(chunks)
    assert len(result) == 2


def test_preserves_score_ordering():
    chunks = [
        _make_chunk("a", "Doc A", 1, 5, 0.9),
        _make_chunk("b", "Doc B", 1, 5, 0.95),
        _make_chunk("c", "Doc A", 3, 8, 0.7),
    ]
    result = deduplicate_chunks(chunks)
    assert len(result) == 2
    assert result[0].chunk_id == "b"
    assert result[1].chunk_id == "a"
