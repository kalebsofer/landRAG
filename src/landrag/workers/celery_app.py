from celery import Celery

from landrag.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "landrag",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_routes={
        "landrag.workers.tasks.scrape_*": {"queue": "scraping"},
        "landrag.workers.tasks.parse_*": {"queue": "parsing"},
        "landrag.workers.tasks.chunk_*": {"queue": "processing"},
        "landrag.workers.tasks.embed_*": {"queue": "embedding"},
    },
    task_default_rate_limit="10/m",
)

celery_app.autodiscover_tasks(["landrag.workers"])
