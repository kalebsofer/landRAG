# RAG Chat Interface — Design Spec

## Overview

A chat-first interface that replaces the existing search page as landRAG's homepage. Users interact conversationally to research UK planning and environmental permitting documents. The system retrieves relevant document chunks via the existing hybrid search pipeline and streams grounded, cited answers using Claude Sonnet.

**Target users:** Environmental consultants, energy developers, and planning lawyers.

**Use modes:** Both exploratory research ("How have offshore wind projects handled cumulative landscape impact?") and direct answer retrieval ("What noise conditions were applied to Hornsea Project Three?").

## UI Layout

Light-themed chat interface inspired by ChatGPT and Claude, built with Jinja2 + vanilla JS + Pico CSS.

### Structure

```
┌──────────────┬─────────────────────────────────────────┐
│              │                                         │
│   Sidebar    │          Message Thread                 │
│              │                                         │
│  - Logo      │   [User bubble, right-aligned]          │
│  - New Chat  │                                         │
│  - History   │   [Assistant response, left-aligned]    │
│    (by date) │     - Inline [1][2] citation badges     │
│              │     - Expandable source cards below     │
│              │                                         │
│              │                                         │
│  - Corpus    ├─────────────────────────────────────────┤
│    Status    │  [Filter chips]  [×]  [×]               │
│  - Scope     │  [Text input................] [Send]    │
│    Filters   │  landRAG searches UK planning docs...   │
└──────────────┴─────────────────────────────────────────┘
```

### Sidebar (Left)

- **Brand:** "landRAG" with blue accent
- **New Chat button:** Creates a new conversation with a generated UUID
- **Conversation history:** Grouped by date (Today, Yesterday, Older). Each entry shows the first message truncated. Active conversation highlighted
- **Corpus status:** Shows data sources, document counts, and last update date per source portal (e.g., "PINS NSIP · 2,341 docs · Updated 12 Mar 2026")
- **Scope Filters button:** Opens a filter panel for manually setting persistent filters
- **Collapsible:** Hamburger toggle on mobile, state persisted in localStorage

### Message Thread (Center)

