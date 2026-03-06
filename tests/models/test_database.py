from datetime import UTC, datetime
from uuid import uuid4

from landrag.models.database import Chunk, Document, IngestionJob, Project
from landrag.models.enums import (
    DocumentType,
    JobStatus,
    ProjectType,
    SourcePortal,
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
