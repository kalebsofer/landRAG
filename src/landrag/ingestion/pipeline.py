"""End-to-end ingestion pipeline: scrape → download → parse → chunk → embed → store."""

import logging
import tempfile
import uuid
from datetime import UTC, datetime
from pathlib import Path

import httpx
from pinecone import Pinecone
from sqlalchemy import select
from sqlalchemy.orm import Session

from landrag.core.config import get_settings
from landrag.core.db import get_sync_engine
from landrag.ingestion.chunker import chunk_document
from landrag.ingestion.embedder import embed_texts
from landrag.ingestion.parsers.pdf import extract_pdf
from landrag.ingestion.scrapers.pins import (
    NsipProject,
    fetch_all_documents,
    fetch_project_list,
)
from landrag.models.database import Chunk, Document, IngestionJob, Project
from landrag.models.enums import SourcePortal

logger = logging.getLogger(__name__)

# Energy-related application type prefixes
ENERGY_TYPE_PREFIXES = ["EN01", "EN02", "EN03", "EN04", "EN05"]


def _is_energy_project(project: NsipProject) -> bool:
    return any(project.project_type.startswith(prefix) for prefix in ENERGY_TYPE_PREFIXES)


def _map_decision(stage: str) -> str | None:
    stage_lower = stage.lower()
    if "post-decision" in stage_lower or "decided" in stage_lower:
        return "granted"
    if "withdrawn" in stage_lower:
        return "withdrawn"
    if "refused" in stage_lower:
        return "refused"
    return "pending"


def _map_project_type(application_type: str) -> str:
    type_lower = application_type.lower()
    if "wind" in type_lower and "offshore" in type_lower:
        return "offshore_wind"
    if "wind" in type_lower:
        return "onshore_wind"
    if "solar" in type_lower:
        return "solar"
    if "battery" in type_lower or "storage" in type_lower:
        return "battery_storage"
    if "gas" in type_lower:
        return "gas_peaker"
    if "transmission" in type_lower or "electric" in type_lower:
        return "transmission"
    if "hydrogen" in type_lower:
        return "hydrogen"
    if "carbon" in type_lower or "ccus" in type_lower:
        return "ccus"
    return "other"


def ingest_projects(session: Session) -> list[Project]:
    """Fetch PINS project list and store energy projects in the database."""
    nsip_projects = fetch_project_list()
    energy_projects = [p for p in nsip_projects if _is_energy_project(p)]
    logger.info(
        "Found %d energy projects out of %d total",
        len(energy_projects),
        len(nsip_projects),
    )

    db_projects: list[Project] = []
    for p in energy_projects:
        existing = session.execute(
            select(Project).where(Project.reference == p.reference)
        ).scalar_one_or_none()

        if existing:
            db_projects.append(existing)
            continue

        project = Project(
            name=p.name,
            reference=p.reference,
            type=_map_project_type(p.project_type),
            local_authority=p.local_authority,
            region=p.region,
            decision=_map_decision(p.decision),
        )
        session.add(project)
        db_projects.append(project)

    session.commit()
    logger.info("Stored %d energy projects in database", len(db_projects))
    return db_projects


def _download_to_tempfile(url: str) -> Path | None:
    """Download a PDF to a temp file. Returns path or None on failure."""
    try:
        with httpx.stream("GET", url, timeout=120, follow_redirects=True) as response:
            response.raise_for_status()
            tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
            for chunk in response.iter_bytes(chunk_size=8192):
                tmp.write(chunk)
            tmp.close()
            return Path(tmp.name)
    except httpx.HTTPError as e:
        logger.error("Failed to download %s: %s", url, e)
        return None


