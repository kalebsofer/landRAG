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
