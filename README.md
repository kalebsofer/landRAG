# landRAG

**Semantic search for UK planning and environmental permitting documents.**

landRAG ingests thousands of planning decisions, EIA chapters, inspector reports, and regulatory guidance from public portals — then makes them searchable by meaning, not just keywords. Ask a question in plain English, filter by project type, topic, region, or outcome, and find the precedent that matters.

Built for environmental consultants, energy developers, and planning lawyers who currently spend hours trawling scattered government portals for relevant case history.

## Architecture

```
                          landrag.softmaxco.io
                                  |
                                  v
                        +-------------------+
                        |    Cloud Run      |
                        |    (FastAPI)      |
                        |                   |
                        |  API + Jinja2 UI  |
                        +--------+----------+
                                 |
              +------------------+------------------+
              |                  |                  |
              v                  v                  v
     +----------------+  +-------------+  +------------------+
     |   PostgreSQL   |  |  Pinecone   |  |      GCS         |
     |  (Cloud SQL)   |  |  (Vectors)  |  |  (Raw files)     |
     |                |  |             |  |                  |
     |  Projects      |  |  3072-dim   |  |  PDFs, HTML,     |
     |  Documents     |  |  embeddings |  |  Word docs       |
     |  Chunks        |  |             |  |                  |
     |  Jobs          |  |             |  |                  |
     +----------------+  +-------------+  +------------------+
              ^                  ^
              |                  |
              +--------+---------+
                       |
              +--------+----------+
              |    Cloud Run      |
              |  (Celery Worker)  |
              |                   |
              |  Scrape > Parse   |
              |  Chunk > Embed    |
              +--------+----------+
                       |
                       v
               +---------------+
               |     Redis     |
               | (Memorystore) |
               |               |
               |  Task queue   |
               +---------------+
```

**Search flow:** Query hits FastAPI, gets embedded via OpenAI, matched against Pinecone (top-k dense retrieval), rescored with BM25 over candidates, then reranked by Cohere cross-encoder. Results come back with metadata from Postgres and highlighted excerpts.

**Ingestion flow:** Celery workers scrape PINS document libraries, extract text (pypdf + Tesseract OCR for scans), chunk semantically by section, classify metadata with Claude Haiku, embed with OpenAI text-embedding-3-large, and upsert to Pinecone.

## What's in the corpus

| Source | Documents | Phase |
|--------|-----------|-------|
| PINS NSIP decisions | Decision letters, EIA chapters, inspector reports | 1 (MVP) |
| PINS appeals | Appeal decision letters | 1 (MVP) |
| GOV.UK guidance | EA, Natural England, regulatory guidance | 1 (MVP) |
| Local Planning Authorities | LPA decisions and documents | 3 |

## Tech stack

| Layer | Choice |
|-------|--------|
| API | Python 3.12, FastAPI |
| Database | PostgreSQL 16 (Cloud SQL) |
| Vectors | Pinecone (text-embedding-3-large, 3072 dims) |
| Reranking | Cohere Rerank API |
| Task queue | Celery + Redis (Memorystore) |
| File storage | Google Cloud Storage |
| LLM | Claude Sonnet (chat), Claude Haiku (classification) |
| UI (MVP) | Jinja2 server-rendered, Pico CSS |
| Infrastructure | GCP (Cloud Run, Cloud SQL, Memorystore, GCS) |

## Getting started

### Prerequisites

- Python 3.12+
- Docker & Docker Compose
- API keys: Pinecone, OpenAI, Cohere, Anthropic

### Setup

```bash
# Clone and enter the repo
git clone https://github.com/your-org/landRAG.git
cd landRAG

# Start Postgres and Redis
docker compose up -d

# Create a virtualenv and install
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[dev]"

# Configure environment
cp .env.example .env
# Edit .env with your API keys

# Run database migrations
alembic upgrade head

# Start the API
uvicorn landrag.api.app:create_app --factory --reload

# Start a Celery worker (separate terminal)
celery -A landrag.workers.celery_app worker --loglevel=info
```

The app will be available at `http://localhost:8000`.

### Running tests

```bash
pytest -v
```

## Project structure

```
src/landrag/
  api/            FastAPI app, routes, dependencies
  ingestion/      Scrapers, parsers, chunker, embedder, classifier
  workers/        Celery task definitions
  models/         SQLAlchemy models, Pydantic schemas, enums
  search/         Retrieval (dense + BM25) and reranking
  templates/      Jinja2 templates for MVP UI
  core/           Config, database, Pinecone client setup
tests/            Mirrors src structure
docs/plans/       Architecture, implementation, and deployment docs
```

## Roadmap

**Phase 1 (MVP)** — PINS corpus ingestion, semantic search with metadata filters, server-rendered UI

**Phase 2** — RAG chat interface, structured condition extraction from decision letters

**Phase 3** — LPA document expansion, React frontend, user accounts, billing, API access

## License

Proprietary. All rights reserved.
