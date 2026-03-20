# CLAUDE.md

## Project Overview

landRAG is a semantic search & RAG platform for UK planning/environmental permitting documents (PINS, LPA, EA, NE, GOV.UK). Python 3.12 + FastAPI monorepo.

## Quick Reference

```bash
# Install
pip install -e ".[dev]"

# Local services (Postgres 16 + Redis 7)
docker compose up -d

# Run migrations
alembic upgrade head

# Start app (dev)
uvicorn landrag.api.app:create_app --factory --reload

# Start Celery worker
celery -A landrag.workers.celery_app worker --loglevel=info
```

## Testing

```bash
pytest tests/ -x -q                          # All unit tests
pytest tests/ -x -q --ignore=tests/workers   # Skip worker tests
pytest tests/path/to/test_file.py -x -q      # Single file
pytest -m evaluation                          # Manual retrieval quality tests (not CI)
```

Integration tests are excluded from CI. The `evaluation` marker is for manual retrieval quality checks only.

## Linting & Formatting

```bash
ruff check src/ tests/          # Lint
ruff check --fix src/ tests/    # Lint + autofix
ruff format src/ tests/         # Format
ruff format --check src/ tests/ # Format check (CI uses this)
mypy src/                       # Type check (strict mode)
```

**Rules:** line length 100, ruff rules E/F/I/N/W/UP, mypy strict.

## Code Conventions

- **Async everywhere**: FastAPI routes, SQLAlchemy asyncio, async tests (pytest-asyncio auto mode)
- **Type hints required**: mypy strict is enforced
- **Pydantic V2** for all schemas
- **SQLAlchemy 2.0** ORM patterns
- **Functions over classes** for utility code
- **Router-based** FastAPI organization in `src/landrag/api/routes/`
- **`get_settings()`** (LRU-cached) for configuration access

## Commit Convention

Use `type: description` format:
- `feat:` new feature
- `fix:` bug fix
- `chore:` maintenance
- `ci:` CI/CD changes
- `ops:` deployment/infrastructure
- `docs:` documentation

## Project Structure

```
src/landrag/
├── api/          FastAPI app factory + routes (health, search, ui)
├── core/         Config (pydantic-settings), DB engine, Pinecone client
├── ingestion/    Scrapers, parsers (PDF/HTML/DOCX), chunker, embedder, classifier
├── models/       SQLAlchemy models, Pydantic schemas, enums
├── search/       Hybrid retrieval (BM25 + vector), Cohere reranker
├── workers/      Celery tasks (parse_document, chunk_and_embed)
├── templates/    Jinja2 server-rendered UI
└── cli.py
```

## Environment

Copy `.env.example` to `.env` and fill in API keys. Key vars: `DATABASE_URL`, `REDIS_URL`, `PINECONE_API_KEY`, `OPENAI_API_KEY`, `COHERE_API_KEY`, `ANTHROPIC_API_KEY`.

## Deployment

GCP Cloud Run. See `scripts/provision.sh` (one-time infra) and `scripts/deploy.sh` (deploy). Region: `europe-west2`.
