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
