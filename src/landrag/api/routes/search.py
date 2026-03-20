from fastapi import APIRouter

from landrag.models.schemas import SearchRequest
from landrag.search.retrieval import execute_search_pipeline

router = APIRouter(prefix="/v1")


def execute_search(request: SearchRequest) -> dict:
    """Thin wrapper for backward compatibility."""
    return execute_search_pipeline(request.query, request.filters, request.limit)


@router.post("/search")
async def search(request: SearchRequest) -> dict:
    return execute_search(request)
