from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "autodocs",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.workers.tasks"],
)

celery_app.conf.update(task_track_started=True, task_serializer="json", result_serializer="json")
