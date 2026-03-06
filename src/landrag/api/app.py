from fastapi import FastAPI

from landrag.api.routes.health import router as health_router
from landrag.api.routes.search import router as search_router
from landrag.api.routes.ui import router as ui_router


def create_app() -> FastAPI:
    app = FastAPI(title="landRAG", version="0.1.0")

    app.include_router(health_router)
    app.include_router(search_router)
    app.include_router(ui_router)

    return app
