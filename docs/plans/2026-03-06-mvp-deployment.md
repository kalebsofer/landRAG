# MVP Deployment Preparation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Prepare landRAG for user testing — fix the broken Dockerfile, harden the app, deploy to GCP Cloud Run with Cloud SQL.

**Architecture:** Cloud Run serves the FastAPI app (Jinja2 UI + search API). Cloud SQL provides Postgres. Pinecone remains serverless. No Celery/Redis needed for user testing — the search path is synchronous. Ingestion runs locally via CLI before deploy.

**Tech Stack:** Docker, GCP Cloud Run, Cloud SQL (Postgres 16), Artifact Registry, Secret Manager, GitHub Actions

---

### Task 1: Cache `get_settings()` with `lru_cache`

**Files:**
- Modify: `src/landrag/core/config.py:35-36`
- Test: `tests/core/test_config.py`

**Step 1: Write the failing test**

Add to `tests/core/test_config.py`:

```python
def test_get_settings_is_cached():
    """get_settings() should return the same instance on repeated calls."""
    from landrag.core.config import get_settings

    s1 = get_settings()
    s2 = get_settings()
    assert s1 is s2
```

**Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python -m pytest tests/core/test_config.py::test_get_settings_is_cached -v`
Expected: FAIL — `s1 is s2` is False because each call creates a new Settings()

**Step 3: Implement**

In `src/landrag/core/config.py`, add `functools.lru_cache`:

```python
from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    # ... (all fields unchanged)


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

**Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python -m pytest tests/core/test_config.py::test_get_settings_is_cached -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/landrag/core/config.py tests/core/test_config.py
git commit -m "feat: cache get_settings() with lru_cache"
```

---

### Task 2: Add CORS middleware

**Files:**
- Modify: `src/landrag/api/app.py`
- Test: `tests/api/test_health.py`

**Step 1: Write the failing test**

Add to `tests/api/test_health.py`:

```python
def test_cors_headers_present():
    """Preflight OPTIONS request should return CORS headers."""
    from fastapi.testclient import TestClient
    from landrag.api.app import create_app

    client = TestClient(create_app())
    response = client.options(
        "/health",
        headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "GET"},
    )
    assert response.headers.get("access-control-allow-origin") is not None
```

**Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python -m pytest tests/api/test_health.py::test_cors_headers_present -v`
Expected: FAIL — no CORS headers in response

**Step 3: Implement**

Replace `src/landrag/api/app.py`:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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
    app.include_router(ui_router)

    return app
```

Note: `allow_origins=["*"]` is fine for MVP user testing. Lock down to specific origins before production.

**Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python -m pytest tests/api/test_health.py::test_cors_headers_present -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/landrag/api/app.py tests/api/test_health.py
git commit -m "feat: add CORS middleware for cross-origin API access"
```

---

### Task 3: Improve `/health` endpoint with DB check

**Files:**
- Modify: `src/landrag/api/routes/health.py`
- Test: `tests/api/test_health.py`

**Step 1: Write the failing test**

Add to `tests/api/test_health.py`:

```python
from unittest.mock import patch, MagicMock


def test_health_returns_db_status():
    """Health endpoint should report database connectivity."""
    from fastapi.testclient import TestClient
    from landrag.api.app import create_app

    client = TestClient(create_app())

    # Mock the sync engine to simulate a working DB
    mock_engine = MagicMock()
    mock_conn = MagicMock()
    mock_conn.__enter__ = MagicMock(return_value=mock_conn)
    mock_conn.__exit__ = MagicMock(return_value=False)
    mock_conn.execute.return_value = None
    mock_engine.connect.return_value = mock_conn

    with patch("landrag.api.routes.health.get_sync_engine", return_value=mock_engine):
        response = client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert "database" in data
    assert data["database"] == "ok"


def test_health_reports_db_failure():
    """Health endpoint should report database failure gracefully."""
    from fastapi.testclient import TestClient
    from landrag.api.app import create_app

    client = TestClient(create_app())

    with patch("landrag.api.routes.health.get_sync_engine", side_effect=Exception("connection refused")):
        response = client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["database"] == "error"
```

**Step 2: Run tests to verify they fail**

