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
