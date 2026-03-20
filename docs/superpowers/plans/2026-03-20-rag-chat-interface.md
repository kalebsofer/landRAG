# RAG Chat Interface Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the search page with a chat-first interface that streams cited answers from UK planning documents using the existing hybrid retrieval pipeline.

**Architecture:** New `src/landrag/chat/` package handles query rewriting (Haiku), filter merging, chunk deduplication, prompt building, and SSE streaming (Sonnet). A single Jinja2 template with vanilla JS handles the frontend. The existing retrieval functions are extracted from the route module into the search package for shared use.

**Tech Stack:** Python 3.12, FastAPI, Anthropic SDK (streaming), Jinja2, vanilla JS, marked.js, Pico CSS

**Spec:** `docs/superpowers/specs/2026-03-20-rag-chat-interface-design.md`

---

## File Structure

### New Files
| File | Responsibility |
|------|----------------|
| `src/landrag/chat/__init__.py` | Package init |
| `src/landrag/chat/dedup.py` | Chunk deduplication (same doc + overlapping pages) |
| `src/landrag/chat/rewriter.py` | Query rewriting + filter extraction via Haiku |
| `src/landrag/chat/prompt.py` | System prompt builder with source injection |
| `src/landrag/chat/streaming.py` | SSE event formatting helpers |
| `src/landrag/chat/pipeline.py` | RAG chat pipeline orchestration |
| `src/landrag/api/routes/chat.py` | `POST /v1/chat` SSE endpoint |
| `src/landrag/api/routes/corpus.py` | `GET /v1/corpus-status` endpoint |
| `src/landrag/templates/chat.html` | Chat UI (Jinja2 + vanilla JS) |
| `tests/chat/__init__.py` | Test package init |
| `tests/chat/test_dedup.py` | Dedup unit tests |
| `tests/chat/test_rewriter.py` | Rewriter unit tests |
| `tests/chat/test_prompt.py` | Prompt builder unit tests |
| `tests/chat/test_streaming.py` | SSE formatting tests |
| `tests/chat/test_filter_merge.py` | Filter merge logic tests |
| `tests/api/test_chat.py` | Chat endpoint integration tests |
| `tests/api/test_corpus.py` | Corpus status endpoint tests |

### Modified Files
| File | Change |
|------|--------|
| `src/landrag/core/config.py` | Add `chat_model`, `chat_max_tokens`, `rewriter_model` settings |
| `src/landrag/models/schemas.py` | Add `ChatMessage`, `ChatRequest`, `SourceResult`, `CorpusSourceStatus`, `CorpusStatusResponse` schemas |
| `src/landrag/search/retrieval.py` | Receive extracted `execute_search_pipeline()` function from route module |
| `src/landrag/api/routes/search.py` | Slim down to thin route calling `search.retrieval` |
| `src/landrag/api/routes/ui.py` | Replace search routes with chat page route |
| `src/landrag/api/app.py` | Register chat + corpus routers |
| `src/landrag/templates/base.html` | Update for chat-first layout |

### Removed Files
| File | Reason |
|------|--------|
| `src/landrag/templates/search.html` | Replaced by chat.html |
| `src/landrag/templates/results.html` | No longer needed |

---

## Task 1: Add Chat Config Settings

**Files:**
- Modify: `src/landrag/core/config.py:6-34`
- Test: `tests/core/test_config.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/core/test_config.py — append this test (follows existing pattern)

def test_chat_model_defaults(monkeypatch):
    monkeypatch.delenv("CHAT_MODEL", raising=False)
    monkeypatch.delenv("REWRITER_MODEL", raising=False)
    s = Settings(
        _env_file=None,
        pinecone_api_key="k",
        openai_api_key="k",
        cohere_api_key="k",
        anthropic_api_key="k",
    )
    assert s.chat_model == "claude-sonnet-4-20250514"
    assert s.chat_max_tokens == 4096
    assert s.rewriter_model == "claude-haiku-4-5-20251001"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/core/test_config.py::test_chat_model_defaults -v`
Expected: FAIL — `AttributeError: 'Settings' object has no attribute 'chat_model'`

- [ ] **Step 3: Write minimal implementation**

Add to `Settings` class in `src/landrag/core/config.py`:

```python
    # Chat
    chat_model: str = "claude-sonnet-4-20250514"
    chat_max_tokens: int = 4096
    rewriter_model: str = "claude-haiku-4-5-20251001"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/core/test_config.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add src/landrag/core/config.py tests/core/test_config.py
git commit -m "feat(config): add chat model settings"
```

---

## Task 2: Add Chat Pydantic Schemas

