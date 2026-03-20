from landrag.models.schemas import ChunkResult


def _pages_overlap(a: ChunkResult, b: ChunkResult) -> bool:
    if a.page_start is None or a.page_end is None or b.page_start is None or b.page_end is None:
        return False
    return a.page_start <= b.page_end and b.page_start <= a.page_end


def deduplicate_chunks(chunks: list[ChunkResult]) -> list[ChunkResult]:
    sorted_chunks = sorted(chunks, key=lambda c: c.score, reverse=True)
    kept: list[ChunkResult] = []
    for chunk in sorted_chunks:
        is_duplicate = False
        for existing in kept:
            if chunk.document_title == existing.document_title and _pages_overlap(chunk, existing):
                is_duplicate = True
                break
        if not is_duplicate:
            kept.append(chunk)
    return kept
