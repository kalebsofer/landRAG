import pytest
from pydantic import ValidationError

from landrag.models.enums import DecisionOutcome, DocumentType, ProjectType, Topic
from landrag.models.schemas import ChunkResult, SearchFilters, SearchRequest, SearchResponse


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