**Files:**
- Modify: `src/landrag/models/schemas.py`
- Test: `tests/models/test_schemas.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/models/test_schemas.py — append these tests

from landrag.models.schemas import ChatMessage, ChatRequest, SourceResult, CorpusSourceStatus, CorpusStatusResponse


def test_chat_message_schema():
    msg = ChatMessage(role="user", content="Hello")
    assert msg.role == "user"
    assert msg.content == "Hello"


def test_chat_message_rejects_invalid_role():
    import pytest
    with pytest.raises(ValueError):
        ChatMessage(role="system", content="Hello")


def test_chat_request_minimal():
    req = ChatRequest(message="What noise conditions?")
    assert req.message == "What noise conditions?"
    assert req.history == []
    assert req.filters is None


def test_chat_request_with_history_and_filters():
    req = ChatRequest(
        message="What about solar?",
        history=[ChatMessage(role="user", content="Hi"), ChatMessage(role="assistant", content="Hello")],
        filters={"project_type": ["solar"]},
    )
    assert len(req.history) == 2
    assert req.filters == {"project_type": ["solar"]}


def test_chat_request_rejects_empty_message():
    import pytest
    with pytest.raises(ValueError):
        ChatRequest(message="")


def test_source_result_schema():
    src = SourceResult(
        ref=1,
        chunk_id="abc-123",
        content="Noise text",
        score=0.92,
        document_title="Decision Letter",
        document_type="decision_letter",
        project_name="Test Wind Farm",
        project_reference="EN010099",
        project_type="onshore_wind",
        topic="noise",
        source_url="https://example.com/doc.pdf",
        page_start=12,
        page_end=13,
    )
    assert src.ref == 1
    assert src.chunk_id == "abc-123"


def test_corpus_status_response():
    resp = CorpusStatusResponse(
        sources=[CorpusSourceStatus(portal="pins", document_count=100, last_updated="2026-03-12T14:30:00Z")],
        total_documents=100,
    )
    assert len(resp.sources) == 1
    assert resp.total_documents == 100
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/models/test_schemas.py -v -k "chat or source_result or corpus_status"`
Expected: FAIL — `ImportError: cannot import name 'ChatMessage'`

- [ ] **Step 3: Write minimal implementation**

Append to `src/landrag/models/schemas.py`:

```python
from typing import Literal


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    history: list[ChatMessage] = Field(default_factory=list)
    filters: dict | None = None


class SourceResult(BaseModel):
    ref: int
    chunk_id: str
    content: str
    score: float
    document_title: str
    document_type: str
    project_name: str
    project_reference: str
    project_type: str
    topic: str | None = None
    source_url: str
    page_start: int | None = None
    page_end: int | None = None


class CorpusSourceStatus(BaseModel):
    portal: str
    document_count: int
    last_updated: str


class CorpusStatusResponse(BaseModel):
    sources: list[CorpusSourceStatus]
    total_documents: int
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/models/test_schemas.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add src/landrag/models/schemas.py tests/models/test_schemas.py
git commit -m "feat(schemas): add chat and corpus status schemas"
```

---

## Task 3: Chunk Deduplication

**Files:**
- Create: `src/landrag/chat/__init__.py`
- Create: `src/landrag/chat/dedup.py`
- Create: `tests/chat/__init__.py`
- Create: `tests/chat/test_dedup.py`

- [ ] **Step 1: Create package init files**

Create empty `src/landrag/chat/__init__.py` and `tests/chat/__init__.py`.

- [ ] **Step 2: Write the failing tests**

```python
# tests/chat/test_dedup.py

from landrag.chat.dedup import deduplicate_chunks
from landrag.models.schemas import ChunkResult


def _make_chunk(chunk_id: str, doc_title: str, page_start: int | None, page_end: int | None, score: float) -> ChunkResult:
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
        _make_chunk("b", "Doc A", 3, 8, 0.7),  # overlaps with a (pages 3-5)
    ]
    result = deduplicate_chunks(chunks)
    assert len(result) == 1
    assert result[0].chunk_id == "a"  # higher score kept


def test_same_doc_non_overlapping_pages_kept():
    chunks = [
        _make_chunk("a", "Doc A", 1, 5, 0.9),
        _make_chunk("b", "Doc A", 10, 15, 0.8),  # no overlap
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
        _make_chunk("c", "Doc A", 3, 8, 0.7),  # deduped against a
    ]
    result = deduplicate_chunks(chunks)
    assert len(result) == 2
    assert result[0].chunk_id == "b"  # highest score first
    assert result[1].chunk_id == "a"
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest tests/chat/test_dedup.py -v`
Expected: FAIL — `ImportError: cannot import name 'deduplicate_chunks'`

- [ ] **Step 4: Write minimal implementation**

```python
# src/landrag/chat/dedup.py

from landrag.models.schemas import ChunkResult


def _pages_overlap(a: ChunkResult, b: ChunkResult) -> bool:
    """Check if two chunks from the same document have overlapping page ranges."""
    if a.page_start is None or a.page_end is None or b.page_start is None or b.page_end is None:
        return False
    return a.page_start <= b.page_end and b.page_start <= a.page_end


def deduplicate_chunks(chunks: list[ChunkResult]) -> list[ChunkResult]:
    """Remove overlapping chunks from the same document, keeping the highest-scored."""
    # Sort by score descending so we keep the best chunk from each overlap group
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
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/chat/test_dedup.py -v`
Expected: ALL PASS

- [ ] **Step 6: Commit**

```bash
git add src/landrag/chat/__init__.py src/landrag/chat/dedup.py tests/chat/__init__.py tests/chat/test_dedup.py
git commit -m "feat(chat): add chunk deduplication"
```

