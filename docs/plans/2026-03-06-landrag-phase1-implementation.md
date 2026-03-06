# landRAG Phase 1 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build the Phase 1 MVP — ingest PINS NSIP and appeal documents, expose semantic search with metadata filters through a server-rendered web UI.

**Architecture:** Python monorepo monolith. FastAPI serves both the API and Jinja2 templates. Celery workers handle async ingestion. Pinecone stores vectors, PostgreSQL stores structured data.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2.0, Alembic, Pinecone, Celery, Redis, Jinja2, pypdf, pytesseract, BeautifulSoup, rank-bm25, OpenAI embeddings, Cohere Rerank, pydantic-settings, Docker Compose, pytest.

**Design doc:** `docs/plans/2026-03-06-landrag-architecture-design.md`

---

### Task 1: Project Scaffolding

**Files:**
- Create: `pyproject.toml`
- Create: `src/landrag/__init__.py`
- Create: `src/landrag/core/__init__.py`
- Create: `src/landrag/core/config.py`
- Create: `.env.example`
- Create: `docker-compose.yml`
- Create: `Dockerfile`
- Create: `.gitignore`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`

**Step 1: Create pyproject.toml**

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "landrag"
version = "0.1.0"
description = "Semantic search and RAG platform for UK planning documents"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.34.0",
    "sqlalchemy[asyncio]>=2.0.0",
    "alembic>=1.14.0",
    "asyncpg>=0.30.0",
    "psycopg2-binary>=2.9.0",
    "pinecone>=6.0.0",
    "celery[redis]>=5.4.0",
    "redis>=5.0.0",
    "jinja2>=3.1.0",
    "pydantic-settings>=2.0.0",
    "openai>=1.60.0",
    "cohere>=5.0.0",
    "pypdf>=5.0.0",
    "pytesseract>=0.3.0",
    "beautifulsoup4>=4.12.0",
    "python-docx>=1.1.0",
    "rank-bm25>=0.2.0",
    "httpx>=0.28.0",
    "tiktoken>=0.8.0",
    "google-cloud-storage>=2.18.0",
    "anthropic>=0.42.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.24.0",
    "pytest-cov>=6.0.0",
    "httpx>=0.28.0",
    "ruff>=0.8.0",
    "mypy>=1.13.0",
    "factory-boy>=3.3.0",
]

[tool.ruff]
target-version = "py312"
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "UP"]

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
markers = [
    "evaluation: retrieval quality evaluation tests (run manually)",
]

[tool.mypy]
python_version = "3.12"
strict = true
plugins = []
```

**Step 2: Create .gitignore**

```
__pycache__/
*.py[cod]
*$py.class
*.egg-info/
dist/
build/
.eggs/
*.egg
.env
.venv/
venv/
*.db
.mypy_cache/
.pytest_cache/
.ruff_cache/
.coverage
htmlcov/
```

**Step 3: Create .env.example**

```env
# Database
DATABASE_URL=postgresql+asyncpg://landrag:landrag@localhost:5432/landrag
DATABASE_URL_SYNC=postgresql+psycopg2://landrag:landrag@localhost:5432/landrag

# Redis
REDIS_URL=redis://localhost:6379/0

# Pinecone
PINECONE_API_KEY=your-pinecone-api-key
PINECONE_INDEX_NAME=landrag-dev

# OpenAI (embeddings)
OPENAI_API_KEY=your-openai-api-key

# Cohere (reranking)
COHERE_API_KEY=your-cohere-api-key

# Anthropic (metadata classification)
ANTHROPIC_API_KEY=your-anthropic-api-key

# GCS
GCS_BUCKET_NAME=landrag-documents

# App
APP_ENV=development
LOG_LEVEL=INFO
```

**Step 4: Create docker-compose.yml**

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

  redis:
    image: redis:7
    ports:
      - "6379:6379"
    volumes:
      - redisdata:/data

volumes:
  pgdata:
  redisdata:
```

**Step 5: Create Dockerfile**

```dockerfile
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir .

COPY src/ src/
COPY alembic/ alembic/
COPY alembic.ini .

