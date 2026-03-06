from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from landrag.api.routes.search import execute_search
from landrag.models.enums import DecisionOutcome, ProjectType, Topic
from landrag.models.schemas import SearchFilters, SearchRequest

router = APIRouter()

templates = Jinja2Templates(
    directory=str(Path(__file__).resolve().parent.parent.parent / "templates")
)


@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(request, "search.html", {"query": ""})


@router.get("/search", response_class=HTMLResponse)
async def search_page(
    request: Request,
    query: str = "",
    project_type: str = "",
    topic: str = "",
    decision: str = "",
):
    if not query:
        return templates.TemplateResponse(request, "search.html", {"query": ""})

    filters = SearchFilters()
    if project_type:
        filters.project_type = [ProjectType(project_type)]
    if topic:
        filters.topic = [Topic(topic)]
    if decision:
        filters.decision = [DecisionOutcome(decision)]

    has_filters = project_type or topic or decision
    search_request = SearchRequest(
        query=query,
        filters=filters if has_filters else None,
    )
    data = execute_search(search_request)

    return templates.TemplateResponse(
        request,
        "results.html",
        {
            "query": query,
            "results": data["results"],
            "total_estimate": data["total_estimate"],
        },
    )