---

## Task 4: Filter Merge Logic

**Files:**
- Create: `tests/chat/test_filter_merge.py`
- The merge function lives in `src/landrag/chat/rewriter.py` (created in Task 5), but we test it standalone first.

- [ ] **Step 1: Write the failing tests**

```python
# tests/chat/test_filter_merge.py

from landrag.chat.rewriter import merge_filters


def test_explicit_wins_over_suggested():
    explicit = {"project_type": ["onshore_wind"]}
    suggested = {"project_type": ["offshore_wind"], "topic": ["noise"]}
    result = merge_filters(explicit, suggested)
    assert result["project_type"] == ["onshore_wind"]
    assert result["topic"] == ["noise"]


def test_suggested_fills_empty_fields():
    explicit = {}
    suggested = {"topic": ["ecology"]}
    result = merge_filters(explicit, suggested)
    assert result["topic"] == ["ecology"]


def test_empty_explicit_list_not_treated_as_set():
    explicit = {"project_type": []}
    suggested = {"project_type": ["solar"]}
    result = merge_filters(explicit, suggested)
    # Empty list means "not set", so suggested wins
    assert result["project_type"] == ["solar"]


def test_both_empty_returns_empty():
    result = merge_filters({}, {})
    assert result == {}


def test_none_values_ignored():
    explicit = {"project_type": None}
    suggested = {"topic": None}
    result = merge_filters(explicit, suggested)
    assert result == {}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/chat/test_filter_merge.py -v`
Expected: FAIL — `ImportError: cannot import name 'merge_filters'`

- [ ] **Step 3: Write minimal implementation**

Create `src/landrag/chat/rewriter.py` with just the merge function for now (full rewriter in Task 5):

```python
# src/landrag/chat/rewriter.py

def merge_filters(explicit: dict, suggested: dict) -> dict:
    """Merge explicit user filters with LLM-suggested filters. Explicit wins per-field."""
    merged = {}
    all_keys = set(list(explicit.keys()) + list(suggested.keys()))
    for key in all_keys:
        if key in explicit and explicit[key]:
            merged[key] = explicit[key]
        elif key in suggested and suggested[key]:
            merged[key] = suggested[key]
    return merged
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/chat/test_filter_merge.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add src/landrag/chat/rewriter.py tests/chat/test_filter_merge.py
git commit -m "feat(chat): add filter merge logic"
```

---

## Task 5: Query Rewriter

**Files:**
- Modify: `src/landrag/chat/rewriter.py`
- Create: `tests/chat/test_rewriter.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/chat/test_rewriter.py

import json
from unittest.mock import MagicMock, patch

from landrag.chat.rewriter import rewrite_query
from landrag.models.schemas import ChatMessage


def _mock_anthropic_response(text: str):
    """Create a mock Anthropic messages.create response."""
    mock_response = MagicMock()
    mock_content = MagicMock()
    mock_content.text = text
    mock_response.content = [mock_content]
    return mock_response


@patch("landrag.chat.rewriter.Anthropic")
def test_rewrite_resolves_pronouns(mock_anthropic_cls):
    mock_client = MagicMock()
    mock_anthropic_cls.return_value = mock_client
    mock_client.messages.create.return_value = _mock_anthropic_response(
        json.dumps({"query": "noise conditions Hornsea Project Three", "filters": {"topic": ["noise"]}})
    )

    history = [
        ChatMessage(role="user", content="Tell me about Hornsea Project Three"),
        ChatMessage(role="assistant", content="Hornsea Three is an offshore wind farm..."),
    ]
    result = rewrite_query("What about noise conditions?", history)

    assert result["query"] == "noise conditions Hornsea Project Three"
    assert result["filters"]["topic"] == ["noise"]


@patch("landrag.chat.rewriter.Anthropic")
def test_rewrite_with_empty_history(mock_anthropic_cls):
    mock_client = MagicMock()
    mock_anthropic_cls.return_value = mock_client
    mock_client.messages.create.return_value = _mock_anthropic_response(
        json.dumps({"query": "offshore wind noise limits", "filters": {"project_type": ["offshore_wind"], "topic": ["noise"]}})
    )

    result = rewrite_query("offshore wind noise limits", [])
    assert result["query"] == "offshore wind noise limits"


@patch("landrag.chat.rewriter.Anthropic")
def test_rewrite_fallback_on_malformed_json(mock_anthropic_cls):
    mock_client = MagicMock()
    mock_anthropic_cls.return_value = mock_client
    mock_client.messages.create.return_value = _mock_anthropic_response("not valid json {{{")

    result = rewrite_query("test query", [])
    assert result["query"] == "test query"
    assert result["filters"] == {}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/chat/test_rewriter.py -v`
Expected: FAIL — `ImportError: cannot import name 'rewrite_query'`

- [ ] **Step 3: Write implementation**

Update `src/landrag/chat/rewriter.py` — add `rewrite_query` below the existing `merge_filters`:

