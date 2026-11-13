from typing import TypedDict

from celery import Celery

from repwise_api.settings import get_settings


class SmokeResult(TypedDict):
    status: str
    worker: str


settings = get_settings()
celery_app = Celery(
    "repwise",
    broker=settings.redis_url,
    backend=settings.redis_url,
)
celery_app.conf.update(
    accept_content=["json"],
    task_serializer="json",
    result_serializer="json",
    result_expires=60,
    task_track_started=True,
    worker_hijack_root_logger=False,
)


@celery_app.task(name="repwise.smoke")  # type: ignore[misc]
def smoke_task() -> SmokeResult:
    return {"status": "ok", "worker": "media"}
