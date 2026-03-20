from typing import Literal

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


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    history: list[ChatMessage] = Field(default_factory=list)
    filters: dict | None = None


class SourceResult(BaseModel):
    ref: int
    chunk_id: str
    content: str
    score: float
    document_title: str
    document_type: str
    project_name: str
    project_reference: str
    project_type: str
    topic: str | None = None
    source_url: str
    page_start: int | None = None
    page_end: int | None = None


class CorpusSourceStatus(BaseModel):
    portal: str
    document_count: int
    last_updated: str


class CorpusStatusResponse(BaseModel):
    sources: list[CorpusSourceStatus]
    total_documents: int