```python
import json
import logging

from anthropic import Anthropic

from landrag.core.config import get_settings
from landrag.models.schemas import ChatMessage

logger = logging.getLogger(__name__)

REWRITE_PROMPT = """Given this conversation context and new message, produce:
1. A standalone search query (resolving pronouns and references to previous messages)
2. Any filters implied by the query

Valid filter keys (all values are lists of strings):
- project_type: onshore_wind, offshore_wind, solar, battery_storage, gas_peaker, transmission, hydrogen, ccus, other
- topic: noise, ecology, landscape, traffic, cultural_heritage, flood_risk, air_quality, socioeconomic, grid, cumulative_impact, decommissioning, construction
- document_type: decision_letter, eia_chapter, inspector_report, consultation_response, policy_statement, guidance
- decision: granted, refused, withdrawn, pending

Conversation context:
{context}

New message: {message}

Respond with ONLY valid JSON: {{"query": "...", "filters": {{"key": ["value"]}}}}"""


def rewrite_query(message: str, history: list[ChatMessage]) -> dict:
    """Rewrite a user message into a standalone search query with filter suggestions."""
    settings = get_settings()
    client = Anthropic(api_key=settings.anthropic_api_key)

    # Build context from last 3 turns
    context_turns = history[-6:]  # last 3 exchanges (user+assistant pairs)
    context = "\n".join(f"{m.role}: {m.content}" for m in context_turns) if context_turns else "(no prior context)"

    prompt = REWRITE_PROMPT.format(context=context, message=message)

    response = client.messages.create(
        model=settings.rewriter_model,
        max_tokens=200,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = response.content[0].text.strip()
    try:
        parsed = json.loads(raw)
        return {
            "query": parsed.get("query", message),
            "filters": parsed.get("filters", {}),
        }
    except (json.JSONDecodeError, KeyError, TypeError):
        logger.warning("Query rewriter returned malformed JSON: %s", raw)
        return {"query": message, "filters": {}}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/chat/test_rewriter.py tests/chat/test_filter_merge.py -v`
Expected: ALL PASS (both rewriter and existing merge tests)

- [ ] **Step 5: Commit**

```bash
git add src/landrag/chat/rewriter.py tests/chat/test_rewriter.py
git commit -m "feat(chat): add query rewriter with Haiku"
```

---

## Task 6: System Prompt Builder

**Files:**
- Create: `src/landrag/chat/prompt.py`
- Create: `tests/chat/test_prompt.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/chat/test_prompt.py

from landrag.chat.prompt import build_system_prompt, build_messages
from landrag.models.schemas import ChatMessage, ChunkResult


def _make_chunk(ref: int) -> ChunkResult:
    return ChunkResult(
        chunk_id=f"chunk-{ref}",
        content=f"Content for source {ref}. Important planning details here.",
        score=0.9,
        highlight=f"Content for source {ref}",
        document_title=f"Document {ref}",
        document_type="decision_letter",
        project_name="Test Project",
        project_reference="EN010099",
        project_type="onshore_wind",
        topic="noise",
        source_url="https://example.com/doc.pdf",
        page_start=ref * 10,
        page_end=ref * 10 + 5,
    )


def test_build_system_prompt_includes_sources():
    chunks = [_make_chunk(1), _make_chunk(2)]
    prompt = build_system_prompt(chunks)
    assert "[1]" in prompt
    assert "[2]" in prompt
    assert "Document 1" in prompt
    assert "Document 2" in prompt
    assert "EN010099" in prompt
    assert "Content for source 1" in prompt


def test_build_system_prompt_includes_rules():
    chunks = [_make_chunk(1)]
    prompt = build_system_prompt(chunks)
    assert "ONLY the source documents" in prompt
    assert "Cite every factual claim" in prompt


def test_build_system_prompt_empty_sources():
    prompt = build_system_prompt([])
    assert "No source documents" in prompt


def test_build_messages_structures_conversation():
    history = [
        ChatMessage(role="user", content="Hi"),
        ChatMessage(role="assistant", content="Hello"),
    ]
    messages = build_messages(history, "What about noise?")
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == "Hi"
    assert messages[1]["role"] == "assistant"
    assert messages[1]["content"] == "Hello"
    assert messages[-1]["role"] == "user"
    assert messages[-1]["content"] == "What about noise?"


def test_build_messages_empty_history():
    messages = build_messages([], "First question")
    assert len(messages) == 1
    assert messages[0]["content"] == "First question"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/chat/test_prompt.py -v`
Expected: FAIL — `ImportError: cannot import name 'build_system_prompt'`

- [ ] **Step 3: Write implementation**