Run: `.venv/Scripts/python -m pytest tests/api/test_health.py::test_health_returns_db_status tests/api/test_health.py::test_health_reports_db_failure -v`
Expected: FAIL — current /health returns `{"status": "ok"}` with no database field

**Step 3: Implement**

Replace `src/landrag/api/routes/health.py`:

```python
import logging

from fastapi import APIRouter
from sqlalchemy import text

from landrag.core.db import get_sync_engine

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/health")
async def health():
    db_status = "ok"
    try:
        engine = get_sync_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as e:
        logger.warning("Health check DB failure: %s", e)
        db_status = "error"

    return {"status": "ok" if db_status == "ok" else "degraded", "database": db_status}
```

**Step 4: Run tests to verify they pass**

Run: `.venv/Scripts/python -m pytest tests/api/test_health.py -v`
Expected: All PASS (including existing test — update it if the response shape changed)

Note: The existing `test_health` test may need updating since the response shape changed from `{"status": "ok"}` to `{"status": "...", "database": "..."}`. Update it to check `assert response.json()["status"] in ("ok", "degraded")`.

**Step 5: Commit**

```bash
git add src/landrag/api/routes/health.py tests/api/test_health.py
git commit -m "feat: add database connectivity check to health endpoint"
```

---

### Task 4: Fix Dockerfile and add entrypoint

**Files:**
- Modify: `Dockerfile`
- Create: `entrypoint.sh`
- Create: `.dockerignore`

The current Dockerfile runs `pip install .` before copying `src/`, so it installs an empty package. Fix the build order and add an entrypoint that runs Alembic migrations before starting uvicorn.

**Step 1: Create `.dockerignore`**

```
.venv/
venv/
__pycache__/
*.py[cod]
.env
.git/
.github/
.mypy_cache/
.pytest_cache/
.ruff_cache/
.coverage
htmlcov/
data/
docs/
tests/
.claude/
*.egg-info/
dist/
build/
```

**Step 2: Create `entrypoint.sh`**

```bash
#!/bin/bash
set -e

echo "Running database migrations..."
alembic upgrade head

echo "Starting application..."
exec uvicorn landrag.api.app:create_app --factory --host 0.0.0.0 --port "$PORT"
```

**Step 3: Rewrite `Dockerfile`**

```dockerfile
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy everything needed for pip install (source included)
COPY pyproject.toml .
COPY src/ src/
RUN pip install --no-cache-dir .

# Copy Alembic config and migrations
COPY alembic/ alembic/
COPY alembic.ini .

# Copy entrypoint
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

ENV PORT=8080

EXPOSE 8080

ENTRYPOINT ["./entrypoint.sh"]
```

Note: Cloud Run sets `PORT` env var (defaults to 8080). The entrypoint reads it.

**Step 4: Verify Docker build**

Run: `docker build -t landrag:test .`
Expected: Build completes without errors. The `pip install .` step should find and install the landrag package from `src/`.

**Step 5: Commit**

```bash
git add Dockerfile entrypoint.sh .dockerignore
git commit -m "fix: Dockerfile build order, add migration entrypoint and .dockerignore"
```

---

### Task 5: Add app service to docker-compose for local testing

**Files:**
- Modify: `docker-compose.yml`

**Step 1: Update `docker-compose.yml`**

```yaml
services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_USER: landrag
      POSTGRES_PASSWORD: landrag
      POSTGRES_DB: landrag
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U landrag"]
      interval: 5s
      timeout: 3s
      retries: 5

  redis:
    image: redis:7
    ports:
      - "6379:6379"
    volumes:
      - redisdata:/data

  app:
    build: .
    ports:
      - "8080:8080"
    env_file: .env
    environment:
      DATABASE_URL: "postgresql+asyncpg://landrag:landrag@postgres:5432/landrag"
      DATABASE_URL_SYNC: "postgresql+psycopg2://landrag:landrag@postgres:5432/landrag"
      REDIS_URL: "redis://redis:6379/0"
      PORT: "8080"
    depends_on:
      postgres:
        condition: service_healthy

volumes:
  pgdata:
  redisdata:
```

**Step 2: Test locally**

Run: `docker compose up --build`
Expected: postgres starts → healthy → app starts → migrations run → uvicorn listening on 0.0.0.0:8080. Visit http://localhost:8080/health and confirm `{"status": "ok", "database": "ok"}`.

