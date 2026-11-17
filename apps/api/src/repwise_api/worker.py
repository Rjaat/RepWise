import json
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, TypedDict

from celery import Celery

from repwise_api.media import normalize_media
from repwise_api.settings import get_settings
from repwise_api.storage import MinioObjectStorage


class SmokeResult(TypedDict):
    status: str
    worker: str


class MediaTaskResult(TypedDict):
    normalized_object_key: str
    manifest_object_key: str
    preflight: dict[str, Any]


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


@celery_app.task(name="repwise.media.preflight")  # type: ignore[misc]
def media_preflight_task(object_key: str, expected_sha256: str) -> MediaTaskResult:
    storage = MinioObjectStorage(settings)
    normalized_key = f"{object_key}.normalized.mp4"
    manifest_key = f"{object_key}.preflight.json"
    with TemporaryDirectory(prefix="repwise-media-") as directory:
        source = Path(directory) / "source"
        normalized = Path(directory) / "normalized.mp4"
        manifest = Path(directory) / "preflight.json"
        storage.download(object_key, str(source))
        result = normalize_media(source, normalized, expected_sha256)
        manifest.write_text(
            f"{json.dumps(result.to_dict(), sort_keys=True)}\n", encoding="utf-8"
        )
        storage.upload(normalized_key, str(normalized), "video/mp4")
        storage.upload(manifest_key, str(manifest), "application/json")
    return {
        "normalized_object_key": normalized_key,
        "manifest_object_key": manifest_key,
        "preflight": result.to_dict(),
    }