```python
# src/landrag/chat/prompt.py

from landrag.models.schemas import ChatMessage, ChunkResult

SYSTEM_PROMPT_TEMPLATE = """You are landRAG, a research assistant for UK planning and environmental permitting documents. You answer questions using ONLY the source documents provided below.

Rules:
- Cite every factual claim using [n] references matching the source numbers
- If the sources don't contain enough information to answer, say so explicitly
- Never fabricate planning conditions, decisions, or document references
- When sources conflict, present both positions with their citations
- Use precise planning terminology (DCO, NSIP, NPS, EIA, etc.)
- For direct questions: be concise and specific
- For exploratory questions: synthesise across sources and highlight patterns

{sources_block}"""

NO_SOURCES_BLOCK = """Sources:
No source documents were found for this query. Inform the user that you couldn't find relevant documents and suggest they try different search terms or adjust their filters."""


def build_system_prompt(chunks: list[ChunkResult]) -> str:
    """Build the system prompt with numbered source chunks."""
    if not chunks:
        return SYSTEM_PROMPT_TEMPLATE.format(sources_block=NO_SOURCES_BLOCK)

    source_lines = ["Sources:"]
    for i, chunk in enumerate(chunks, 1):
        page_range = ""
        if chunk.page_start is not None and chunk.page_end is not None:
            page_range = f", pp. {chunk.page_start}-{chunk.page_end}"
        elif chunk.page_start is not None:
            page_range = f", p. {chunk.page_start}"

        header = f"[{i}] {chunk.document_title} ({chunk.project_reference}, {chunk.document_type}{page_range})"
        source_lines.append(header)
        source_lines.append(chunk.content)
        source_lines.append("")

    return SYSTEM_PROMPT_TEMPLATE.format(sources_block="\n".join(source_lines))


def build_messages(history: list[ChatMessage], current_message: str) -> list[dict]:
    """Build the messages array for the Anthropic API call."""
    messages = [{"role": m.role, "content": m.content} for m in history]
    messages.append({"role": "user", "content": current_message})
    return messages
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/chat/test_prompt.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add src/landrag/chat/prompt.py tests/chat/test_prompt.py
git commit -m "feat(chat): add system prompt builder"
```

---

## Task 7: SSE Streaming Helpers

**Files:**
- Create: `src/landrag/chat/streaming.py`
- Create: `tests/chat/test_streaming.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/chat/test_streaming.py

from landrag.chat.streaming import format_sse_event


def test_format_sources_event():
    sources = [{"ref": 1, "document_title": "Doc A"}]
    event = format_sse_event("sources", sources)
    assert event.startswith("event: sources\n")
    assert "data: " in event
    assert '"ref": 1' in event
    assert event.endswith("\n\n")


def test_format_token_event():
    event = format_sse_event("token", {"text": "Hello"})
    assert event == 'event: token\ndata: {"text": "Hello"}\n\n'


def test_format_done_event():
    event = format_sse_event("done", {"suggested_filters": {}})
    assert event.startswith("event: done\n")
    assert event.endswith("\n\n")


def test_format_error_event():
    event = format_sse_event("error", {"message": "Something went wrong"})
    assert event.startswith("event: error\n")
    assert "Something went wrong" in event
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/chat/test_streaming.py -v`
Expected: FAIL — `ImportError: cannot import name 'format_sse_event'`

- [ ] **Step 3: Write implementation**

```python
# src/landrag/chat/streaming.py

import json


def format_sse_event(event_type: str, data: dict | list) -> str:
    """Format data as a Server-Sent Event string."""
    return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/chat/test_streaming.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add src/landrag/chat/streaming.py tests/chat/test_streaming.py
git commit -m "feat(chat): add SSE streaming helpers"
```

---

## Task 8: Extract Retrieval Logic to Search Package

**Files:**
- Modify: `src/landrag/search/retrieval.py`
- Modify: `src/landrag/api/routes/search.py`
- Test: `tests/search/test_retrieval.py` (existing tests must still pass)
- Test: `tests/api/test_search.py` (existing tests must still pass)

- [ ] **Step 1: Move `execute_search` logic into search package**

Add to `src/landrag/search/retrieval.py` (below existing `bm25_rescore` and `combine_scores`):

```python
from landrag.core.pinecone import build_metadata_filter, get_pinecone_index
from landrag.ingestion.embedder import embed_query
from landrag.search.reranker import rerank


def execute_search_pipeline(query: str, filters=None, limit: int = 10) -> dict:
    """Execute the full search pipeline: embed → Pinecone → BM25 → rerank.

    This is the shared retrieval function used by both the search API and chat pipeline.
    """
    # 1. Embed query
    query_embedding = embed_query(query)

    # 2. Pinecone search
    index = get_pinecone_index()
    pinecone_filter = build_metadata_filter(filters)
    pinecone_results = index.query(
        vector=query_embedding,
        top_k=20,
        include_metadata=True,
        filter=pinecone_filter if pinecone_filter else None,
    )

    if not pinecone_results.matches:
        return {"results": [], "total_estimate": 0}

    # 3. Extract texts and dense scores
    texts = [m.metadata.get("text", "") for m in pinecone_results.matches]
    dense_scores = [m.score for m in pinecone_results.matches]
    chunk_ids = [m.id for m in pinecone_results.matches]

    # 4. BM25 re-score
    bm25_scores_list = bm25_rescore(texts, query)

    # 5. Combine scores
    combine_scores(dense_scores, bm25_scores_list)

    # 6. Rerank top candidates
    reranked = rerank(query, texts, top_n=limit)

    # 7. Build response
    results = []
    for r in reranked:
        idx = r["index"]
        match = pinecone_results.matches[idx]
        meta = match.metadata
        results.append(
            {
                "chunk_id": chunk_ids[idx],
                "content": texts[idx],
                "score": r["score"],
                "highlight": texts[idx][:200],
                "document_title": meta.get("document_title", ""),
                "document_type": meta.get("document_type", ""),
                "project_name": meta.get("project_name", ""),
                "project_reference": meta.get("project_reference", ""),
                "project_type": meta.get("project_type", ""),
                "topic": meta.get("topic"),
                "source_url": meta.get("source_url", ""),
                "page_start": meta.get("page_start"),
                "page_end": meta.get("page_end"),
            }
        )

    return {"results": results, "total_estimate": len(results)}
```