**Step 3: Commit**

```bash
git add docker-compose.yml
git commit -m "feat: add app service to docker-compose for full local stack"
```

---

### Task 6: GitHub Actions CI workflow

**Files:**
- Create: `.github/workflows/ci.yml`

**Step 1: Create CI workflow**

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  lint-and-test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python 3.12
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install ".[dev]"

      - name: Lint with ruff
        run: |
          ruff check src/ tests/
          ruff format --check src/ tests/

      - name: Run tests
        run: pytest tests/ -v --ignore=tests/integration
```

Note: Tests that need a real DB/Pinecone go in `tests/integration/` (doesn't exist yet — this is future-proofing the ignore). All current tests use mocks and will pass without external services.

**Step 2: Verify tests pass locally**

Run: `.venv/Scripts/python -m pytest tests/ -v`
Expected: All tests PASS

Run: `.venv/Scripts/ruff check src/ tests/ && .venv/Scripts/ruff format --check src/ tests/`
Expected: No issues

**Step 3: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: add GitHub Actions workflow for lint and test"
```

---

### Task 7: GCP deployment

This task provisions GCP infrastructure and deploys the app. No TDD — these are `gcloud` CLI commands.

**Prerequisites:**
- Google Cloud SDK (`gcloud`) installed and authenticated
- A GCP project created (e.g., `landrag-mvp`)
- Billing enabled

**Step 1: Set project and enable APIs**

```bash
export GCP_PROJECT=landrag-mvp
export GCP_REGION=europe-west2

gcloud config set project $GCP_PROJECT

gcloud services enable \
  run.googleapis.com \
  sqladmin.googleapis.com \
  artifactregistry.googleapis.com \
  secretmanager.googleapis.com \
  cloudbuild.googleapis.com
```

**Step 2: Create Artifact Registry repository**

```bash
gcloud artifacts repositories create landrag \
  --repository-format=docker \
  --location=$GCP_REGION
```

**Step 3: Create Cloud SQL instance**

```bash
gcloud sql instances create landrag-db \
  --database-version=POSTGRES_16 \
  --tier=db-f1-micro \
  --region=$GCP_REGION \
  --database-flags=max_connections=50

gcloud sql databases create landrag --instance=landrag-db

gcloud sql users set-password postgres \
  --instance=landrag-db \
  --password=<GENERATE_SECURE_PASSWORD>
```

Note the connection name from: `gcloud sql instances describe landrag-db --format='value(connectionName)'`
It will be like `landrag-mvp:europe-west2:landrag-db`.

**Step 4: Store secrets in Secret Manager**

```bash
echo -n "<your-openai-key>" | gcloud secrets create openai-api-key --data-file=-
echo -n "<your-pinecone-key>" | gcloud secrets create pinecone-api-key --data-file=-
echo -n "<your-cohere-key>" | gcloud secrets create cohere-api-key --data-file=-
echo -n "<your-anthropic-key>" | gcloud secrets create anthropic-api-key --data-file=-
echo -n "<db-password>" | gcloud secrets create database-password --data-file=-
```

**Step 5: Build and push Docker image**

```bash
gcloud builds submit --tag $GCP_REGION-docker.pkg.dev/$GCP_PROJECT/landrag/app:latest
```

**Step 6: Deploy to Cloud Run**

```bash
export CLOUD_SQL_CONNECTION=landrag-mvp:europe-west2:landrag-db

gcloud run deploy landrag \
  --image=$GCP_REGION-docker.pkg.dev/$GCP_PROJECT/landrag/app:latest \
  --region=$GCP_REGION \
  --platform=managed \
  --allow-unauthenticated \
  --add-cloudsql-instances=$CLOUD_SQL_CONNECTION \
  --set-env-vars="DATABASE_URL=postgresql+asyncpg://postgres@/landrag?host=/cloudsql/$CLOUD_SQL_CONNECTION" \
  --set-env-vars="DATABASE_URL_SYNC=postgresql+psycopg2://postgres@/landrag?host=/cloudsql/$CLOUD_SQL_CONNECTION" \
  --set-env-vars="APP_ENV=production" \
  --set-env-vars="PINECONE_INDEX_NAME=landrag-dev" \
  --set-secrets="OPENAI_API_KEY=openai-api-key:latest" \
  --set-secrets="PINECONE_API_KEY=pinecone-api-key:latest" \
  --set-secrets="COHERE_API_KEY=cohere-api-key:latest" \
  --set-secrets="ANTHROPIC_API_KEY=anthropic-api-key:latest" \
  --set-secrets="DATABASE_PASSWORD=database-password:latest" \
  --memory=1Gi \
  --cpu=1 \
  --min-instances=0 \
  --max-instances=3 \
  --port=8080
```

