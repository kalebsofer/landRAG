import pytest
from pydantic import ValidationError

from landrag.models.enums import DecisionOutcome, DocumentType, ProjectType, Topic
from landrag.models.schemas import (
    ChatMessage,
    ChatRequest,
    ChunkResult,
    CorpusSourceStatus,
    CorpusStatusResponse,
    SearchFilters,
    SearchRequest,
    SearchResponse,
    SourceResult,
)


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


def test_chat_message_schema():
    msg = ChatMessage(role="user", content="Hello")
    assert msg.role == "user"
    assert msg.content == "Hello"


def test_chat_message_rejects_invalid_role():
    with pytest.raises(ValidationError):
        ChatMessage(role="system", content="Hello")


def test_chat_request_minimal():
    req = ChatRequest(message="What noise conditions?")
    assert req.message == "What noise conditions?"
    assert req.history == []
    assert req.filters is None


def test_chat_request_with_history_and_filters():
    req = ChatRequest(
        message="What about solar?",
        history=[
            ChatMessage(role="user", content="Hi"),
            ChatMessage(role="assistant", content="Hello"),
        ],
        filters={"project_type": ["solar"]},
    )
    assert len(req.history) == 2
    assert req.filters == {"project_type": ["solar"]}


def test_chat_request_rejects_empty_message():
    with pytest.raises(ValidationError):
        ChatRequest(message="")


def test_source_result_schema():
    src = SourceResult(
        ref=1,
        chunk_id="abc-123",
        content="Noise text",
        score=0.92,
        document_title="Decision Letter",
        document_type="decision_letter",
        project_name="Test Wind Farm",
        project_reference="EN010099",
        project_type="onshore_wind",
        topic="noise",
        source_url="https://example.com/doc.pdf",
        page_start=12,
        page_end=13,
    )
    assert src.ref == 1
    assert src.chunk_id == "abc-123"


def test_corpus_status_response():
    resp = CorpusStatusResponse(
        sources=[
            CorpusSourceStatus(
                portal="pins", document_count=100, last_updated="2026-03-12T14:30:00Z"
            )
        ],
        total_documents=100,
    )
    assert len(resp.sources) == 1
    assert resp.total_documents == 100