- [ ] **Step 2: Slim down the route to call the shared function**

Replace `src/landrag/api/routes/search.py`:

```python
from fastapi import APIRouter

from landrag.models.schemas import SearchRequest
from landrag.search.retrieval import execute_search_pipeline

router = APIRouter(prefix="/v1")


def execute_search(request: SearchRequest) -> dict:
    """Thin wrapper for backward compatibility."""
    return execute_search_pipeline(request.query, request.filters, request.limit)


@router.post("/search")
async def search(request: SearchRequest) -> dict:
    return execute_search(request)
```

- [ ] **Step 3: Run all existing tests to verify nothing broke**

Run: `pytest tests/search/test_retrieval.py tests/api/test_search.py tests/api/test_ui.py -v`
Expected: ALL PASS

- [ ] **Step 4: Commit**

```bash
git add src/landrag/search/retrieval.py src/landrag/api/routes/search.py
git commit -m "refactor: extract search pipeline to search package"
```

---

## Task 9: Chat Pipeline Orchestration

**Files:**
- Create: `src/landrag/chat/pipeline.py`
- No separate test file — the pipeline is an async generator that wires together the other tested components. It's tested through the endpoint integration test in Task 11.

- [ ] **Step 1: Write the pipeline**

```python
# src/landrag/chat/pipeline.py

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
    return [ChunkResult(**r) for r in raw_results]


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
    history: list[ChatMessage],
    explicit_filters: dict | None = None,
) -> AsyncGenerator[str, None]:
    """Run the full RAG chat pipeline, yielding SSE events."""
    settings = get_settings()

    # Step 1-2: Query rewriting (runs in thread to avoid blocking)
    rewrite_result = await asyncio.to_thread(rewrite_query, message, history)
    rewritten_query = rewrite_result["query"]
    suggested_filters = rewrite_result["filters"]

    # Step 3: Merge filters
    merged = merge_filters(explicit_filters or {}, suggested_filters)
    search_filters = SearchFilters(**merged) if merged else None

    # Step 3: Retrieve (runs in thread)
    raw = await asyncio.to_thread(
        execute_search_pipeline, rewritten_query, search_filters, 10
    )
    raw_results = raw["results"]

    # Step 4: Deduplicate
    chunks = _to_chunk_results(raw_results)
    chunks = deduplicate_chunks(chunks)
    chunks = chunks[:5]  # top 5 for generation

    # Step 5: Emit sources
    source_dicts = _to_source_results(chunks)
    yield format_sse_event("sources", source_dicts)

    # Step 6: Generate with streaming
    if not chunks:
        yield format_sse_event("token", {"text": "I couldn't find relevant planning documents for that query. Try broadening your search or adjusting filters."})
        yield format_sse_event("done", {"suggested_filters": suggested_filters})
        return

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
        yield format_sse_event("error", {"message": "Failed to generate a response. Sources are shown above for reference."})

    # Step 7: Done
    yield format_sse_event("done", {"suggested_filters": suggested_filters})
```

- [ ] **Step 2: Verify the file has no syntax errors**

Run: `python -c "import ast; ast.parse(open('src/landrag/chat/pipeline.py').read()); print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add src/landrag/chat/pipeline.py
git commit -m "feat(chat): add RAG pipeline orchestration"
```

---

## Task 10: Corpus Status Endpoint

**Files:**
- Create: `src/landrag/api/routes/corpus.py`
- Create: `tests/api/test_corpus.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/api/test_corpus.py

from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from landrag.api.app import create_app


@patch("landrag.api.routes.corpus.get_async_session_factory")
def test_corpus_status_returns_sources(mock_factory):
    # Mock the DB session factory and query result
    from datetime import datetime, UTC

    mock_session = AsyncMock()
    mock_result = AsyncMock()
    mock_result.all.return_value = [
        ("pins", 2341, datetime(2026, 3, 12, 14, 30, tzinfo=UTC)),
        ("lpa", 892, datetime(2026, 3, 10, 9, 15, tzinfo=UTC)),
    ]
    mock_session.execute.return_value = mock_result
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    mock_session_factory = AsyncMock(return_value=mock_session)
    mock_factory.return_value = mock_session_factory

    app = create_app()
    client = TestClient(app)
    response = client.get("/v1/corpus-status")
    assert response.status_code == 200
    data = response.json()
    assert "sources" in data
    assert "total_documents" in data
    assert data["total_documents"] == 3233
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/api/test_corpus.py -v`
Expected: FAIL — `ImportError`