Note: The Cloud SQL Auth Proxy is built into Cloud Run when you use `--add-cloudsql-instances`. The Unix socket appears at `/cloudsql/<connection-name>`. The `?host=` parameter in the DB URL tells SQLAlchemy to use it.

For the DB password in the connection URL, update the env vars:
```
DATABASE_URL=postgresql+asyncpg://postgres:<PASSWORD>@/landrag?host=/cloudsql/$CLOUD_SQL_CONNECTION
DATABASE_URL_SYNC=postgresql+psycopg2://postgres:<PASSWORD>@/landrag?host=/cloudsql/$CLOUD_SQL_CONNECTION
```

Or better: modify `config.py` to build the URL from `DATABASE_PASSWORD` secret + known socket path. But for MVP, inline the password in the env var is simplest.

**Step 7: Verify deployment**

```bash
SERVICE_URL=$(gcloud run services describe landrag --region=$GCP_REGION --format='value(status.url)')
curl $SERVICE_URL/health
```

Expected: `{"status": "ok", "database": "ok"}`

**Step 8: Commit deploy script**

Create `scripts/deploy.sh` with the above commands (minus secrets) for repeatable deploys:

```bash
#!/bin/bash
set -e

GCP_PROJECT=${GCP_PROJECT:-landrag-mvp}
GCP_REGION=${GCP_REGION:-europe-west2}
CLOUD_SQL_CONNECTION=${CLOUD_SQL_CONNECTION:-$GCP_PROJECT:$GCP_REGION:landrag-db}

echo "Building and pushing image..."
gcloud builds submit --tag $GCP_REGION-docker.pkg.dev/$GCP_PROJECT/landrag/app:latest

echo "Deploying to Cloud Run..."
gcloud run deploy landrag \
  --image=$GCP_REGION-docker.pkg.dev/$GCP_PROJECT/landrag/app:latest \
  --region=$GCP_REGION \
  --platform=managed \
  --allow-unauthenticated \
  --add-cloudsql-instances=$CLOUD_SQL_CONNECTION \
  --port=8080

echo "Deployment complete!"
gcloud run services describe landrag --region=$GCP_REGION --format='value(status.url)'
```

```bash
git add scripts/deploy.sh
git commit -m "ops: add Cloud Run deploy script"
```

---

### Task 8: Scale ingestion and verify search

Before handing the app to testers, ingest a meaningful subset of data.

**Step 1: Run pipeline for all energy projects (or a subset)**

From local machine with `.env` configured and Cloud SQL accessible (either via Cloud SQL Auth Proxy locally or direct connection):

```bash
# If connecting to Cloud SQL from local:
# 1. Start Cloud SQL Auth Proxy: cloud-sql-proxy landrag-mvp:europe-west2:landrag-db
# 2. Update .env with DATABASE_URL pointing to localhost:5432

# Ingest all energy projects, 10 docs each (to keep it manageable for MVP)
.venv/Scripts/python -m landrag.cli --max-docs 10 --log-level INFO
```

Expected: Processes 174 energy projects, ~1740 documents max, thousands of chunks stored in Postgres + Pinecone.

**Step 2: Verify search works end-to-end**

```bash
curl -X POST $SERVICE_URL/v1/search \
  -H "Content-Type: application/json" \
  -d '{"query": "environmental impact of offshore wind", "limit": 5}'
```

Expected: JSON response with results containing relevant chunks, scores, project names, document titles.

**Step 3: Verify UI works**

Visit `$SERVICE_URL` in browser. Search for "biodiversity net gain". Verify results render with project names, document titles, and text snippets.
