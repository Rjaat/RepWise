import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, TypedDict

from celery import Celery

from repwise_api.media import normalize_media
from repwise_api.pose import ModelIdentity, build_pose_artifact_file
from repwise_api.settings import get_settings
from repwise_api.squat import extract_knee_angle_samples, segment_squats
from repwise_api.storage import MinioObjectStorage


class SmokeResult(TypedDict):
    status: str
    worker: str


class MediaTaskResult(TypedDict):
    normalized_object_key: str
    manifest_object_key: str
    preflight: dict[str, Any]


class PoseTaskResult(TypedDict):
    artifact_object_key: str
    artifact_sha256: str
    frame_count: int


class SegmentationTaskResult(TypedDict):
    segmentation_object_key: str
    outcome: str
    complete_rep_count: int
    partial_rep_count: int


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


@celery_app.task(name="repwise.pose.persist")  # type: ignore[misc]
def pose_artifact_task(
    inference_object_key: str,
    inference_sha256: str,
    normalized_media_sha256: str,
    model_name: str,
    model_version: str,
    model_sha256: str,
) -> PoseTaskResult:
    """Validate pinned inference output and publish a versioned private artifact."""
    storage = MinioObjectStorage(settings)
    artifact_key = f"{inference_object_key}.pose.v1.json"
    with TemporaryDirectory(prefix="repwise-pose-") as directory:
        inference = Path(directory) / "inference.json"
        artifact_path = Path(directory) / "pose.v1.json"
        storage.download(inference_object_key, str(inference))
        artifact = build_pose_artifact_file(
            inference,
            artifact_path,
            source_sha256=normalized_media_sha256,
            model=ModelIdentity(model_name, model_version, model_sha256),
            expected_input_sha256=inference_sha256,
        )
        storage.upload(artifact_key, str(artifact_path), "application/json")
    return {
        "artifact_object_key": artifact_key,
        "artifact_sha256": str(artifact["artifact_sha256"]),
        "frame_count": int(artifact["summary"]["frame_count"]),
    }


@celery_app.task(name="repwise.squat.segment")  # type: ignore[misc]
def squat_segmentation_task(
    pose_artifact_key: str,
    pose_artifact_sha256: str,
    frame_width: int,
    frame_height: int,
) -> SegmentationTaskResult:
    storage = MinioObjectStorage(settings)
    segmentation_key = f"{pose_artifact_key}.squat-segmentation.v1.json"
    with TemporaryDirectory(prefix="repwise-squat-") as directory:
        pose_path = Path(directory) / "pose.json"
        segmentation_path = Path(directory) / "segmentation.json"
        storage.download(pose_artifact_key, str(pose_path))
        if hashlib.sha256(pose_path.read_bytes()).hexdigest() != pose_artifact_sha256:
            raise ValueError("Pose artifact checksum mismatch")
        pose_artifact = json.loads(pose_path.read_text(encoding="utf-8"))
        if not isinstance(pose_artifact, dict):
            raise ValueError("Pose artifact must be an object")
        samples = extract_knee_angle_samples(pose_artifact, frame_width, frame_height)
        result = segment_squats(samples)
        segmentation_path.write_text(
            f"{json.dumps(result.to_dict(), sort_keys=True)}\n", encoding="utf-8"
        )
        storage.upload(segmentation_key, str(segmentation_path), "application/json")
    return {
        "segmentation_object_key": segmentation_key,
        "outcome": result.outcome,
        "complete_rep_count": len(result.complete_reps),
        "partial_rep_count": len(result.partial_reps),
    }