def process_and_ingest_document(
    session: Session,
    project: Project,
    doc_url: str,
    doc_title: str,
    pinecone_index,
) -> int:
    """Download, parse, chunk, embed, and store a single document. Cleans up temp file after.

    Returns chunk count.
    """
    # Check if already ingested
    existing = session.execute(
        select(Document).where(Document.source_url == doc_url)
    ).scalar_one_or_none()
    if existing:
        existing_chunks = (
            session.execute(select(Chunk).where(Chunk.document_id == existing.id)).scalars().all()
        )
        if existing_chunks:
            logger.debug("Already processed: %s (%d chunks)", doc_title, len(existing_chunks))
            return len(existing_chunks)

    # Download to temp file
    tmp_path = _download_to_tempfile(doc_url)
    if not tmp_path:
        return 0

    try:
        # Parse
        parsed = extract_pdf(str(tmp_path))
        if not parsed.text.strip():
            logger.warning("Empty text extracted from %s (likely scanned PDF)", doc_title)
            return 0

        # Chunk
        chunks = chunk_document(parsed)
        if not chunks:
            return 0

        # Embed
        texts = [c.text for c in chunks]
        embeddings = embed_texts(texts)

        # Create Document record (no local storage_path — source_url is the reference)
        doc = Document(
            project_id=project.id,
            title=doc_title,
            type="decision_letter" if "decision" in doc_title.lower() else "eia_chapter",
            file_format="pdf",
            source_url=doc_url,
            source_portal=SourcePortal.PINS.value,
            retrieved_at=datetime.now(UTC),
            storage_path="",  # no local storage
        )
        session.add(doc)
        session.flush()  # get doc.id

        # Store chunks in Postgres + Pinecone
        pinecone_vectors = []
        for chunk, embedding in zip(chunks, embeddings):
            pinecone_id = str(uuid.uuid4())

            db_chunk = Chunk(
                document_id=doc.id,
                content=chunk.text,
                chunk_index=chunk.chunk_index,
                pinecone_id=pinecone_id,
            )
            session.add(db_chunk)

            pinecone_vectors.append(
                {
                    "id": pinecone_id,
                    "values": embedding,
                    "metadata": {
                        "text": chunk.text[:1000],
                        "project_type": project.type,
                        "document_type": doc.type,
                        "topic": chunk.section_heading or "",
                        "decision": project.decision or "",
                        "date_published": str(doc.date_published) if doc.date_published else "",
                        "region": project.region,
                        "capacity_mw": project.capacity_mw or 0,
                        "project_reference": project.reference,
                        "document_title": doc.title,
                        "project_name": project.name,
                        "source_url": doc.source_url,
                        "page_start": chunk.chunk_index,
                        "page_end": chunk.chunk_index,
                    },
                }
            )

        # Upsert to Pinecone in batches of 100
        for i in range(0, len(pinecone_vectors), 100):
            batch = pinecone_vectors[i : i + 100]
            pinecone_index.upsert(vectors=batch)

        session.commit()
        logger.info("Processed %s: %d chunks", doc_title, len(chunks))
        return len(chunks)

    except Exception as e:
        session.rollback()
        logger.error("Failed to process %s: %s", doc_title, e)
        return 0
    finally:
        # Always clean up temp file
        tmp_path.unlink(missing_ok=True)


def run_pipeline(
    project_references: list[str] | None = None,
    max_documents_per_project: int | None = None,
):
    """Run the full ingestion pipeline.

    Args:
        project_references: Specific project references to ingest.
            If None, ingest all energy projects.
        max_documents_per_project: Limit documents per project (useful for testing).
    """
    settings = get_settings()
    engine = get_sync_engine()

    # Set up Pinecone
    pc = Pinecone(api_key=settings.pinecone_api_key)
    pinecone_index = pc.Index(settings.pinecone_index_name)

    with Session(engine) as session:
        # Create ingestion job
        job = IngestionJob(
            source_portal=SourcePortal.PINS.value,
            status="running",
            started_at=datetime.now(UTC),
        )
        session.add(job)
        session.commit()

        try:
            # Step 1: Fetch and store projects
            projects = ingest_projects(session)

            if project_references:
                projects = [p for p in projects if p.reference in project_references]

            logger.info("Processing %d projects", len(projects))
            job.documents_found = 0
            job.documents_processed = 0

            total_chunks = 0
            for project in projects:
                # Step 2: Fetch document links
                doc_links = fetch_all_documents(project.reference)
                if max_documents_per_project:
                    doc_links = doc_links[:max_documents_per_project]

                job.documents_found = (job.documents_found or 0) + len(doc_links)
                session.commit()

                # Step 3: Process each document (download → parse → chunk → embed → store → cleanup)
                for link in doc_links:
                    chunk_count = process_and_ingest_document(
                        session, project, link.url, link.title, pinecone_index
                    )
                    total_chunks += chunk_count
                    job.documents_processed = (job.documents_processed or 0) + 1
                    session.commit()

            job.status = "completed"
            job.completed_at = datetime.now(UTC)
            session.commit()

            logger.info(
                "Pipeline complete: %d projects, %d documents, %d chunks",
                len(projects),
                job.documents_found,
                total_chunks,
            )

        except Exception as e:
            job.status = "failed"
            job.error_message = str(e)
            job.completed_at = datetime.now(UTC)
            session.commit()
            logger.error("Pipeline failed: %s", e)
            raise