- **User messages:** Right-aligned bubbles, light blue background (#eef2ff)
- **Assistant messages:** Left-aligned, full-width, rendered as markdown via marked.js (~8KB CDN)
- **Citation badges:** Inline `[1]`, `[2]` etc. rendered as clickable blue spans. Clicking scrolls to and expands the corresponding source card
- **Source cards:** Below each assistant message, collapsed by default. Each card shows:
  - Reference number and document title
  - Document type, project reference, project type, topic
  - Page range
  - Expandable: full source text snippet and link to original source URL

### Input Area (Bottom)

- **Filter chips:** Pinned filters shown as removable pills above the input (e.g., "OFFSHORE_WIND ×", "NOISE ×")
- **Text input:** Auto-growing textarea. Enter to send, Shift+Enter for newline
- **Send button:** Blue arrow, disabled during streaming. Replaced by a stop button while streaming
- **Disclaimer:** "landRAG searches UK planning documents. Answers include source citations."

### Empty State

Centered welcome when no conversation is active:
- landRAG logo and brief description
- Corpus status summary (sources, counts, last updated)
- 3-4 clickable starter question chips:
  - "What noise conditions apply to offshore wind projects?"
  - "Compare ecology mitigation across solar farms"
  - "Summarise flood risk assessments for battery storage"
  - "What did the inspector conclude on landscape impact for Hornsea Three?"

### Colour Palette

- Background: white (#ffffff)
- Sidebar: light grey (#f7f7f8)
- Primary accent: blue (#2563eb)
- User bubble: light blue (#eef2ff)
- Source cards: off-white (#f9fafb) with grey border (#e5e5e5)
- Text: dark (#1a1a1a / #333)
- Muted text: grey (#888 / #999)
- Filter chips: blue tint (#eef2ff) with blue border (#c7d2fe)

## API Design

### `GET /`

Serves the chat Jinja2 template. Replaces the existing search homepage.

### `POST /v1/chat`

Accepts a message with conversation history and optional filters. Returns a streaming SSE response.

**Request body:**

```json
{
  "message": "What noise conditions were applied to Hornsea Three?",
  "history": [
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "..."}
  ],
  "filters": {
    "project_type": "OFFSHORE_WIND",
    "topic": "NOISE"
  }
}
```

- `message` (string, required): The user's current message
- `history` (array, optional): Previous conversation turns as role/content pairs
- `filters` (object, optional): Explicitly pinned filters. All fields from the existing `SearchFilters` schema are supported: project_type, topic, document_type, decision, date_range, region, capacity_mw_range

**SSE stream — three event types in order:**

1. **`event: sources`** — Fired once after retrieval completes. Delivers source metadata and content so the frontend can render cards immediately.
```
event: sources
data: [{"ref": 1, "chunk_id": "...", "document_title": "...", "document_type": "...", "project_name": "...", "project_reference": "...", "project_type": "...", "topic": "...", "source_url": "...", "page_start": 45, "page_end": 48, "content": "..."}]
```

2. **`event: token`** — Fired per token as Claude Sonnet streams the answer.
```
event: token
data: {"text": "Hornsea Project Three"}
```

3. **`event: done`** — Signals stream complete. Includes any LLM-suggested filters.
```
event: done
data: {"suggested_filters": {"project_type": "OFFSHORE_WIND", "topic": "NOISE"}}
```

**Why sources first:** Search completes in ~1-2s. Emitting sources before the LLM starts gives users immediate feedback that retrieval worked. They can begin reading source cards while the answer streams in.

### `GET /v1/corpus-status`

Returns corpus metadata for transparency about what's searchable.

**Response:**

```json
{
  "sources": [
    {
      "portal": "PINS_NSIP",
      "document_count": 2341,
      "last_updated": "2026-03-12T14:30:00Z"
    },
    {
      "portal": "PINS_APPEALS",
      "document_count": 892,
      "last_updated": "2026-03-10T09:15:00Z"
    }
  ],
  "total_documents": 3233
}
```

Queries the `Document` and `IngestionJob` tables grouped by `source_portal`. Frontend caches in localStorage with a 1-hour TTL.

### Existing endpoints

- `POST /v1/search` — Retained as an internal API. No longer exposed in the UI.
- `GET /health` — Unchanged.

## RAG Pipeline

### Flow

```
User message + history + filters
        │
        ▼
  ┌─────────────┐
  │  1. CONTEXT  │  Extract last 2-3 turns from history
  │   WINDOW     │  for conversational context
  └──────┬──────┘
         │
         ▼
  ┌─────────────┐
  │ 2. QUERY    │  Send message + recent context to Claude Haiku
  │ REWRITING   │  → Standalone search query
  │             │  → Filter suggestions from natural language
  └──────┬──────┘
         │
         ▼
  ┌─────────────┐
  │ 3. RETRIEVE │  Call existing execute_search() with rewritten query
  │             │  Merge: explicit user filters + LLM-suggested filters
  │             │  Returns top-k ChunkResults with scores
  └──────┬──────┘
         │
         ▼
  ┌─────────────┐
  │ 4. DEDUPE   │  Remove overlapping chunks from same document
  │  CHUNKS     │  (same document_id + overlapping page range)
  │             │  Preserves source diversity
  └──────┬──────┘
         │
         ▼
  ┌─────────────┐
  │ 5. STREAM   │  Emit SSE `sources` event with chunk metadata
  │  SOURCES    │  (fires before LLM starts — fast feedback)
  └──────┬──────┘
         │
         ▼
  ┌─────────────┐
  │ 6. GENERATE │  Build prompt: system instructions + source chunks
  │  (STREAM)   │  + conversation history + user message
  │             │  Stream Claude Sonnet response token-by-token
  │             │  via SSE `token` events
  └──────┬──────┘
         │
         ▼
  ┌─────────────┐
  │ 7. DONE     │  Emit SSE `done` with suggested filters
  └─────────────┘
```

### Query Rewriting (Step 2)

Uses Claude Haiku for speed and cost. Prompt:

```
Given this conversation context and new message, produce:
1. A standalone search query (resolving pronouns and references)
2. Any filters implied by the query (project_type, topic, etc.)

Conversation context:
{last 2-3 turns}

New message: {user message}

Respond as JSON: {"query": "...", "filters": {"project_type": "...", ...}}
```

On first messages (empty history), query rewriting is still applied for filter extraction but the query passes through largely unchanged.

### Filter Merge Logic (Step 3)

Explicit user-pinned filters always take precedence. LLM-suggested filters are additive only — they fill in unset filter fields but never override what the user explicitly set.

```python
merged = {**suggested_filters, **explicit_filters}  # explicit wins
```

### Chunk Deduplication (Step 4)

After retrieval and reranking, deduplicate chunks that come from the same document with overlapping page ranges. Keep the highest-scored chunk from each overlapping group. This ensures diverse sources in the generation prompt rather than multiple excerpts from the same section.

### Context Budget (Step 6)

The generation prompt has a token budget:
- System prompt: ~300 tokens
- Source chunks: top 5 chunks, ~2-3k tokens
- Conversation history: full history, capped at ~8k tokens (truncate oldest turns)
- User message: variable

Total prompt budget stays well within Claude Sonnet's context window.

## System Prompt

```
You are landRAG, a research assistant for UK planning and environmental
permitting documents. You answer questions using ONLY the source documents
provided below.

Rules:
- Cite every factual claim using [n] references matching the source numbers
- If the sources don't contain enough information to answer, say so explicitly
- Never fabricate planning conditions, decisions, or document references
- When sources conflict, present both positions with their citations
- Use precise planning terminology (DCO, NSIP, NPS, EIA, etc.)
- For direct questions: be concise and specific
- For exploratory questions: synthesise across sources and highlight patterns

Sources:
[1] {document_title} ({project_reference}, {document_type}, pp. {page_range})
{chunk_content}

[2] ...
```

**Constraints rationale:**
- **"ONLY the source documents"** — Prevents hallucination of planning conditions. A fabricated noise limit in a planning application could have legal consequences.
- **Mandatory citation** — Every factual claim gets `[n]`. The frontend renders these as clickable badges.
- **Conflict handling** — Planning documents frequently contradict (e.g., applicant's assessment vs. inspector's findings). The prompt requires presenting both.
- **Explicit about gaps** — If sources don't cover the question, say so rather than hedging with uncited speculation.

## Frontend Architecture

### Technology

- **Template:** Single Jinja2 file `chat.html` extending `base.html`
- **CSS:** Pico CSS (existing CDN) + inline styles for chat-specific elements
- **JS:** Vanilla JavaScript, inline in the template
- **Markdown:** marked.js (~8KB) from CDN
- **No build step, no node_modules**

### State

```javascript
State = {
  conversations: {},    // All conversations keyed by UUID
  activeId: null,       // Current conversation ID
  filters: {},          // Pinned filters for current conversation
  streaming: false      // Whether a response is in progress
}
```

Synced to `localStorage.landrag_conversations` on every mutation. Corpus status cached separately in `localStorage.landrag_corpus_status` with a 1-hour TTL.

### Interaction Table

| Action | Behaviour |
|--------|-----------|
| Page load | Load state from localStorage, render sidebar, show last active conversation or empty state |
| New Chat | Generate UUID, add to state, clear message area, show welcome prompt |
| Send message | Append to history, POST to `/v1/chat` via `fetch()`, read SSE stream from response body |
| `sources` event | Render source cards below the in-progress message (collapsed by default) |
| `token` event | Append text to assistant message div, run through marked.js for markdown |
| `done` event | Close stream, parse suggested filters, show "pin filter?" prompt if new filters detected |
| Click `[n]` badge | Scroll to and expand the corresponding source card |
| Remove filter chip | Remove from state, no retroactive effect on existing messages |
| Delete conversation | Remove from localStorage, switch to next conversation or empty state |
| Sidebar toggle | CSS class toggle, persisted in localStorage |
| Stop button | Abort the fetch request, keep partial response displayed |
| Starter chip click | Populate input with the question text and auto-send |

### Citation Post-Processing

After each `token` event, a regex scans the accumulated response text for `[n]` patterns and wraps them in clickable `<span>` elements linked to the corresponding source card. Applied incrementally as tokens arrive.

### Streaming Implementation

Uses `fetch()` with `ReadableStream` reader on the response body, not `EventSource` (which requires GET). The response is `Content-Type: text/event-stream`. JS parses SSE format line-by-line from the stream chunks.

## Corpus Status & Transparency

### Sidebar Display

Bottom of the sidebar, always visible:

```
─────────────────────
Data Sources
PINS NSIP    · 2,341 docs · Updated 12 Mar 2026
PINS Appeals ·   892 docs · Updated 10 Mar 2026
─────────────────────
```

### Empty State

The welcome screen includes the full corpus summary so first-time users immediately understand scope.

### In Error Messages

When no results are found, the response includes: "landRAG currently covers X documents from [source list]. Last updated [date]." Helps users distinguish "out of scope" from "poorly worded query".

### When Asked About Unsupported Corpus

The system prompt includes awareness of which source portals are indexed. If a user asks about documents outside the current corpus, the response acknowledges the gap: "landRAG currently covers PINS NSIP and Appeals documents. LPA, EA, and NE documents are not yet indexed."

## Error Handling

| Scenario | Behaviour |
|----------|-----------|
| No relevant sources found | Message: "I couldn't find relevant planning documents for that query. Try broadening your search or adjusting filters." Includes corpus status. No source cards. |
| Retrieval succeeds, LLM stream fails | Sources already displayed. Error banner: "Failed to generate a response. Sources are shown below for reference." |
| Network disconnect mid-stream | Detect stream close, show partial response with "Response interrupted — click to retry" button. |
| Empty conversation history | Valid first message. Query rewriting still runs for filter extraction. |
| Message sent while streaming | Disabled. Send button greyed out, replaced by stop button. |
| Long conversation (>8k tokens history) | Truncate oldest turns from generation prompt. Full history preserved in localStorage for display. |
| localStorage full | Catch quota error, warn user, offer to delete oldest conversations. |
| Filters return zero Pinecone results | Fall back to search without filters. Note in response: "No results matched your filters. Showing results from all documents instead." |
| User asks about unsupported corpus | Response acknowledges gap with current corpus scope. |

## Testing Strategy

| Layer | What's Tested | Approach |
|-------|---------------|----------|
| Chat endpoint | Request validation, SSE event format, error responses | pytest + httpx AsyncClient, mock retrieval and LLM |
| Query rewriter | Pronoun resolution, filter extraction, first-message handling | Unit tests with canned histories, mock Haiku |
| Chunk deduplication | Same-doc overlap removal, diverse source preservation | Pure function, unit tests with synthetic ChunkResults |
| System prompt builder | Source injection, token budget, prompt format | Unit tests asserting chunk content and metadata in output |
| SSE streaming | Event ordering (sources → tokens → done), partial failure | Integration test with mock LLM yielding known tokens |
| Corpus status | Correct counts and dates per source portal | Unit test with DB fixtures |
| Filter merge | Explicit overrides suggestions, additive-only behaviour | Unit tests with filter combinations |
| Frontend | Manual verification against mockup | Acceptable for MVP (solo dev, vanilla JS) |

All tests follow existing patterns: pytest with async fixtures, mocked external APIs (Anthropic, OpenAI, Cohere, Pinecone).

## Files Changed

### New Files
- `src/landrag/api/templates/chat.html` — Chat interface template (Jinja2 + vanilla JS)
- `src/landrag/api/routes/chat.py` — Chat API route (`POST /v1/chat`)
- `src/landrag/chat/` — New package for chat logic
  - `src/landrag/chat/pipeline.py` — RAG chat pipeline orchestration
  - `src/landrag/chat/rewriter.py` — Query rewriting with Haiku
  - `src/landrag/chat/prompt.py` — System prompt builder
  - `src/landrag/chat/dedup.py` — Chunk deduplication
  - `src/landrag/chat/streaming.py` — SSE response formatting
- `src/landrag/api/routes/corpus.py` — Corpus status endpoint
- `tests/test_chat_endpoint.py`
- `tests/test_query_rewriter.py`
- `tests/test_chunk_dedup.py`
- `tests/test_prompt_builder.py`
- `tests/test_sse_streaming.py`
- `tests/test_corpus_status.py`
- `tests/test_filter_merge.py`

### Modified Files
- `src/landrag/api/app.py` — Register chat and corpus routers, remove old UI router
- `src/landrag/api/routes/ui.py` — Replace search page routes with chat page route
- `src/landrag/api/templates/base.html` — Update nav for chat-first layout
- `src/landrag/core/config.py` — Add chat model settings (sonnet model name, max tokens)
- `src/landrag/models/schemas.py` — Add ChatRequest, ChatMessage, CorpusStatus schemas

### Removed
- `src/landrag/api/templates/search.html` — Replaced by chat.html
- `src/landrag/api/templates/results.html` — No longer needed
