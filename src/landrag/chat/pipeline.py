import asyncio
import logging
from collections.abc import AsyncGenerator

from anthropic import Anthropic

from landrag.chat.dedup import deduplicate_chunks
from landrag.chat.prompt import build_messages, build_system_prompt
from landrag.chat.rewriter import merge_filters, rewrite_query
from landrag.chat.streaming import format_sse_event
from landrag.core.config import get_settings
from landrag.models.schemas import ChatMessage, ChunkResult, SearchFilters, SourceResult
from landrag.search.retrieval import execute_search_pipeline

logger = logging.getLogger(__name__)


def _to_chunk_results(raw_results: list[dict]) -> list[ChunkResult]:
    """Convert raw search results dicts to ChunkResult models."""
    results = []
    for r in raw_results:
        # Pinecone may return empty string for topic — normalize to None
        if not r.get("topic"):
            r["topic"] = None
        results.append(ChunkResult(**r))
    return results


def _to_source_results(chunks: list[ChunkResult]) -> list[dict]:
    """Convert ChunkResults to numbered source result dicts for the SSE event."""
    return [
        SourceResult(
            ref=i,
            chunk_id=c.chunk_id,
            content=c.content,
            score=c.score,
            document_title=c.document_title,
            document_type=c.document_type,
            project_name=c.project_name,
            project_reference=c.project_reference,
            project_type=c.project_type,
            topic=c.topic,
            source_url=c.source_url,
            page_start=c.page_start,
            page_end=c.page_end,
        ).model_dump()
        for i, c in enumerate(chunks, 1)
    ]


async def chat_stream(
    message: str,
    history: list[ChatMessage] | None = None,
    explicit_filters: dict | None = None,
) -> AsyncGenerator[str, None]:
    """Run the full RAG chat pipeline, yielding SSE events."""
    settings = get_settings()
    history = history or []

    # Step 1-2: Query rewriting
    yield format_sse_event("status", {"text": "Understanding your question..."})
    rewrite_result = await asyncio.to_thread(rewrite_query, message, history)
    rewritten_query = rewrite_result["query"]
    suggested_filters = rewrite_result["filters"]

    # Step 3: Merge filters
    merged = merge_filters(explicit_filters or {}, suggested_filters)
    # Ensure all filter values are lists (rewriter may return scalars)
    for key, val in list(merged.items()):
        if val is not None and not isinstance(val, list):
            merged[key] = [val]
    search_filters = SearchFilters(**merged) if merged else None

    # Step 3: Retrieve
    yield format_sse_event("status", {"text": "Searching planning documents..."})
    raw = await asyncio.to_thread(
        execute_search_pipeline, rewritten_query, search_filters, 10
    )
    raw_results = raw["results"]

    # Step 4: Deduplicate
    chunks = _to_chunk_results(raw_results)
    chunks = deduplicate_chunks(chunks)
    chunks = chunks[:5]  # top 5 for generation

    # Step 5: Emit sources
    yield format_sse_event("status", {"text": f"Found {len(chunks)} relevant sources"})
    source_dicts = _to_source_results(chunks)
    yield format_sse_event("sources", source_dicts)

    # Step 6: Generate with streaming
    if not chunks:
        yield format_sse_event(
            "token",
            {
                "text": "I couldn't find relevant planning documents for that query. "
                "Try broadening your search or adjusting filters."
            },
        )
        yield format_sse_event("done", {"suggested_filters": suggested_filters})
        return

    yield format_sse_event("status", {"text": "Generating response..."})
    system_prompt = build_system_prompt(chunks)
    messages = build_messages(history, message)

    client = Anthropic(api_key=settings.anthropic_api_key)

    try:
        with client.messages.stream(
            model=settings.chat_model,
            max_tokens=settings.chat_max_tokens,
            system=system_prompt,
            messages=messages,
        ) as stream:
            for text in stream.text_stream:
                yield format_sse_event("token", {"text": text})
    except Exception:
        logger.exception("LLM streaming failed")
        yield format_sse_event(
            "error",
            {"message": "Failed to generate a response. Sources are shown above for reference."},
        )

    # Step 7: Done
    yield format_sse_event("done", {"suggested_filters": suggested_filters})