- [ ] **Step 3: Write implementation**

```python
# src/landrag/api/routes/corpus.py

from fastapi import APIRouter
from sqlalchemy import func, select

from landrag.core.db import get_async_session_factory
from landrag.models.database import Document
from landrag.models.schemas import CorpusSourceStatus, CorpusStatusResponse

router = APIRouter(prefix="/v1")


@router.get("/corpus-status")
async def corpus_status() -> CorpusStatusResponse:
    """Return document counts and last update per source portal."""
    session_factory = get_async_session_factory()
    async with session_factory() as session:
        result = await session.execute(
            select(
                Document.source_portal,
                func.count(Document.id).label("doc_count"),
                func.max(Document.created_at).label("last_updated"),
            ).group_by(Document.source_portal)
        )
        rows = result.all()

    sources = [
        CorpusSourceStatus(
            portal=row[0],
            document_count=row[1],
            last_updated=row[2].isoformat() if row[2] else "",
        )
        for row in rows
    ]
    total = sum(s.document_count for s in sources)

    return CorpusStatusResponse(sources=sources, total_documents=total)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/api/test_corpus.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/landrag/api/routes/corpus.py tests/api/test_corpus.py
git commit -m "feat(api): add corpus status endpoint"
```

---

## Task 11: Chat API Endpoint

**Files:**
- Create: `src/landrag/api/routes/chat.py`
- Create: `tests/api/test_chat.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/api/test_chat.py

from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from landrag.api.app import create_app


def _mock_chat_stream(*args, **kwargs):
    """Return an async generator that yields test SSE events."""
    async def _gen():
        yield 'event: sources\ndata: [{"ref": 1, "chunk_id": "abc", "document_title": "Test Doc", "document_type": "decision_letter", "project_name": "Test", "project_reference": "EN010099", "project_type": "onshore_wind", "topic": "noise", "source_url": "https://example.com", "content": "Test content", "score": 0.9, "page_start": 1, "page_end": 5}]\n\n'
        yield 'event: token\ndata: {"text": "The noise"}\n\n'
        yield 'event: token\ndata: {"text": " conditions"}\n\n'
        yield 'event: done\ndata: {"suggested_filters": {}}\n\n'
    return _gen()


@patch("landrag.api.routes.chat.chat_stream", side_effect=_mock_chat_stream)
def test_chat_endpoint_streams_sse(mock_stream):
    app = create_app()
    client = TestClient(app)
    response = client.post(
        "/v1/chat",
        json={"message": "What noise conditions?"},
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    body = response.text
    assert "event: sources" in body
    assert "event: token" in body
    assert "event: done" in body


def test_chat_endpoint_rejects_empty_message():
    app = create_app()
    client = TestClient(app)
    response = client.post("/v1/chat", json={"message": ""})
    assert response.status_code == 422
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/api/test_chat.py -v`
Expected: FAIL — `ImportError`

- [ ] **Step 3: Write implementation**

```python
# src/landrag/api/routes/chat.py

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from landrag.chat.pipeline import chat_stream
from landrag.models.schemas import ChatRequest

router = APIRouter(prefix="/v1")


@router.post("/chat")
async def chat(request: ChatRequest) -> StreamingResponse:
    """Stream a RAG chat response as Server-Sent Events."""
    return StreamingResponse(
        chat_stream(
            message=request.message,
            history=request.history,
            explicit_filters=request.filters,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/api/test_chat.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add src/landrag/api/routes/chat.py tests/api/test_chat.py
git commit -m "feat(api): add streaming chat endpoint"
```

---

## Task 12: Register New Routers & Update App

**Files:**
- Modify: `src/landrag/api/app.py`
- Modify: `src/landrag/api/routes/ui.py`
- Test: existing tests must still pass

- [ ] **Step 1: Update app.py to register new routers**

```python
# src/landrag/api/app.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from landrag.api.routes.chat import router as chat_router
from landrag.api.routes.corpus import router as corpus_router
from landrag.api.routes.health import router as health_router
from landrag.api.routes.search import router as search_router
from landrag.api.routes.ui import router as ui_router


def create_app() -> FastAPI:
    app = FastAPI(title="landRAG", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health_router)
    app.include_router(search_router)
    app.include_router(chat_router)
    app.include_router(corpus_router)
    app.include_router(ui_router)

    return app
```

- [ ] **Step 2: Update ui.py to serve chat page**

Replace `src/landrag/api/routes/ui.py`:

```python
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()

templates = Jinja2Templates(
    directory=str(Path(__file__).resolve().parent.parent.parent / "templates")
)


@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(request, "chat.html")
```

- [ ] **Step 3: Run all existing tests**

Run: `pytest tests/ -v --ignore=tests/chat`
Expected: ALL PASS (existing tests unbroken). Note: `tests/api/test_ui.py` may need updating since the `/search` route is removed. If it fails, update it to test the new `GET /` → `chat.html` route instead.

- [ ] **Step 4: Commit**

