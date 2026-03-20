from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from landrag.chat.pipeline import chat_stream
from landrag.models.schemas import ChatRequest

router = APIRouter(prefix="/v1")


@router.post("/chat")
async def chat(request: ChatRequest) -> StreamingResponse:
    """Stream a RAG chat response as Server-Sent Events."""
    return StreamingResponse(
        chat_stream(
            message=request.message,
            history=request.history,
            explicit_filters=request.filters,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