EXPOSE 8000
CMD ["uvicorn", "landrag.api.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
```

**Step 6: Create config module**

`src/landrag/__init__.py` — empty file

`src/landrag/core/__init__.py` — empty file

`src/landrag/core/config.py`:
```python
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    # Database
    database_url: str = "postgresql+asyncpg://landrag:landrag@localhost:5432/landrag"
    database_url_sync: str = "postgresql+psycopg2://landrag:landrag@localhost:5432/landrag"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Pinecone
    pinecone_api_key: str = ""
    pinecone_index_name: str = "landrag-dev"

    # OpenAI
    openai_api_key: str = ""

    # Cohere
    cohere_api_key: str = ""

    # Anthropic
    anthropic_api_key: str = ""

    # GCS
    gcs_bucket_name: str = "landrag-documents"

    # App
    app_env: str = "development"
    log_level: str = "INFO"


def get_settings() -> Settings:
    return Settings()
```

**Step 7: Create test scaffold**

`tests/__init__.py` — empty file

`tests/conftest.py`:
```python
import pytest

from landrag.core.config import Settings


@pytest.fixture
def settings() -> Settings:
    return Settings(
        database_url="postgresql+asyncpg://landrag:landrag@localhost:5432/landrag_test",
        database_url_sync="postgresql+psycopg2://landrag:landrag@localhost:5432/landrag_test",
        pinecone_api_key="test-key",
        pinecone_index_name="landrag-test",
        openai_api_key="test-key",
        cohere_api_key="test-key",
        anthropic_api_key="test-key",
    )
```

**Step 8: Write test for config**

`tests/core/__init__.py` — empty file

`tests/core/test_config.py`:
```python
from landrag.core.config import Settings, get_settings


def test_settings_defaults():
    s = Settings(
        pinecone_api_key="k",
        openai_api_key="k",
        cohere_api_key="k",
        anthropic_api_key="k",
    )
    assert s.app_env == "development"
    assert s.pinecone_index_name == "landrag-dev"
    assert "5432" in s.database_url


def test_get_settings_returns_instance():
    s = get_settings()
    assert isinstance(s, Settings)
```

**Step 9: Install and run tests**

Run:
```bash
pip install -e ".[dev]"
pytest tests/core/test_config.py -v
```
Expected: 2 PASS

**Step 10: Commit**

```bash
git add -A
git commit -m "feat: project scaffolding with config, docker-compose, and test setup"
```

---

### Task 2: Enums and Pydantic Schemas

**Files:**
- Create: `src/landrag/models/__init__.py`
- Create: `src/landrag/models/enums.py`
- Create: `src/landrag/models/schemas.py`
- Create: `tests/models/__init__.py`
- Create: `tests/models/test_enums.py`
- Create: `tests/models/test_schemas.py`

**Step 1: Write tests for enums**

`tests/models/__init__.py` — empty file

`tests/models/test_enums.py`:
```python
from landrag.models.enums import (
    DecisionOutcome,
    DocumentType,
    JobStatus,
    ProjectType,
    SourcePortal,
    Topic,
)


def test_project_type_values():
    assert ProjectType.ONSHORE_WIND.value == "onshore_wind"
    assert ProjectType.SOLAR.value == "solar"
    assert ProjectType.BATTERY_STORAGE.value == "battery_storage"


def test_topic_values():
    assert Topic.NOISE.value == "noise"
    assert Topic.ECOLOGY.value == "ecology"
    assert Topic.LANDSCAPE.value == "landscape"


def test_document_type_values():
    assert DocumentType.DECISION_LETTER.value == "decision_letter"
    assert DocumentType.EIA_CHAPTER.value == "eia_chapter"


def test_source_portal_values():
    assert SourcePortal.PINS.value == "pins"
    assert SourcePortal.LPA.value == "lpa"


def test_decision_outcome_values():
    assert DecisionOutcome.GRANTED.value == "granted"
    assert DecisionOutcome.REFUSED.value == "refused"


def test_job_status_values():
    assert JobStatus.PENDING.value == "pending"
    assert JobStatus.RUNNING.value == "running"
    assert JobStatus.COMPLETED.value == "completed"
    assert JobStatus.FAILED.value == "failed"
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/models/test_enums.py -v`
Expected: FAIL (module not found)

**Step 3: Implement enums**

`src/landrag/models/__init__.py` — empty file

`src/landrag/models/enums.py`:
```python
from enum import Enum


class ProjectType(str, Enum):
    ONSHORE_WIND = "onshore_wind"
    OFFSHORE_WIND = "offshore_wind"
    SOLAR = "solar"
    BATTERY_STORAGE = "battery_storage"
    GAS_PEAKER = "gas_peaker"
    TRANSMISSION = "transmission"
    HYDROGEN = "hydrogen"
    CCUS = "ccus"
    OTHER = "other"


class DocumentType(str, Enum):
    DECISION_LETTER = "decision_letter"
    EIA_CHAPTER = "eia_chapter"
    INSPECTOR_REPORT = "inspector_report"
    CONSULTATION_RESPONSE = "consultation_response"
    POLICY_STATEMENT = "policy_statement"
    GUIDANCE = "guidance"


class Topic(str, Enum):
    NOISE = "noise"
    ECOLOGY = "ecology"
    LANDSCAPE = "landscape"
    TRAFFIC = "traffic"
    CULTURAL_HERITAGE = "cultural_heritage"
    FLOOD_RISK = "flood_risk"
    AIR_QUALITY = "air_quality"
    SOCIOECONOMIC = "socioeconomic"
    GRID = "grid"
    CUMULATIVE_IMPACT = "cumulative_impact"
    DECOMMISSIONING = "decommissioning"
    CONSTRUCTION = "construction"


class SourcePortal(str, Enum):
    PINS = "pins"
    LPA = "lpa"
    EA = "ea"
    NE = "ne"
    GOV = "gov"


class DecisionOutcome(str, Enum):
    GRANTED = "granted"
    REFUSED = "refused"
    WITHDRAWN = "withdrawn"
    PENDING = "pending"


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/models/test_enums.py -v`
Expected: 6 PASS

**Step 5: Write tests for Pydantic schemas**

`tests/models/test_schemas.py`:
```python
import pytest
from pydantic import ValidationError

from landrag.models.enums import DecisionOutcome, DocumentType, ProjectType, Topic
from landrag.models.schemas import SearchFilters, SearchRequest, SearchResponse, ChunkResult


def test_search_request_minimal():
    req = SearchRequest(query="noise conditions on wind farms")
    assert req.query == "noise conditions on wind farms"
    assert req.filters is None
    assert req.limit == 10


def test_search_request_with_filters():
    req = SearchRequest(
        query="noise conditions",
        filters=SearchFilters(
            project_type=[ProjectType.ONSHORE_WIND],
            topic=[Topic.NOISE],
            decision=[DecisionOutcome.GRANTED],
        ),
        limit=20,
    )
    assert req.filters.project_type == [ProjectType.ONSHORE_WIND]
    assert req.limit == 20


def test_search_request_limit_max():
    req = SearchRequest(query="test", limit=50)
    assert req.limit == 50


def test_search_request_limit_exceeds_max():
    with pytest.raises(ValidationError):
        SearchRequest(query="test", limit=51)


def test_search_request_empty_query():
    with pytest.raises(ValidationError):
        SearchRequest(query="")


def test_search_response_structure():
    resp = SearchResponse(
        results=[
            ChunkResult(
                chunk_id="abc-123",
                content="Sample text about noise",
                score=0.95,
                highlight="Sample text about **noise**",
                document_title="Decision Letter",
                document_type=DocumentType.DECISION_LETTER,
                project_name="Wind Farm X",
                project_reference="EN010099",
                project_type=ProjectType.ONSHORE_WIND,
                topic=Topic.NOISE,
                source_url="https://example.com/doc.pdf",
                page_start=12,
                page_end=13,
            )
        ],
        total_estimate=1,
    )
    assert len(resp.results) == 1
    assert resp.results[0].score == 0.95
```

**Step 6: Run tests to verify they fail**

Run: `pytest tests/models/test_schemas.py -v`
Expected: FAIL (import error)

**Step 7: Implement schemas**

`src/landrag/models/schemas.py`:
```python
from pydantic import BaseModel, Field

from landrag.models.enums import DecisionOutcome, DocumentType, ProjectType, Topic


class DateRange(BaseModel):
    from_date: str
    to_date: str


class CapacityRange(BaseModel):
    min: float
    max: float


class SearchFilters(BaseModel):
    project_type: list[ProjectType] | None = None
    topic: list[Topic] | None = None
    document_type: list[DocumentType] | None = None
    decision: list[DecisionOutcome] | None = None
    date_range: DateRange | None = None
    region: list[str] | None = None
    capacity_mw_range: CapacityRange | None = None


class SearchRequest(BaseModel):
    query: str = Field(min_length=1)
    filters: SearchFilters | None = None
    limit: int = Field(default=10, ge=1, le=50)


class ChunkResult(BaseModel):
    chunk_id: str
    content: str
    score: float
    highlight: str
    document_title: str
    document_type: DocumentType
    project_name: str
    project_reference: str
    project_type: ProjectType
    topic: Topic | None = None
    source_url: str
    page_start: int | None = None
    page_end: int | None = None


class SearchResponse(BaseModel):
    results: list[ChunkResult]
    total_estimate: int
```

**Step 8: Run tests to verify they pass**

Run: `pytest tests/models/test_schemas.py -v`
Expected: 6 PASS

**Step 9: Commit**

```bash
git add -A
git commit -m "feat: add enums and Pydantic schemas for search API"
```

---

### Task 3: Database Models and Migrations

**Files:**
- Create: `src/landrag/core/db.py`
- Create: `src/landrag/models/database.py`
- Create: `alembic.ini`
- Create: `alembic/env.py`
- Create: `alembic/script.py.mako`
- Create: `alembic/versions/` (directory)
- Create: `tests/models/test_database.py`

**Step 1: Write test for SQLAlchemy models**

`tests/models/test_database.py`:
```python
from uuid import uuid4
from datetime import datetime, date, UTC

from landrag.models.database import Project, Document, Chunk, IngestionJob
from landrag.models.enums import (
    ProjectType,
    DocumentType,
    SourcePortal,
    DecisionOutcome,
    JobStatus,
    Topic,
)


def test_project_model_fields():
    p = Project(
        id=uuid4(),
        name="Test Wind Farm",
        reference="EN010099",
        type=ProjectType.ONSHORE_WIND,
        local_authority="Test Council",
        region="East Midlands",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    assert p.name == "Test Wind Farm"
    assert p.type == ProjectType.ONSHORE_WIND
    assert p.capacity_mw is None


def test_document_model_fields():
    d = Document(
        id=uuid4(),
        project_id=uuid4(),
        title="Decision Letter",
        type=DocumentType.DECISION_LETTER,
        file_format="pdf",
        source_url="https://example.com/doc.pdf",
        source_portal=SourcePortal.PINS,
        retrieved_at=datetime.now(UTC),
        storage_path="gs://bucket/doc.pdf",
        created_at=datetime.now(UTC),
    )
    assert d.type == DocumentType.DECISION_LETTER
    assert d.date_published is None


def test_chunk_model_fields():
    c = Chunk(
        id=uuid4(),
        document_id=uuid4(),
        content="This is a chunk of text about noise conditions.",
        chunk_index=0,
        pinecone_id="vec-abc-123",
        created_at=datetime.now(UTC),
    )
    assert c.chunk_index == 0
    assert c.topic is None


def test_ingestion_job_model_fields():
    j = IngestionJob(
        id=uuid4(),
        source_portal=SourcePortal.PINS,
        status=JobStatus.PENDING,
        created_at=datetime.now(UTC),
    )
    assert j.status == JobStatus.PENDING
    assert j.documents_found is None
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/models/test_database.py -v`
Expected: FAIL (import error)

**Step 3: Create database session factory**

`src/landrag/core/db.py`:
```python
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from landrag.core.config import get_settings


def get_async_engine():
    settings = get_settings()
    return create_async_engine(settings.database_url, echo=settings.app_env == "development")


def get_async_session_factory() -> async_sessionmaker[AsyncSession]:
    engine = get_async_engine()
    return async_sessionmaker(engine, expire_on_commit=False)


def get_sync_engine():
    settings = get_settings()
    return create_engine(settings.database_url_sync, echo=settings.app_env == "development")


def get_sync_session_factory() -> sessionmaker:
    engine = get_sync_engine()
    return sessionmaker(engine)
```

**Step 4: Implement database models**

`src/landrag/models/database.py`:
```python
import uuid
from datetime import datetime, UTC

from sqlalchemy import (
    String,
    Text,
    Float,
    Integer,
    Boolean,
    DateTime,
    Date,
    ForeignKey,
    ARRAY,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(500))
    reference: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    type: Mapped[str] = mapped_column(String(50))
    local_authority: Mapped[str] = mapped_column(String(200))
    region: Mapped[str] = mapped_column(String(100))
    coordinates: Mapped[list[float] | None] = mapped_column(ARRAY(Float), nullable=True)
    capacity_mw: Mapped[float | None] = mapped_column(Float, nullable=True)
    decision: Mapped[str | None] = mapped_column(String(20), nullable=True)
    decision_date: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    documents: Mapped[list["Document"]] = relationship(back_populates="project")


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id"))
    title: Mapped[str] = mapped_column(String(1000))
    type: Mapped[str] = mapped_column(String(50))
    date_published: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    file_format: Mapped[str] = mapped_column(String(10))
    source_url: Mapped[str] = mapped_column(Text)
    source_portal: Mapped[str] = mapped_column(String(20))
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    storage_path: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    project: Mapped["Project"] = relationship(back_populates="documents")
    chunks: Mapped[list["Chunk"]] = relationship(back_populates="document")


class Chunk(Base):
    __tablename__ = "chunks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("documents.id"))
    content: Mapped[str] = mapped_column(Text)
    chunk_index: Mapped[int] = mapped_column(Integer)
    topic: Mapped[str | None] = mapped_column(String(50), nullable=True)
    chapter_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    page_start: Mapped[int | None] = mapped_column(Integer, nullable=True)
    page_end: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pinecone_id: Mapped[str] = mapped_column(String(100), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    document: Mapped["Document"] = relationship(back_populates="chunks")


class IngestionJob(Base):
    __tablename__ = "ingestion_jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_portal: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20), default="pending")
    documents_found: Mapped[int | None] = mapped_column(Integer, nullable=True)
    documents_processed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
```

**Step 5: Run tests to verify they pass**

Run: `pytest tests/models/test_database.py -v`
Expected: 4 PASS

**Step 6: Initialize Alembic**

Run:
```bash
alembic init alembic
```

Then edit `alembic.ini` — set `sqlalchemy.url` to empty (we'll override in env.py).

Edit `alembic/env.py` to import our models and read config:

`alembic/env.py`:
```python
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from landrag.core.config import get_settings
from landrag.models.database import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_url() -> str:
    return get_settings().database_url_sync


def run_migrations_offline() -> None:
    url = get_url()
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = get_url()
    connectable = engine_from_config(configuration, prefix="sqlalchemy.", poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

**Step 7: Generate initial migration**

Run (with docker-compose postgres running):
```bash
docker compose up -d postgres
alembic revision --autogenerate -m "initial schema"
```

**Step 8: Apply migration**

Run:
```bash
alembic upgrade head
```

**Step 9: Commit**

```bash
git add -A
git commit -m "feat: add SQLAlchemy models, Alembic migrations, and database setup"
```

---

### Task 4: Pinecone Client Setup

**Files:**
- Create: `src/landrag/core/pinecone.py`
- Create: `tests/core/test_pinecone.py`

**Step 1: Write test for Pinecone client factory**

`tests/core/test_pinecone.py`:
```python
from unittest.mock import patch, MagicMock

from landrag.core.pinecone import get_pinecone_index, build_metadata_filter
from landrag.models.enums import ProjectType, Topic, DecisionOutcome
from landrag.models.schemas import SearchFilters, DateRange


def test_build_metadata_filter_empty():
    result = build_metadata_filter(None)
    assert result == {}


def test_build_metadata_filter_project_type():
    filters = SearchFilters(project_type=[ProjectType.ONSHORE_WIND, ProjectType.SOLAR])
    result = build_metadata_filter(filters)
    assert result["project_type"] == {"$in": ["onshore_wind", "solar"]}


def test_build_metadata_filter_topic():
    filters = SearchFilters(topic=[Topic.NOISE])
    result = build_metadata_filter(filters)
    assert result["topic"] == {"$in": ["noise"]}


def test_build_metadata_filter_decision():
    filters = SearchFilters(decision=[DecisionOutcome.GRANTED])
    result = build_metadata_filter(filters)
    assert result["decision"] == {"$in": ["granted"]}


def test_build_metadata_filter_date_range():
    filters = SearchFilters(date_range=DateRange(from_date="2022-01-01", to_date="2024-12-31"))
    result = build_metadata_filter(filters)
    assert result["date_published"]["$gte"] == "2022-01-01"
    assert result["date_published"]["$lte"] == "2024-12-31"


def test_build_metadata_filter_combined():
    filters = SearchFilters(
        project_type=[ProjectType.SOLAR],
        topic=[Topic.NOISE, Topic.ECOLOGY],
        decision=[DecisionOutcome.GRANTED],
    )
    result = build_metadata_filter(filters)
    assert "project_type" in result
    assert "topic" in result
    assert "decision" in result
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/core/test_pinecone.py -v`
Expected: FAIL (import error)

**Step 3: Implement Pinecone client and filter builder**

`src/landrag/core/pinecone.py`:
```python
from pinecone import Pinecone

from landrag.core.config import get_settings
from landrag.models.schemas import SearchFilters


def get_pinecone_index():
    settings = get_settings()
    pc = Pinecone(api_key=settings.pinecone_api_key)
    return pc.Index(settings.pinecone_index_name)


def build_metadata_filter(filters: SearchFilters | None) -> dict:
    if filters is None:
        return {}

    pinecone_filter: dict = {}

    if filters.project_type:
        pinecone_filter["project_type"] = {"$in": [t.value for t in filters.project_type]}

    if filters.topic:
        pinecone_filter["topic"] = {"$in": [t.value for t in filters.topic]}

    if filters.document_type:
        pinecone_filter["document_type"] = {"$in": [t.value for t in filters.document_type]}

    if filters.decision:
        pinecone_filter["decision"] = {"$in": [d.value for d in filters.decision]}

    if filters.date_range:
        pinecone_filter["date_published"] = {
            "$gte": filters.date_range.from_date,
            "$lte": filters.date_range.to_date,
        }

    if filters.region:
        pinecone_filter["region"] = {"$in": filters.region}

    if filters.capacity_mw_range:
        pinecone_filter["capacity_mw"] = {
            "$gte": filters.capacity_mw_range.min,
            "$lte": filters.capacity_mw_range.max,
        }

    return pinecone_filter
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/core/test_pinecone.py -v`
Expected: 6 PASS

**Step 5: Commit**

```bash
git add -A
git commit -m "feat: add Pinecone client setup and metadata filter builder"
```

---

### Task 5: Text Extraction (Parsers)

**Files:**
- Create: `src/landrag/ingestion/__init__.py`
- Create: `src/landrag/ingestion/parsers/__init__.py`
- Create: `src/landrag/ingestion/parsers/pdf.py`
- Create: `src/landrag/ingestion/parsers/html.py`
- Create: `src/landrag/ingestion/parsers/docx.py`
- Create: `tests/ingestion/__init__.py`
- Create: `tests/ingestion/parsers/__init__.py`
- Create: `tests/ingestion/parsers/test_pdf.py`
- Create: `tests/ingestion/parsers/test_html.py`
- Create: `tests/ingestion/parsers/test_docx.py`
- Create: `tests/fixtures/` (test PDFs, HTML, docx)

**Step 1: Write tests for HTML parser**

`tests/ingestion/__init__.py` — empty
`tests/ingestion/parsers/__init__.py` — empty

`tests/ingestion/parsers/test_html.py`:
```python
from landrag.ingestion.parsers.html import extract_html


def test_extract_html_basic():
    html = "<html><body><h1>Title</h1><p>Paragraph one.</p><p>Paragraph two.</p></body></html>"
    result = extract_html(html)
    assert "Title" in result.text
    assert "Paragraph one." in result.text
    assert "Paragraph two." in result.text


def test_extract_html_strips_scripts_and_styles():
    html = "<html><head><style>body{color:red}</style></head><body><script>alert(1)</script><p>Content</p></body></html>"
    result = extract_html(html)
    assert "alert" not in result.text
    assert "color:red" not in result.text
    assert "Content" in result.text


def test_extract_html_preserves_structure():
    html = "<html><body><h2>Section 1</h2><p>Text.</p><h2>Section 2</h2><p>More text.</p></body></html>"
    result = extract_html(html)
    assert result.sections is not None
    assert len(result.sections) >= 2
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/ingestion/parsers/test_html.py -v`
Expected: FAIL

**Step 3: Implement HTML parser**

`src/landrag/ingestion/__init__.py` — empty
`src/landrag/ingestion/parsers/__init__.py` — empty

`src/landrag/ingestion/parsers/html.py`:
```python
from dataclasses import dataclass, field

from bs4 import BeautifulSoup


@dataclass
class ParsedSection:
    heading: str
    content: str


@dataclass
class ParsedDocument:
    text: str
    sections: list[ParsedSection] = field(default_factory=list)
    page_count: int | None = None


def extract_html(html_content: str) -> ParsedDocument:
    soup = BeautifulSoup(html_content, "html.parser")

    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()

    sections: list[ParsedSection] = []
    headings = soup.find_all(["h1", "h2", "h3", "h4"])

    for heading in headings:
        heading_text = heading.get_text(strip=True)
        content_parts: list[str] = []
        for sibling in heading.find_next_siblings():
            if sibling.name in ["h1", "h2", "h3", "h4"]:
                break
            content_parts.append(sibling.get_text(strip=True))
        sections.append(ParsedSection(heading=heading_text, content="\n".join(content_parts)))

    full_text = soup.get_text(separator="\n", strip=True)

    return ParsedDocument(text=full_text, sections=sections)
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/ingestion/parsers/test_html.py -v`
Expected: 3 PASS

**Step 5: Write tests for PDF parser**

Create a minimal test PDF fixture first. For unit tests, we mock pypdf.

`tests/ingestion/parsers/test_pdf.py`:
```python
from unittest.mock import MagicMock, patch

from landrag.ingestion.parsers.pdf import extract_pdf, PdfQualityResult


def _mock_pdf_reader(pages: list[str]):
    reader = MagicMock()
    mock_pages = []
    for text in pages:
        page = MagicMock()
        page.extract_text.return_value = text
        mock_pages.append(page)
    reader.pages = mock_pages
    return reader


@patch("landrag.ingestion.parsers.pdf.PdfReader")
def test_extract_pdf_native(mock_reader_cls):
    mock_reader_cls.return_value = _mock_pdf_reader(["Page one content.", "Page two content."])
    result = extract_pdf("/fake/path.pdf")
    assert "Page one content." in result.text
    assert "Page two content." in result.text
    assert result.page_count == 2


@patch("landrag.ingestion.parsers.pdf.PdfReader")
def test_extract_pdf_detects_low_quality(mock_reader_cls):
    mock_reader_cls.return_value = _mock_pdf_reader(["", "  ", "x"])
    result = extract_pdf("/fake/path.pdf")
    assert result.quality == PdfQualityResult.LOW


@patch("landrag.ingestion.parsers.pdf.PdfReader")
def test_extract_pdf_good_quality(mock_reader_cls):
    mock_reader_cls.return_value = _mock_pdf_reader(["A" * 200, "B" * 200])
    result = extract_pdf("/fake/path.pdf")
    assert result.quality == PdfQualityResult.GOOD
```

**Step 6: Run tests to verify they fail**

Run: `pytest tests/ingestion/parsers/test_pdf.py -v`
Expected: FAIL

**Step 7: Implement PDF parser**

`src/landrag/ingestion/parsers/pdf.py`:
```python
from enum import Enum

from pypdf import PdfReader

from landrag.ingestion.parsers.html import ParsedDocument


class PdfQualityResult(str, Enum):
    GOOD = "good"
    LOW = "low"


class PdfExtractResult(ParsedDocument):
    quality: PdfQualityResult = PdfQualityResult.GOOD


MIN_CHARS_PER_PAGE = 50


def extract_pdf(file_path: str) -> PdfExtractResult:
    reader = PdfReader(file_path)
    pages_text: list[str] = []

    for page in reader.pages:
        text = page.extract_text() or ""
        pages_text.append(text)

    full_text = "\n".join(pages_text)
    page_count = len(reader.pages)

    non_empty_pages = sum(1 for t in pages_text if len(t.strip()) >= MIN_CHARS_PER_PAGE)
    quality = (
        PdfQualityResult.GOOD
        if page_count == 0 or non_empty_pages / page_count > 0.5
        else PdfQualityResult.LOW
    )

    return PdfExtractResult(text=full_text, page_count=page_count, quality=quality)
```

**Step 8: Run tests to verify they pass**

Run: `pytest tests/ingestion/parsers/test_pdf.py -v`
Expected: 3 PASS

**Step 9: Write tests for DOCX parser**

`tests/ingestion/parsers/test_docx.py`:
```python
from unittest.mock import MagicMock, patch

from landrag.ingestion.parsers.docx import extract_docx


def _mock_docx_document(paragraphs: list[tuple[str, str]]):
    """paragraphs: list of (style_name, text) tuples"""
    doc = MagicMock()
    mock_paras = []
    for style_name, text in paragraphs:
        para = MagicMock()
        para.text = text
        para.style.name = style_name
        mock_paras.append(para)
    doc.paragraphs = mock_paras
    return doc


@patch("landrag.ingestion.parsers.docx.DocxDocument")
def test_extract_docx_basic(mock_docx_cls):
    mock_docx_cls.return_value = _mock_docx_document([
        ("Normal", "First paragraph."),
        ("Normal", "Second paragraph."),
    ])
    result = extract_docx("/fake/path.docx")
    assert "First paragraph." in result.text
    assert "Second paragraph." in result.text


@patch("landrag.ingestion.parsers.docx.DocxDocument")
def test_extract_docx_with_headings(mock_docx_cls):
    mock_docx_cls.return_value = _mock_docx_document([
        ("Heading 1", "Section One"),
        ("Normal", "Content of section one."),
        ("Heading 1", "Section Two"),
        ("Normal", "Content of section two."),
    ])
    result = extract_docx("/fake/path.docx")
    assert len(result.sections) == 2
    assert result.sections[0].heading == "Section One"
```

**Step 10: Run tests to verify they fail**

Run: `pytest tests/ingestion/parsers/test_docx.py -v`
Expected: FAIL

**Step 11: Implement DOCX parser**

`src/landrag/ingestion/parsers/docx.py`:
```python
from docx import Document as DocxDocument

from landrag.ingestion.parsers.html import ParsedDocument, ParsedSection


def extract_docx(file_path: str) -> ParsedDocument:
    doc = DocxDocument(file_path)

    text_parts: list[str] = []
    sections: list[ParsedSection] = []
    current_heading: str | None = None
    current_content: list[str] = []

    for para in doc.paragraphs:
        text_parts.append(para.text)

        if para.style.name.startswith("Heading"):
            if current_heading is not None:
                sections.append(
                    ParsedSection(heading=current_heading, content="\n".join(current_content))
                )
            current_heading = para.text
            current_content = []
        elif current_heading is not None:
            current_content.append(para.text)

    if current_heading is not None:
        sections.append(ParsedSection(heading=current_heading, content="\n".join(current_content)))

    return ParsedDocument(text="\n".join(text_parts), sections=sections)
```

**Step 12: Run tests to verify they pass**

Run: `pytest tests/ingestion/parsers/test_docx.py -v`
Expected: 2 PASS

**Step 13: Commit**

```bash
git add -A
git commit -m "feat: add text extraction parsers for PDF, HTML, and DOCX"
```

---

### Task 6: Chunking

**Files:**
- Create: `src/landrag/ingestion/chunker.py`
- Create: `tests/ingestion/test_chunker.py`

**Step 1: Write tests for chunker**

`tests/ingestion/test_chunker.py`:
```python
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
    # No chunk should contain a split mid-sentence from different paragraphs
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
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/ingestion/test_chunker.py -v`
Expected: FAIL

**Step 3: Implement chunker**

`src/landrag/ingestion/chunker.py`:
```python
from dataclasses import dataclass

import tiktoken

from landrag.ingestion.parsers.html import ParsedDocument


@dataclass
class ChunkConfig:
    max_tokens: int = 512
    overlap_tokens: int = 64


@dataclass
class TextChunk:
    text: str
    chunk_index: int
    section_heading: str | None = None


_encoder = tiktoken.get_encoding("cl100k_base")


def _count_tokens(text: str) -> int:
    return len(_encoder.encode(text))


def _split_into_paragraphs(text: str) -> list[str]:
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if not paragraphs:
        paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
    return paragraphs if paragraphs else [text]


def _chunk_text(text: str, config: ChunkConfig, start_index: int, heading: str | None = None) -> list[TextChunk]:
    if _count_tokens(text) <= config.max_tokens:
        return [TextChunk(text=text, chunk_index=start_index, section_heading=heading)]

    paragraphs = _split_into_paragraphs(text)
    chunks: list[TextChunk] = []
    current_parts: list[str] = []
    current_tokens = 0
    idx = start_index

    for para in paragraphs:
        para_tokens = _count_tokens(para)

        if current_tokens + para_tokens > config.max_tokens and current_parts:
            chunks.append(TextChunk(
                text="\n\n".join(current_parts),
                chunk_index=idx,
                section_heading=heading,
            ))
            idx += 1

            # Overlap: keep last paragraph(s) up to overlap_tokens
            overlap_parts: list[str] = []
            overlap_tokens = 0
            for p in reversed(current_parts):
                p_tokens = _count_tokens(p)
                if overlap_tokens + p_tokens > config.overlap_tokens:
                    break
                overlap_parts.insert(0, p)
                overlap_tokens += p_tokens

            current_parts = overlap_parts
            current_tokens = overlap_tokens

        current_parts.append(para)
        current_tokens += para_tokens

    if current_parts:
        chunks.append(TextChunk(
            text="\n\n".join(current_parts),
            chunk_index=idx,
            section_heading=heading,
        ))

    return chunks


def chunk_document(doc: ParsedDocument, config: ChunkConfig | None = None) -> list[TextChunk]:
    if config is None:
        config = ChunkConfig()

    # If sections are available, chunk by section
    if doc.sections:
        chunks: list[TextChunk] = []
        idx = 0
        for section in doc.sections:
            section_text = f"{section.heading}\n\n{section.content}" if section.content else section.heading
            section_chunks = _chunk_text(section_text, config, idx, heading=section.heading)
            chunks.extend(section_chunks)
            idx += len(section_chunks)
        return chunks

    # Fallback: fixed-size chunking on full text
    return _chunk_text(doc.text, config, start_index=0)
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/ingestion/test_chunker.py -v`
Expected: 5 PASS

**Step 5: Commit**

```bash
git add -A
git commit -m "feat: add semantic and fixed-size document chunker"
```

---

### Task 7: Embedding

**Files:**
- Create: `src/landrag/ingestion/embedder.py`
- Create: `tests/ingestion/test_embedder.py`

**Step 1: Write tests for embedder**

`tests/ingestion/test_embedder.py`:
```python
from unittest.mock import MagicMock, patch

from landrag.ingestion.embedder import embed_texts, embed_query


@patch("landrag.ingestion.embedder.get_openai_client")
def test_embed_texts_returns_vectors(mock_get_client):
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.data = [
        MagicMock(embedding=[0.1] * 3072, index=0),
        MagicMock(embedding=[0.2] * 3072, index=1),
    ]
    mock_client.embeddings.create.return_value = mock_response
    mock_get_client.return_value = mock_client

    results = embed_texts(["text one", "text two"])
    assert len(results) == 2
    assert len(results[0]) == 3072
    mock_client.embeddings.create.assert_called_once()


@patch("landrag.ingestion.embedder.get_openai_client")
def test_embed_query_returns_single_vector(mock_get_client):
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.data = [MagicMock(embedding=[0.5] * 3072, index=0)]
    mock_client.embeddings.create.return_value = mock_response
    mock_get_client.return_value = mock_client

    result = embed_query("noise conditions on wind farms")
    assert len(result) == 3072


@patch("landrag.ingestion.embedder.get_openai_client")
def test_embed_texts_batches_large_input(mock_get_client):
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.data = [MagicMock(embedding=[0.1] * 3072, index=i) for i in range(100)]
    mock_client.embeddings.create.return_value = mock_response
    mock_get_client.return_value = mock_client

    texts = [f"text {i}" for i in range(100)]
    results = embed_texts(texts)
    assert len(results) == 100
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/ingestion/test_embedder.py -v`
Expected: FAIL

**Step 3: Implement embedder**

`src/landrag/ingestion/embedder.py`:
```python
from openai import OpenAI

from landrag.core.config import get_settings

EMBEDDING_MODEL = "text-embedding-3-large"
BATCH_SIZE = 100


def get_openai_client() -> OpenAI:
    settings = get_settings()
    return OpenAI(api_key=settings.openai_api_key)


def embed_texts(texts: list[str]) -> list[list[float]]:
    client = get_openai_client()
    all_embeddings: list[list[float]] = [[] for _ in texts]

    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i : i + BATCH_SIZE]
        response = client.embeddings.create(model=EMBEDDING_MODEL, input=batch)
        for item in response.data:
            all_embeddings[i + item.index] = item.embedding

    return all_embeddings


def embed_query(query: str) -> list[float]:
    return embed_texts([query])[0]
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/ingestion/test_embedder.py -v`
Expected: 3 PASS

**Step 5: Commit**

```bash
git add -A
git commit -m "feat: add OpenAI text-embedding-3-large embedder"
```

---

### Task 8: Metadata Classifier

**Files:**
- Create: `src/landrag/ingestion/classifier.py`
- Create: `tests/ingestion/test_classifier.py`

**Step 1: Write tests for classifier**

`tests/ingestion/test_classifier.py`:
```python
from landrag.ingestion.classifier import extract_pins_reference, classify_project_type_from_path
from landrag.models.enums import ProjectType


def test_extract_pins_reference():
    assert extract_pins_reference("EN010012 - Hornsea Project") == "EN010012"
    assert extract_pins_reference("Application EN020024 details") == "EN020024"
    assert extract_pins_reference("No reference here") is None


def test_classify_project_type_from_path():
    assert classify_project_type_from_path("wind-farm-decision.pdf") == ProjectType.ONSHORE_WIND
    assert classify_project_type_from_path("solar-park-eia.pdf") == ProjectType.SOLAR
    assert classify_project_type_from_path("battery-storage-report.pdf") == ProjectType.BATTERY_STORAGE
    assert classify_project_type_from_path("random-document.pdf") is None
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/ingestion/test_classifier.py -v`
Expected: FAIL

**Step 3: Implement rule-based classifiers**

`src/landrag/ingestion/classifier.py`:
```python
import re

from anthropic import Anthropic

from landrag.core.config import get_settings
from landrag.models.enums import ProjectType, Topic

_PINS_REF_PATTERN = re.compile(r"EN\d{6}")

_PROJECT_TYPE_KEYWORDS: dict[str, ProjectType] = {
    "wind": ProjectType.ONSHORE_WIND,
    "offshore-wind": ProjectType.OFFSHORE_WIND,
    "solar": ProjectType.SOLAR,
    "battery": ProjectType.BATTERY_STORAGE,
    "gas-peaker": ProjectType.GAS_PEAKER,
    "gas peaker": ProjectType.GAS_PEAKER,
    "transmission": ProjectType.TRANSMISSION,
    "hydrogen": ProjectType.HYDROGEN,
    "ccus": ProjectType.CCUS,
    "carbon capture": ProjectType.CCUS,
}


def extract_pins_reference(text: str) -> str | None:
    match = _PINS_REF_PATTERN.search(text)
    return match.group(0) if match else None


def classify_project_type_from_path(path: str) -> ProjectType | None:
    path_lower = path.lower()
    for keyword, project_type in _PROJECT_TYPE_KEYWORDS.items():
        if keyword in path_lower:
            return project_type
    return None


def classify_topic_llm(text: str) -> Topic | None:
    """Use Claude Haiku to classify the topic of a text chunk."""
    settings = get_settings()
    client = Anthropic(api_key=settings.anthropic_api_key)

    topics_list = ", ".join(t.value for t in Topic)

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=50,
        messages=[
            {
                "role": "user",
                "content": (
                    f"Classify the following planning document text into exactly one topic. "
                    f"Valid topics: {topics_list}. "
                    f"Respond with ONLY the topic value, nothing else. "
                    f"If none fit, respond with 'none'.\n\n"
                    f"Text: {text[:1000]}"
                ),
            }
        ],
    )

    result = response.content[0].text.strip().lower()
    try:
        return Topic(result)
    except ValueError:
        return None
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/ingestion/test_classifier.py -v`
Expected: 2 PASS

**Step 5: Commit**

```bash
git add -A
git commit -m "feat: add rule-based and LLM metadata classifiers"
```

---

### Task 9: Celery Worker Setup

**Files:**
- Create: `src/landrag/workers/__init__.py`
- Create: `src/landrag/workers/celery_app.py`
- Create: `src/landrag/workers/tasks.py`
- Create: `tests/workers/__init__.py`
- Create: `tests/workers/test_tasks.py`

**Step 1: Write test for task definitions**

`tests/workers/__init__.py` — empty

`tests/workers/test_tasks.py`:
```python
from unittest.mock import patch, MagicMock

from landrag.workers.tasks import parse_document, chunk_and_embed


@patch("landrag.workers.tasks.extract_pdf")
def test_parse_document_calls_pdf_parser(mock_extract):
    mock_extract.return_value = MagicMock(text="Extracted text", sections=[], page_count=5)
    result = parse_document("/fake/path.pdf", "pdf")
    mock_extract.assert_called_once_with("/fake/path.pdf")
    assert result["text"] == "Extracted text"
    assert result["page_count"] == 5


@patch("landrag.workers.tasks.extract_html")
def test_parse_document_calls_html_parser(mock_extract):
    mock_extract.return_value = MagicMock(text="HTML content", sections=[], page_count=None)
    result = parse_document("/fake/path.html", "html")
    mock_extract.assert_called_once()
    assert result["text"] == "HTML content"
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/workers/test_tasks.py -v`
Expected: FAIL

**Step 3: Implement Celery app and tasks**

`src/landrag/workers/__init__.py` — empty

`src/landrag/workers/celery_app.py`:
```python
from celery import Celery

from landrag.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "landrag",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_routes={
        "landrag.workers.tasks.scrape_*": {"queue": "scraping"},
        "landrag.workers.tasks.parse_*": {"queue": "parsing"},
        "landrag.workers.tasks.chunk_*": {"queue": "processing"},
        "landrag.workers.tasks.embed_*": {"queue": "embedding"},
    },
    task_default_rate_limit="10/m",
)

celery_app.autodiscover_tasks(["landrag.workers"])
```

`src/landrag/workers/tasks.py`:
```python
from landrag.workers.celery_app import celery_app
from landrag.ingestion.parsers.pdf import extract_pdf
from landrag.ingestion.parsers.html import extract_html, ParsedDocument
from landrag.ingestion.parsers.docx import extract_docx


@celery_app.task(name="landrag.workers.tasks.parse_document")
def parse_document(file_path: str, file_format: str) -> dict:
    if file_format == "pdf":
        result = extract_pdf(file_path)
    elif file_format == "html":
        with open(file_path) as f:
            result = extract_html(f.read())
    elif file_format == "docx":
        result = extract_docx(file_path)
    else:
        raise ValueError(f"Unsupported format: {file_format}")

    return {
        "text": result.text,
        "sections": [{"heading": s.heading, "content": s.content} for s in result.sections],
        "page_count": result.page_count,
    }


@celery_app.task(name="landrag.workers.tasks.chunk_and_embed")
def chunk_and_embed(parsed_data: dict, document_id: str) -> dict:
    from landrag.ingestion.chunker import chunk_document, TextChunk
    from landrag.ingestion.parsers.html import ParsedDocument, ParsedSection
    from landrag.ingestion.embedder import embed_texts

    doc = ParsedDocument(
        text=parsed_data["text"],
        sections=[
            ParsedSection(heading=s["heading"], content=s["content"])
            for s in parsed_data.get("sections", [])
        ],
        page_count=parsed_data.get("page_count"),
    )

    chunks = chunk_document(doc)
    texts = [c.text for c in chunks]
    embeddings = embed_texts(texts)

    return {
        "document_id": document_id,
        "chunk_count": len(chunks),
        "chunks": [
            {
                "text": c.text,
                "chunk_index": c.chunk_index,
                "section_heading": c.section_heading,
                "embedding": emb,
            }
            for c, emb in zip(chunks, embeddings)
        ],
    }
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/workers/test_tasks.py -v`
Expected: 2 PASS

**Step 5: Commit**

```bash
git add -A
git commit -m "feat: add Celery worker app and ingestion tasks"
```

---

### Task 10: Search & Retrieval

**Files:**
- Create: `src/landrag/search/__init__.py`
- Create: `src/landrag/search/retrieval.py`
- Create: `src/landrag/search/reranker.py`
- Create: `tests/search/__init__.py`
- Create: `tests/search/test_retrieval.py`
- Create: `tests/search/test_reranker.py`

**Step 1: Write tests for BM25 re-scoring**

`tests/search/__init__.py` — empty

`tests/search/test_retrieval.py`:
```python
from landrag.search.retrieval import bm25_rescore, combine_scores


def test_bm25_rescore():
    texts = [
        "Noise conditions on wind farms near dwellings",
        "Ecology survey of bat populations",
        "Traffic management during construction",
    ]
    query = "noise conditions wind farms"
    scores = bm25_rescore(texts, query)
    assert len(scores) == 3
    # The noise-related text should score highest
    assert scores[0] > scores[1]
    assert scores[0] > scores[2]


def test_combine_scores():
    dense_scores = [0.9, 0.7, 0.5]
    bm25_scores = [0.3, 0.8, 0.1]
    combined = combine_scores(dense_scores, bm25_scores, dense_weight=0.7, bm25_weight=0.3)
    assert len(combined) == 3
    # First: 0.9*0.7 + 0.3*0.3 = 0.72
    # Second: 0.7*0.7 + 0.8*0.3 = 0.73
    assert combined[1] > combined[0]  # BM25 boost pushes second higher
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/search/test_retrieval.py -v`
Expected: FAIL

**Step 3: Implement retrieval module**

`src/landrag/search/__init__.py` — empty

`src/landrag/search/retrieval.py`:
```python
from rank_bm25 import BM25Okapi


def bm25_rescore(texts: list[str], query: str) -> list[float]:
    tokenized_corpus = [doc.lower().split() for doc in texts]
    tokenized_query = query.lower().split()
    bm25 = BM25Okapi(tokenized_corpus)
    scores = bm25.get_scores(tokenized_query)
    return scores.tolist()


def combine_scores(
    dense_scores: list[float],
    bm25_scores: list[float],
    dense_weight: float = 0.7,
    bm25_weight: float = 0.3,
) -> list[float]:
    # Normalize BM25 scores to 0-1 range
    max_bm25 = max(bm25_scores) if bm25_scores and max(bm25_scores) > 0 else 1.0
    normalized_bm25 = [s / max_bm25 for s in bm25_scores]

    return [
        dense_weight * d + bm25_weight * b
        for d, b in zip(dense_scores, normalized_bm25)
    ]
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/search/test_retrieval.py -v`
Expected: 2 PASS

**Step 5: Write tests for reranker**

`tests/search/test_reranker.py`:
```python
from unittest.mock import MagicMock, patch

from landrag.search.reranker import rerank


@patch("landrag.search.reranker.get_cohere_client")
def test_rerank_returns_reordered_results(mock_get_client):
    mock_client = MagicMock()
    mock_result_0 = MagicMock()
    mock_result_0.index = 1
    mock_result_0.relevance_score = 0.95
    mock_result_1 = MagicMock()
    mock_result_1.index = 0
    mock_result_1.relevance_score = 0.80
    mock_response = MagicMock()
    mock_response.results = [mock_result_0, mock_result_1]
    mock_client.rerank.return_value = mock_response
    mock_get_client.return_value = mock_client

    texts = ["text about ecology", "text about noise conditions"]
    results = rerank("noise conditions", texts, top_n=2)
    assert len(results) == 2
    assert results[0]["index"] == 1  # noise text ranked first
    assert results[0]["score"] == 0.95
```

**Step 6: Run tests to verify they fail**

Run: `pytest tests/search/test_reranker.py -v`
Expected: FAIL

**Step 7: Implement reranker**

`src/landrag/search/reranker.py`:
```python
import cohere

from landrag.core.config import get_settings


def get_cohere_client() -> cohere.ClientV2:
    settings = get_settings()
    return cohere.ClientV2(api_key=settings.cohere_api_key)


def rerank(query: str, texts: list[str], top_n: int = 10) -> list[dict]:
    client = get_cohere_client()
    response = client.rerank(
        model="rerank-v3.5",
        query=query,
        documents=texts,
        top_n=top_n,
    )
    return [
        {"index": r.index, "score": r.relevance_score}
        for r in response.results
    ]
```

**Step 8: Run tests to verify they pass**

Run: `pytest tests/search/test_reranker.py -v`
Expected: 1 PASS

**Step 9: Commit**

```bash
git add -A
git commit -m "feat: add hybrid search retrieval with BM25 and Cohere reranker"
```

---

### Task 11: FastAPI App and Search Route

**Files:**
- Create: `src/landrag/api/__init__.py`
- Create: `src/landrag/api/app.py`
- Create: `src/landrag/api/dependencies.py`
- Create: `src/landrag/api/routes/__init__.py`
- Create: `src/landrag/api/routes/health.py`
- Create: `src/landrag/api/routes/search.py`
- Create: `tests/api/__init__.py`
- Create: `tests/api/test_health.py`
- Create: `tests/api/test_search.py`

**Step 1: Write test for health endpoint**

`tests/api/__init__.py` — empty

`tests/api/test_health.py`:
```python
from fastapi.testclient import TestClient

from landrag.api.app import create_app


def test_health_endpoint():
    app = create_app()
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/api/test_health.py -v`
Expected: FAIL

**Step 3: Implement FastAPI app and health route**

`src/landrag/api/__init__.py` — empty
`src/landrag/api/routes/__init__.py` — empty

`src/landrag/api/routes/health.py`:
```python
from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health():
    return {"status": "ok"}
```

`src/landrag/api/app.py`:
```python
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from landrag.api.routes.health import router as health_router


def create_app() -> FastAPI:
    app = FastAPI(title="landRAG", version="0.1.0")

    app.include_router(health_router)

    return app
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/api/test_health.py -v`
Expected: 1 PASS

**Step 5: Write test for search endpoint**

`tests/api/test_search.py`:
```python
from unittest.mock import patch, MagicMock, AsyncMock

from fastapi.testclient import TestClient

from landrag.api.app import create_app


@patch("landrag.api.routes.search.execute_search")
def test_search_endpoint_returns_results(mock_search):
    mock_search.return_value = {
        "results": [
            {
                "chunk_id": "abc-123",
                "content": "Noise condition text",
                "score": 0.92,
                "highlight": "**Noise** condition text",
                "document_title": "Decision Letter",
                "document_type": "decision_letter",
                "project_name": "Test Wind Farm",
                "project_reference": "EN010099",
                "project_type": "onshore_wind",
                "topic": "noise",
                "source_url": "https://example.com/doc.pdf",
                "page_start": 12,
                "page_end": 13,
            }
        ],
        "total_estimate": 1,
    }

    app = create_app()
    client = TestClient(app)
    response = client.post("/v1/search", json={"query": "noise conditions on wind farms"})
    assert response.status_code == 200
    data = response.json()
    assert len(data["results"]) == 1
    assert data["results"][0]["chunk_id"] == "abc-123"


def test_search_endpoint_validates_empty_query():
    app = create_app()
    client = TestClient(app)
    response = client.post("/v1/search", json={"query": ""})
    assert response.status_code == 422


def test_search_endpoint_validates_limit():
    app = create_app()
    client = TestClient(app)
    response = client.post("/v1/search", json={"query": "test", "limit": 100})
    assert response.status_code == 422
```

**Step 6: Run tests to verify they fail**

Run: `pytest tests/api/test_search.py -v`
Expected: FAIL (search route not registered)

**Step 7: Implement search route**

`src/landrag/api/dependencies.py`:
```python
from functools import lru_cache

from landrag.core.config import Settings, get_settings


@lru_cache
def get_cached_settings() -> Settings:
    return get_settings()
```

`src/landrag/api/routes/search.py`:
```python
from fastapi import APIRouter

from landrag.models.schemas import SearchRequest, SearchResponse

router = APIRouter(prefix="/v1")


def execute_search(request: SearchRequest) -> dict:
    """Execute the full search pipeline. Wired up to real retrieval in integration."""
    from landrag.ingestion.embedder import embed_query
    from landrag.core.pinecone import get_pinecone_index, build_metadata_filter
    from landrag.search.retrieval import bm25_rescore, combine_scores
    from landrag.search.reranker import rerank

    # 1. Embed query
    query_embedding = embed_query(request.query)

    # 2. Pinecone search
    index = get_pinecone_index()
    pinecone_filter = build_metadata_filter(request.filters)
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
    bm25_scores = bm25_rescore(texts, request.query)

    # 5. Combine scores
    combined = combine_scores(dense_scores, bm25_scores)

    # 6. Rerank top candidates
    reranked = rerank(request.query, texts, top_n=request.limit)

    # 7. Build response using reranked order
    results = []
    for r in reranked:
        idx = r["index"]
        match = pinecone_results.matches[idx]
        meta = match.metadata
        results.append({
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
        })

    return {"results": results, "total_estimate": len(results)}


@router.post("/search")
async def search(request: SearchRequest) -> dict:
    return execute_search(request)
```

Update `src/landrag/api/app.py` to include search router:

```python
from fastapi import FastAPI

from landrag.api.routes.health import router as health_router
from landrag.api.routes.search import router as search_router


def create_app() -> FastAPI:
    app = FastAPI(title="landRAG", version="0.1.0")

    app.include_router(health_router)
    app.include_router(search_router)

    return app
```

**Step 8: Run tests to verify they pass**

Run: `pytest tests/api/test_search.py -v`
Expected: 3 PASS

**Step 9: Commit**

```bash
git add -A
git commit -m "feat: add FastAPI app with health and search endpoints"
```

---

### Task 12: Jinja2 MVP UI

**Files:**
- Create: `src/landrag/templates/base.html`
- Create: `src/landrag/templates/search.html`
- Create: `src/landrag/templates/results.html`
- Create: `src/landrag/templates/document.html`
- Create: `src/landrag/api/routes/ui.py`
- Create: `tests/api/test_ui.py`

**Step 1: Write test for UI routes**

`tests/api/test_ui.py`:
```python
from unittest.mock import patch

from fastapi.testclient import TestClient

from landrag.api.app import create_app


def test_home_page_renders():
    app = create_app()
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert "landRAG" in response.text
    assert "<form" in response.text


@patch("landrag.api.routes.ui.execute_search")
def test_search_page_renders_results(mock_search):
    mock_search.return_value = {
        "results": [
            {
                "chunk_id": "abc",
                "content": "Sample noise text",
                "score": 0.9,
                "highlight": "Sample noise text",
                "document_title": "Decision Letter",
                "document_type": "decision_letter",
                "project_name": "Wind Farm X",
                "project_reference": "EN010099",
                "project_type": "onshore_wind",
                "topic": "noise",
                "source_url": "https://example.com/doc.pdf",
                "page_start": 1,
                "page_end": 2,
            }
        ],
        "total_estimate": 1,
    }
    app = create_app()
    client = TestClient(app)
    response = client.get("/search?query=noise+conditions")
    assert response.status_code == 200
    assert "Wind Farm X" in response.text
    assert "noise" in response.text
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/api/test_ui.py -v`
Expected: FAIL

**Step 3: Create base template**

`src/landrag/templates/base.html`:
```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}landRAG{% endblock %}</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@picocss/pico@2/css/pico.min.css">
    <style>
        .result-card { margin-bottom: 1rem; padding: 1rem; border: 1px solid var(--pico-muted-border-color); border-radius: var(--pico-border-radius); }
        .result-card h4 { margin-bottom: 0.25rem; }
        .badge { display: inline-block; padding: 0.15rem 0.5rem; border-radius: 0.25rem; font-size: 0.8rem; background: var(--pico-primary-background); color: var(--pico-primary-inverse); }
        .meta { font-size: 0.85rem; color: var(--pico-muted-color); }
        .score { font-weight: bold; }
        .filter-panel { margin-bottom: 1rem; }
    </style>
</head>
<body>
    <main class="container">
        <nav>
            <ul><li><strong><a href="/">landRAG</a></strong></li></ul>
        </nav>
        {% block content %}{% endblock %}
    </main>
</body>
</html>
```

**Step 4: Create search (home) template**

`src/landrag/templates/search.html`:
```html
{% extends "base.html" %}
{% block title %}landRAG - Search{% endblock %}
{% block content %}
<h1>landRAG</h1>
<p>Search UK planning decisions, EIAs, and inspector reports.</p>

<form action="/search" method="get">
    <fieldset role="group">
        <input type="search" name="query" placeholder="e.g. noise conditions on onshore wind farms" value="{{ query or '' }}" required>
        <button type="submit">Search</button>
    </fieldset>

    <details class="filter-panel">
        <summary>Filters</summary>
        <div class="grid">
            <label>
                Project Type
                <select name="project_type">
                    <option value="">All</option>
                    <option value="onshore_wind">Onshore Wind</option>
                    <option value="offshore_wind">Offshore Wind</option>
                    <option value="solar">Solar</option>
                    <option value="battery_storage">Battery Storage</option>
                    <option value="gas_peaker">Gas Peaker</option>
                    <option value="transmission">Transmission</option>
                    <option value="hydrogen">Hydrogen</option>
                    <option value="ccus">CCUS</option>
                </select>
            </label>
            <label>
                Topic
                <select name="topic">
                    <option value="">All</option>
                    <option value="noise">Noise</option>
                    <option value="ecology">Ecology</option>
                    <option value="landscape">Landscape</option>
                    <option value="traffic">Traffic</option>
                    <option value="flood_risk">Flood Risk</option>
                    <option value="cultural_heritage">Cultural Heritage</option>
                    <option value="air_quality">Air Quality</option>
                    <option value="socioeconomic">Socioeconomic</option>
                    <option value="cumulative_impact">Cumulative Impact</option>
                </select>
            </label>
            <label>
                Decision
                <select name="decision">
                    <option value="">All</option>
                    <option value="granted">Granted</option>
                    <option value="refused">Refused</option>
                </select>
            </label>
        </div>
    </details>
</form>
{% endblock %}
```

**Step 5: Create results template**

`src/landrag/templates/results.html`:
```html
{% extends "base.html" %}
{% block title %}Results - landRAG{% endblock %}
{% block content %}
<form action="/search" method="get">
    <fieldset role="group">
        <input type="search" name="query" value="{{ query }}" required>
        <button type="submit">Search</button>
    </fieldset>
</form>

<p class="meta">{{ total_estimate }} result{{ 's' if total_estimate != 1 else '' }} for "{{ query }}"</p>

{% for result in results %}
<article class="result-card">
    <h4>{{ result.document_title }}</h4>
    <p class="meta">
        <strong>{{ result.project_name }}</strong> ({{ result.project_reference }})
        {% if result.topic %}<span class="badge">{{ result.topic }}</span>{% endif %}
        <span class="score">{{ "%.2f"|format(result.score) }}</span>
    </p>
    <p>{{ result.highlight }}</p>
    <p class="meta">
        {% if result.page_start %}Pages {{ result.page_start }}–{{ result.page_end }} | {% endif %}
        <a href="{{ result.source_url }}" target="_blank" rel="noopener">View source</a>
    </p>
</article>
{% else %}
<p>No results found. Try a different query or adjust your filters.</p>
{% endfor %}
{% endblock %}
```

**Step 6: Create document view template**

`src/landrag/templates/document.html`:
```html
{% extends "base.html" %}
{% block title %}{{ document.title }} - landRAG{% endblock %}
{% block content %}
<hgroup>
    <h2>{{ document.title }}</h2>
    <p>{{ document.project_name }} ({{ document.project_reference }})</p>
</hgroup>

<table>
    <tr><td>Type</td><td>{{ document.document_type }}</td></tr>
    <tr><td>Source</td><td>{{ document.source_portal }}</td></tr>
    <tr><td>Published</td><td>{{ document.date_published or 'Unknown' }}</td></tr>
    <tr><td>Format</td><td>{{ document.file_format }}</td></tr>
</table>

<p><a href="{{ document.source_url }}" target="_blank" rel="noopener">View original document</a></p>

{% if chunks %}
<h3>Document Chunks</h3>
{% for chunk in chunks %}
<article class="result-card">
    <p class="meta">
        Chunk {{ chunk.chunk_index + 1 }}
        {% if chunk.topic %}<span class="badge">{{ chunk.topic }}</span>{% endif %}
        {% if chunk.page_start %}| Pages {{ chunk.page_start }}–{{ chunk.page_end }}{% endif %}
    </p>
    <p>{{ chunk.content[:500] }}{% if chunk.content|length > 500 %}...{% endif %}</p>
</article>
{% endfor %}
{% endif %}
{% endblock %}
```

**Step 7: Implement UI routes**

`src/landrag/api/routes/ui.py`:
```python
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from landrag.api.routes.search import execute_search
from landrag.models.schemas import SearchRequest, SearchFilters
from landrag.models.enums import ProjectType, Topic, DecisionOutcome

router = APIRouter()

templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))


@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(request, "search.html", {"query": ""})


@router.get("/search", response_class=HTMLResponse)
async def search_page(
    request: Request,
    query: str = "",
    project_type: str = "",
    topic: str = "",
    decision: str = "",
):
    if not query:
        return templates.TemplateResponse(request, "search.html", {"query": ""})

    filters = SearchFilters()
    if project_type:
        filters.project_type = [ProjectType(project_type)]
    if topic:
        filters.topic = [Topic(topic)]
    if decision:
        filters.decision = [DecisionOutcome(decision)]

    has_filters = project_type or topic or decision
    search_request = SearchRequest(
        query=query,
        filters=filters if has_filters else None,
    )
    data = execute_search(search_request)

    return templates.TemplateResponse(request, "results.html", {
        "query": query,
        "results": data["results"],
        "total_estimate": data["total_estimate"],
    })
```

Update `src/landrag/api/app.py` to include UI router:

```python
from fastapi import FastAPI

from landrag.api.routes.health import router as health_router
from landrag.api.routes.search import router as search_router
from landrag.api.routes.ui import router as ui_router


def create_app() -> FastAPI:
    app = FastAPI(title="landRAG", version="0.1.0")

    app.include_router(health_router)
    app.include_router(search_router)
    app.include_router(ui_router)

    return app
```

**Step 8: Run tests to verify they pass**

Run: `pytest tests/api/test_ui.py -v`
Expected: 2 PASS

**Step 9: Commit**

```bash
git add -A
git commit -m "feat: add Jinja2 server-rendered MVP UI with search and results pages"
```

---

### Task 13: PINS Scraper (Skeleton)

**Files:**
- Create: `src/landrag/ingestion/scrapers/__init__.py`
- Create: `src/landrag/ingestion/scrapers/pins.py`
- Create: `tests/ingestion/scrapers/__init__.py`
- Create: `tests/ingestion/scrapers/test_pins.py`

**Step 1: Write tests for PINS scraper utilities**

`tests/ingestion/scrapers/__init__.py` — empty

`tests/ingestion/scrapers/test_pins.py`:
```python
from landrag.ingestion.scrapers.pins import (
    parse_nsip_project_list_page,
    parse_document_library_page,
    NsipProject,
    DocumentLink,
)


SAMPLE_PROJECT_HTML = """
<tr>
    <td><a href="/projects/EN010012">Hornsea Project One</a></td>
    <td>Offshore Wind</td>
    <td>East Riding of Yorkshire</td>
    <td>Granted</td>
</tr>
<tr>
    <td><a href="/projects/EN010077">Gate Burton Energy Park</a></td>
    <td>Solar</td>
    <td>West Lindsey</td>
    <td>Pending</td>
</tr>
"""


def test_parse_nsip_project_list():
    projects = parse_nsip_project_list_page(SAMPLE_PROJECT_HTML)
    assert len(projects) == 2
    assert projects[0].reference == "EN010012"
    assert projects[0].name == "Hornsea Project One"
    assert projects[1].reference == "EN010077"


SAMPLE_DOC_LIBRARY_HTML = """
<tr>
    <td><a href="/docs/EN010012-001234.pdf">Environmental Statement Chapter 7 - Noise</a></td>
    <td>Environmental Statement</td>
    <td>15/03/2019</td>
</tr>
<tr>
    <td><a href="/docs/EN010012-005678.pdf">Decision Letter</a></td>
    <td>Decision</td>
    <td>01/09/2020</td>
</tr>
"""


def test_parse_document_library_page():
    docs = parse_document_library_page(SAMPLE_DOC_LIBRARY_HTML, "EN010012")
    assert len(docs) == 2
    assert "Noise" in docs[0].title
    assert docs[1].title == "Decision Letter"
    assert docs[0].project_reference == "EN010012"
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/ingestion/scrapers/test_pins.py -v`
Expected: FAIL

**Step 3: Implement PINS scraper parsing utilities**

`src/landrag/ingestion/scrapers/__init__.py` — empty

`src/landrag/ingestion/scrapers/pins.py`:
```python
from dataclasses import dataclass

from bs4 import BeautifulSoup

from landrag.ingestion.classifier import extract_pins_reference


@dataclass
class NsipProject:
    reference: str
    name: str
    project_type: str
    local_authority: str
    decision: str
    url_path: str


@dataclass
class DocumentLink:
    title: str
    url_path: str
    category: str
    date_str: str
    project_reference: str


def parse_nsip_project_list_page(html: str) -> list[NsipProject]:
    soup = BeautifulSoup(html, "html.parser")
    projects: list[NsipProject] = []

    for row in soup.find_all("tr"):
        cells = row.find_all("td")
        if len(cells) < 4:
            continue

        link = cells[0].find("a")
        if not link:
            continue

        url_path = link.get("href", "")
        name = link.get_text(strip=True)
        reference = extract_pins_reference(url_path) or extract_pins_reference(name) or ""

        projects.append(NsipProject(
            reference=reference,
            name=name,
            project_type=cells[1].get_text(strip=True),
            local_authority=cells[2].get_text(strip=True),
            decision=cells[3].get_text(strip=True),
            url_path=url_path,
        ))

    return projects


def parse_document_library_page(html: str, project_reference: str) -> list[DocumentLink]:
    soup = BeautifulSoup(html, "html.parser")
    docs: list[DocumentLink] = []

    for row in soup.find_all("tr"):
        cells = row.find_all("td")
        if len(cells) < 3:
            continue

        link = cells[0].find("a")
        if not link:
            continue

        docs.append(DocumentLink(
            title=link.get_text(strip=True),
            url_path=link.get("href", ""),
            category=cells[1].get_text(strip=True),
            date_str=cells[2].get_text(strip=True),
            project_reference=project_reference,
        ))

    return docs
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/ingestion/scrapers/test_pins.py -v`
Expected: 2 PASS

**Step 5: Commit**

```bash
git add -A
git commit -m "feat: add PINS scraper HTML parsing utilities"
```

---

### Task 14: Run Full Test Suite and Lint

**Step 1: Run all tests**

```bash
pytest tests/ -v --tb=short
```
Expected: All tests pass (20+ tests)

**Step 2: Run ruff**

```bash
ruff check src/ tests/
```
Expected: No errors (or fix any that appear)

**Step 3: Run ruff format**

```bash
ruff format src/ tests/
```

**Step 4: Fix any issues and commit**

```bash
git add -A
git commit -m "chore: fix lint issues and verify full test suite passes"
```

---

### Summary

| Task | Component | Tests |
|------|-----------|-------|
| 1 | Project scaffolding, config, docker-compose | 2 |
| 2 | Enums, Pydantic schemas | 12 |
| 3 | SQLAlchemy models, Alembic | 4 |
| 4 | Pinecone client, filter builder | 6 |
| 5 | Text parsers (PDF, HTML, DOCX) | 8 |
| 6 | Document chunker | 5 |
| 7 | Embedding module | 3 |
| 8 | Metadata classifier | 2 |
| 9 | Celery worker and tasks | 2 |
| 10 | Search retrieval + reranker | 3 |
| 11 | FastAPI app + search endpoint | 4 |
| 12 | Jinja2 MVP UI | 2 |
| 13 | PINS scraper parsing | 2 |
| 14 | Full test suite + lint | — |
