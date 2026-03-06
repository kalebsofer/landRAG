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
