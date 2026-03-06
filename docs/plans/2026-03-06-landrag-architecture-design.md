# landRAG Architecture Design

## Overview

landRAG is a semantic search and RAG platform for UK planning and environmental permitting. It ingests publicly available planning decisions, EIAs, inspector reports, and regulatory guidance, exposing them through a search API and conversational interface.

Target users: environmental consultants, energy developers, planning lawyers.

## Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Backend | Python (FastAPI) | Best fit for ML ecosystem (embeddings, OCR, reranking) |
| Architecture | Monorepo monolith | Solo dev, fastest iteration, split later if needed |
| Vector store | Pinecone | Managed, offloads index ops |
| Structured DB | PostgreSQL (Cloud SQL) | Relational fits metadata, conditions, job state |
| Job queue | Celery + Redis | Python standard, well-documented async task queue |
| Cloud | GCP | Cloud Run (API), Cloud SQL, Memorystore, GCS |
| MVP UI | Jinja2 server-rendered | No build step, fast to ship; separate React SPA later |

## Project Structure

```
landRAG/
  src/
    landrag/
      api/
        routes/
          search.py        # POST /v1/search
          health.py        # GET /health
        dependencies.py    # shared deps (db sessions, pinecone client)
        app.py             # FastAPI app factory
      ingestion/
        scrapers/
          pins.py          # PINS NSIP + appeal decisions
        parsers/
          pdf.py           # pypdf + Tesseract OCR fallback
          html.py          # BeautifulSoup HTML extraction
          docx.py          # python-docx extraction
        chunker.py         # semantic + fixed-size fallback chunking
        embedder.py        # embedding via OpenAI text-embedding-3-large
        classifier.py     # LLM-assisted metadata extraction (Claude Haiku)
      workers/
        tasks.py           # Celery task definitions
        celery_app.py      # Celery config
      models/
        database.py        # SQLAlchemy models
        schemas.py         # Pydantic request/response schemas
        enums.py           # ProjectType, DocumentType, Topic, etc.
      search/
        retrieval.py       # hybrid search: Pinecone dense + BM25 sparse
        reranker.py        # cross-encoder reranking (Cohere Rerank)
      templates/           # Jinja2 templates for MVP UI
        base.html
        search.html
        results.html
      core/
        config.py          # pydantic-settings, env vars
        pinecone.py        # Pinecone client init
        db.py              # SQLAlchemy engine/session factory
  tests/
  alembic/                 # DB migrations
  alembic.ini
  pyproject.toml
  Dockerfile
  docker-compose.yml       # local dev: postgres, redis
  .env.example
```

## Data Models

### PostgreSQL Schema

**Project** — represents a planning project (NSIP, appeal, etc.)
- id (UUID PK), name, reference (unique, e.g. EN010012), type (ProjectType enum), local_authority, region, coordinates (nullable), capacity_mw (nullable), decision (nullable), decision_date (nullable), created_at, updated_at

**Document** — a single file ingested from a source portal
- id (UUID PK), project_id (FK), title, type (DocumentType enum), date_published (nullable), file_format, source_url, source_portal (SourcePortal enum), retrieved_at, storage_path (GCS path), created_at

**Chunk** — a text segment from a document, linked to its Pinecone vector
- id (UUID PK), document_id (FK), content (text), chunk_index, topic (Topic enum, nullable), chapter_number (nullable), page_start (nullable), page_end (nullable), pinecone_id, created_at

**IngestionJob** — tracks scraping/processing runs
- id (UUID PK), source_portal, status (pending/running/completed/failed), documents_found (nullable), documents_processed (nullable), error_message (nullable), started_at (nullable), completed_at (nullable), created_at

**PlanningCondition** (Phase 2) — structured conditions extracted from decision letters
- id (UUID PK), document_id (FK), project_id (FK), condition_number, category (Topic enum), requirement (text), raw_text (text), trigger (nullable), discharge_authority (nullable), monitoring_required (bool), thresholds (JSONB, nullable), created_at

### Pinecone Vector Metadata

Stored per vector for server-side filtering:
- project_type, document_type, topic, decision, date_published, region, capacity_mw, project_reference

## Ingestion Pipeline

Celery tasks, each stage separate for retry isolation:

```
ScrapeTask → ParseTask (per doc) → ChunkTask (per doc) → EmbedTask (batch)
```

- **Scraping:** Crawl PINS document libraries. Rate limited (5/min). Store raw files in GCS.
- **Text extraction:** pypdf for native PDFs, Tesseract OCR for scanned docs, BeautifulSoup for HTML, python-docx for Word.
- **Chunking:** Semantic chunking by section headers first, fixed-size fallback (512 tokens, 64 overlap). Preserve paragraph boundaries.
- **Metadata classification:** Rule-based for PINS references and dates. Claude Haiku for topic classification and project type when ambiguous.
- **Embedding:** text-embedding-3-large (OpenAI). Batch embed, upsert to Pinecone, write pinecone_id to Postgres.

## Search & Retrieval

```
Query → Embed → Pinecone (top-k=20, metadata filters) → Fetch chunks from Postgres
  → BM25 re-score (rank_bm25 in-memory over 20 candidates)
  → Combine scores (0.7 dense + 0.3 BM25)
  → Cross-encoder rerank (Cohere Rerank) → top-n results
```

- Hybrid retrieval: dense vectors + sparse BM25 for technical terms
- BM25 runs in-memory over Pinecone candidates only — no separate search engine
- Reranker: Cohere Rerank API to start; swap to local cross-encoder if cost is an issue

### API

```
POST /v1/search
  query: str
  filters?: projectType[], topic[], documentType[], decision[], dateRange, region[], capacityMwRange
  limit?: int (default 10, max 50)

Response:
  results: [{chunk, score, highlight}]
  totalEstimate: int
```

## MVP UI (Server-Rendered)

Jinja2 templates, Pico CSS for styling, no JS build step.

- **Search page (/):** query input + collapsible filter panel
- **Results page (/search):** result cards with title, project, topic badge, score, highlighted excerpt, source link. Pagination.
- **Document view (/document/{id}):** full metadata + chunk list + original source link

Note: production frontend will be a separate React SPA. Jinja2 UI is MVP scaffolding.

## Infrastructure

### Local Dev

docker-compose: PostgreSQL 16, Redis 7. Pinecone uses dev index (free tier). API + Celery worker run on host.

### GCP Deployment

| Component | Service |
|-----------|---------|
| API | Cloud Run |
| Celery workers | Cloud Run Jobs / GCE |
| PostgreSQL | Cloud SQL |
| Redis | Memorystore |
| File storage | GCS |
| Secrets | Secret Manager |

### CI

GitHub Actions: ruff (lint), mypy (type check), pytest (tests) on push. Deploy to Cloud Run on merge to main.

## Testing Strategy

- **Unit tests:** chunking logic, metadata extraction, filter translation, schema validation
- **Integration tests:** ingestion pipeline (known PDF → chunks in Postgres + Pinecone), search endpoint (seeded data → expected results)
- **Retrieval evaluation:** 200 hand-curated QA pairs, Recall@10 + MRR, run manually via `pytest -m evaluation`

## Phasing

**Phase 1 (MVP):** PINS corpus ingestion + semantic search + metadata filters + server-rendered UI
**Phase 2:** RAG chat interface + condition extraction
**Phase 3:** LPA expansion + React frontend + user accounts + billing + API access