```bash
git add src/landrag/api/app.py src/landrag/api/routes/ui.py
git commit -m "feat(app): register chat and corpus routers, update homepage"
```

---

## Task 13: Chat UI Template

**Files:**
- Create: `src/landrag/templates/chat.html`
- Modify: `src/landrag/templates/base.html`
- Remove: `src/landrag/templates/search.html`
- Remove: `src/landrag/templates/results.html`

This is the largest task — the full chat UI. Tested manually against the mockup.

- [ ] **Step 1: Update base.html for chat layout**

Replace `src/landrag/templates/base.html`:

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}landRAG{% endblock %}</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@picocss/pico@2/css/pico.min.css">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: system-ui, -apple-system, sans-serif; background: #ffffff; color: #1a1a1a; height: 100vh; overflow: hidden; }
    </style>
    {% block styles %}{% endblock %}
</head>
<body>
    {% block body %}{% endblock %}
    {% block scripts %}{% endblock %}
</body>
</html>
```

- [ ] **Step 2: Create chat.html**

Create `src/landrag/templates/chat.html` — this is a large file. Key sections:

The template extends `base.html` and contains:
- CSS for the chat layout (sidebar, message thread, input area, source cards, filter chips)
- HTML structure matching the approved mockup
- Vanilla JS handling: state management, localStorage sync, SSE streaming via fetch + ReadableStream, citation post-processing with marked.js, sidebar management, filter chips

Due to the size of this file, the implementing agent should build it section by section following the spec's UI Layout, Interaction Table, and Colour Palette sections. The key JS functions needed are:

```javascript
// State
const State = { conversations: {}, activeId: null, filters: {}, streaming: false };

// Core functions
function loadState()          // Load from localStorage
function saveState()          // Sync to localStorage
function newChat()            // Create new conversation
function switchChat(id)       // Switch active conversation
function deleteChat(id)       // Remove conversation
function renderSidebar()      // Render conversation list grouped by date
function renderMessages()     // Render message thread for active conversation
function renderEmptyState()   // Show welcome + starter chips
function renderFilters()      // Render pinned filter chips

// Streaming
async function sendMessage(text)  // POST to /v1/chat, read SSE stream
function parseSSE(chunk)          // Parse SSE text into events
function handleSourcesEvent(data) // Render source cards
function handleTokenEvent(data)   // Append text + markdown render
function handleDoneEvent(data)    // Close stream, suggest filters
function stopStreaming()          // Abort current stream

// Citations
function processCitations(html)   // Regex [n] → clickable spans
function scrollToSource(ref)      // Scroll to + expand source card

// Corpus status
async function loadCorpusStatus() // GET /v1/corpus-status, cache in localStorage

// Filters
function addFilter(key, value)    // Pin a filter
function removeFilter(key, value) // Unpin a filter
function openFilterPanel()        // Show filter selection panel
```

CDN dependencies in the template `<head>`:
```html
<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
```

- [ ] **Step 3: Delete old templates**

Remove `src/landrag/templates/search.html` and `src/landrag/templates/results.html`.

- [ ] **Step 4: Verify the app starts**

Run: `python -c "from landrag.api.app import create_app; app = create_app(); print('OK')"`
Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add src/landrag/templates/base.html src/landrag/templates/chat.html
git rm src/landrag/templates/search.html src/landrag/templates/results.html
git commit -m "feat(ui): add chat interface, remove old search templates"
```

---

## Task 14: Update UI Tests

**Files:**
- Modify: `tests/api/test_ui.py`

- [ ] **Step 1: Update tests for new routes**

Replace `tests/api/test_ui.py`:

```python
from fastapi.testclient import TestClient

from landrag.api.app import create_app


def test_home_serves_chat_page():
    app = create_app()
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert "landRAG" in response.text
    assert "chat" in response.text.lower() or "message" in response.text.lower()
```

- [ ] **Step 2: Run updated test**

Run: `pytest tests/api/test_ui.py -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add tests/api/test_ui.py
git commit -m "test: update UI tests for chat homepage"
```

---

## Task 15: Full Test Suite & Smoke Test

**Files:** None — validation only.

- [ ] **Step 1: Run the complete test suite**

Run: `pytest tests/ -v`
Expected: ALL PASS

- [ ] **Step 2: Run linter**

Run: `ruff check src/ tests/`
Expected: No errors. Fix any issues.

- [ ] **Step 3: Run type checker (advisory)**

Run: `mypy src/landrag/chat/`
Expected: Note any type errors for fixing but don't block on strict mypy.

- [ ] **Step 4: Manual smoke test**

Run: `uvicorn landrag.api.app:create_app --factory --port 8080`

Open `http://localhost:8080` in a browser and verify:
- Chat UI loads with sidebar, empty state, starter chips
- Sidebar shows "New Chat" button
- Input area is visible with placeholder text
- Corpus status area is present in sidebar

Note: Full end-to-end testing requires API keys and a running Pinecone index. The smoke test verifies the UI renders and the app starts without errors.

- [ ] **Step 5: Final commit if any fixes were needed**

```bash
git add -A
git commit -m "fix: address lint and test issues from full suite run"
```
