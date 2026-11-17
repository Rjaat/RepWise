import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, TypedDict

from celery import Celery

from repwise_api.media import normalize_media
from repwise_api.pose import ModelIdentity, build_pose_artifact_file
from repwise_api.practice import PracticeSample, evaluate_practice_rep
from repwise_api.readiness import ReadinessObservation, evaluate_readiness
from repwise_api.reports import build_squat_report
from repwise_api.retention import reject_tombstoned_analysis
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


class ReportTaskResult(TypedDict):
    report_object_key: str
    report_sha256: str
    rep_count: int


class ReadinessTaskResult(TypedDict):
    readiness_object_key: str
    ready: bool
    code: str


class PracticeTaskResult(TypedDict):
    practice_object_key: str
    suitable: bool
    code: str


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


@celery_app.task(name="repwise.smoke")  # type: ignore[untyped-decorator]
def smoke_task() -> SmokeResult:
    return {"status": "ok", "worker": "media"}


@celery_app.task(name="repwise.media.preflight")  # type: ignore[untyped-decorator]
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


@celery_app.task(name="repwise.pose.persist")  # type: ignore[untyped-decorator]
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


@celery_app.task(name="repwise.squat.segment")  # type: ignore[untyped-decorator]
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


@celery_app.task(name="repwise.report.publish")  # type: ignore[untyped-decorator]
def publish_report_task(
    segmentation_object_key: str,
    segmentation_file_sha256: str,
    analysis_id: str,
    source_sha256: str,
    pose_artifact_sha256: str,
) -> ReportTaskResult:
    reject_tombstoned_analysis(analysis_id, settings.database_url)
    storage = MinioObjectStorage(settings)
    report_key = f"analyses/{analysis_id}/report.v1.json"
    with TemporaryDirectory(prefix="repwise-report-") as directory:
        segmentation_path = Path(directory) / "segmentation.json"
        report_path = Path(directory) / "report.json"
        storage.download(segmentation_object_key, str(segmentation_path))
        segmentation_bytes = segmentation_path.read_bytes()
        if hashlib.sha256(segmentation_bytes).hexdigest() != segmentation_file_sha256:
            raise ValueError("Segmentation artifact checksum mismatch")
        segmentation = json.loads(segmentation_bytes)
        if not isinstance(segmentation, dict):
            raise ValueError("Segmentation artifact must be an object")
        report = build_squat_report(
            segmentation,
            analysis_id=analysis_id,
            source_sha256=source_sha256,
            pose_artifact_sha256=pose_artifact_sha256,
            segmentation_artifact_sha256=segmentation_file_sha256,
        )
        report_path.write_bytes(report.canonical_payload() + b"\n")
        reject_tombstoned_analysis(analysis_id, settings.database_url)
        storage.upload(report_key, str(report_path), "application/json")
    return {
        "report_object_key": report_key,
        "report_sha256": report.checksum(),
        "rep_count": len(report.reps),
    }


@celery_app.task(name="repwise.capture.readiness")  # type: ignore[untyped-decorator]
def capture_readiness_task(observations_object_key: str) -> ReadinessTaskResult:
    storage = MinioObjectStorage(settings)
    result_key = f"{observations_object_key}.readiness.v1.json"
    with TemporaryDirectory(prefix="repwise-readiness-") as directory:
        source_path = Path(directory) / "observations.json"
        result_path = Path(directory) / "readiness.json"
        storage.download(observations_object_key, str(source_path))
        decoded = json.loads(source_path.read_text(encoding="utf-8"))
        if not isinstance(decoded, list):
            raise ValueError("Readiness observations must be an array")
        observations = tuple(
            ReadinessObservation(
                timestamp_seconds=float(item["timestamp_seconds"]),
                required_landmark_coverage=float(item["required_landmark_coverage"]),
                full_body_visible=bool(item["full_body_visible"]),
                side_view_score=float(item["side_view_score"]),
                motion_px=float(item["motion_px"]),
            )
            for item in decoded
        )
        result = evaluate_readiness(observations)
        result_path.write_text(
            f"{json.dumps(result.to_dict(), sort_keys=True)}\n", encoding="utf-8"
        )
        storage.upload(result_key, str(result_path), "application/json")
    return {
        "readiness_object_key": result_key,
        "ready": result.ready,
        "code": result.code,
    }


@celery_app.task(name="repwise.capture.practice")  # type: ignore[untyped-decorator]
def practice_rep_task(samples_object_key: str) -> PracticeTaskResult:
    storage = MinioObjectStorage(settings)
    result_key = f"{samples_object_key}.practice.v1.json"
    with TemporaryDirectory(prefix="repwise-practice-") as directory:
        source_path = Path(directory) / "samples.json"
        result_path = Path(directory) / "practice.json"
        storage.download(samples_object_key, str(source_path))
        decoded = json.loads(source_path.read_text(encoding="utf-8"))
        if not isinstance(decoded, list):
            raise ValueError("Practice samples must be an array")
        samples = tuple(
            PracticeSample(
                timestamp_seconds=float(item["timestamp_seconds"]),
                knee_angle_degrees=(
                    None
                    if item["knee_angle_degrees"] is None
                    else float(item["knee_angle_degrees"])
                ),
                required_landmark_coverage=float(item["required_landmark_coverage"]),
            )
            for item in decoded
        )
        result = evaluate_practice_rep(samples)
        result_path.write_text(
            f"{json.dumps(result.to_dict(), sort_keys=True)}\n", encoding="utf-8"
        )
        storage.upload(result_key, str(result_path), "application/json")
    return {
        "practice_object_key": result_key,
        "suitable": result.suitable,
        "code": result.code,
    }
