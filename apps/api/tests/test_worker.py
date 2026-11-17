import hashlib
import json
from pathlib import Path
from typing import Any
from unittest.mock import Mock, patch

import pytest

from repwise_api.media import MediaProbe, PreflightResult
from repwise_api.smoke import main
from repwise_api.worker import (
    capture_readiness_task,
    celery_app,
    media_preflight_task,
    pose_artifact_task,
    practice_rep_task,
    publish_report_task,
    smoke_task,
    squat_segmentation_task,
)


def test_smoke_task_has_deterministic_json_result() -> None:
    celery_app.conf.task_always_eager = True
    celery_app.conf.task_store_eager_result = False

    result = smoke_task.delay()

    assert result.get() == {"status": "ok", "worker": "media"}


@pytest.mark.parametrize(
    ("payload", "raises"),
    [
        ({"status": "ok", "worker": "media"}, False),
        ({"status": "unexpected"}, True),
    ],
)
def test_smoke_entrypoint_validates_and_removes_result(
    payload: dict[str, Any], raises: bool, capsys: pytest.CaptureFixture[str]
) -> None:
    result = Mock()
    result.get.return_value = payload

    with patch("repwise_api.smoke.smoke_task.delay", return_value=result):
        if raises:
            with pytest.raises(RuntimeError, match="Unexpected smoke result"):
                main()
            result.forget.assert_not_called()
        else:
            main()
            result.forget.assert_called_once_with()
            assert "completed" in capsys.readouterr().out

    result.get.assert_called_once_with(timeout=20)


def test_media_task_moves_private_artifacts_and_returns_manifest() -> None:
    storage = Mock()
    probe = MediaProbe("h264", 100, 100, 1, 0, False, False, "1", "1")
    preflight = PreflightResult("a" * 64, "b" * 64, probe, probe, ())
    with (
        patch("repwise_api.worker.MinioObjectStorage", return_value=storage),
        patch("repwise_api.worker.normalize_media", return_value=preflight),
    ):
        result = media_preflight_task("users/1/uploads/2/source", "a" * 64)

    assert result["normalized_object_key"].endswith(".normalized.mp4")
    assert result["manifest_object_key"].endswith(".preflight.json")
    assert result["preflight"]["normalized_sha256"] == "b" * 64
    storage.download.assert_called_once()
    assert storage.upload.call_count == 2


def test_pose_task_persists_private_versioned_artifact() -> None:
    storage = Mock()
    artifact = {
        "artifact_sha256": "d" * 64,
        "summary": {"frame_count": 3},
    }
    with (
        patch("repwise_api.worker.MinioObjectStorage", return_value=storage),
        patch(
            "repwise_api.worker.build_pose_artifact_file", return_value=artifact
        ) as build,
    ):
        result = pose_artifact_task(
            "users/1/inference.json",
            "a" * 64,
            "b" * 64,
            "MediaPipe Pose Landmarker Full",
            "1.2.3",
            "c" * 64,
        )

    assert result == {
        "artifact_object_key": "users/1/inference.json.pose.v1.json",
        "artifact_sha256": "d" * 64,
        "frame_count": 3,
    }
    storage.download.assert_called_once()
    storage.upload.assert_called_once()
    assert build.call_args.kwargs["model"].version == "1.2.3"


def test_squat_task_verifies_and_persists_segmentation() -> None:
    storage = Mock()
    pose_bytes = json.dumps({"frames": []}).encode()

    def download(_key: str, destination: str) -> None:
        Path(destination).write_bytes(pose_bytes)

    storage.download.side_effect = download
    with patch("repwise_api.worker.MinioObjectStorage", return_value=storage):
        result = squat_segmentation_task(
            "users/1/pose.json", hashlib.sha256(pose_bytes).hexdigest(), 100, 200
        )

    assert result == {
        "segmentation_object_key": ("users/1/pose.json.squat-segmentation.v1.json"),
        "outcome": "not_assessable",
        "complete_rep_count": 0,
        "partial_rep_count": 0,
    }
    storage.upload.assert_called_once()


def test_squat_task_rejects_checksum_and_non_object_artifact() -> None:
    storage = Mock()

    def download(_key: str, destination: str) -> None:
        Path(destination).write_text("[]", encoding="utf-8")

    storage.download.side_effect = download
    with patch("repwise_api.worker.MinioObjectStorage", return_value=storage):
        with pytest.raises(ValueError, match="checksum mismatch"):
            squat_segmentation_task("pose.json", "a" * 64, 100, 200)
        checksum = hashlib.sha256(b"[]").hexdigest()
        with pytest.raises(ValueError, match="must be an object"):
            squat_segmentation_task("pose.json", checksum, 100, 200)


def test_report_task_verifies_and_publishes_immutable_report() -> None:
    storage = Mock()
    segmentation = json.dumps(
        {"complete_reps": [], "partial_reps": []}, sort_keys=True
    ).encode()

    def download(_key: str, destination: str) -> None:
        Path(destination).write_bytes(segmentation)

    storage.download.side_effect = download
    checksum = hashlib.sha256(segmentation).hexdigest()
    with patch("repwise_api.worker.MinioObjectStorage", return_value=storage):
        result = publish_report_task(
            "segmentation.json", checksum, "analysis-1", "a" * 64, "b" * 64
        )
    assert result["report_object_key"] == "analyses/analysis-1/report.v1.json"
    assert result["rep_count"] == 0
    assert len(result["report_sha256"]) == 64
    storage.upload.assert_called_once()


def test_report_task_rejects_corruption_and_invalid_shape() -> None:
    storage = Mock()

    def download(_key: str, destination: str) -> None:
        Path(destination).write_text("[]", encoding="utf-8")

    storage.download.side_effect = download
    with patch("repwise_api.worker.MinioObjectStorage", return_value=storage):
        with pytest.raises(ValueError, match="checksum mismatch"):
            publish_report_task("seg.json", "a" * 64, "id", "b" * 64, "c" * 64)
        checksum = hashlib.sha256(b"[]").hexdigest()
        with pytest.raises(ValueError, match="must be an object"):
            publish_report_task("seg.json", checksum, "id", "b" * 64, "c" * 64)


def test_readiness_task_publishes_stable_instruction() -> None:
    storage = Mock()
    payload = [
        {
            "timestamp_seconds": index * 0.1,
            "required_landmark_coverage": 0.95,
            "full_body_visible": True,
            "side_view_score": 0.9,
            "motion_px": 1,
        }
        for index in range(5)
    ]

    def download(_key: str, destination: str) -> None:
        Path(destination).write_text(json.dumps(payload), encoding="utf-8")

    storage.download.side_effect = download
    with patch("repwise_api.worker.MinioObjectStorage", return_value=storage):
        result = capture_readiness_task("capture/observations.json")
    assert result == {
        "readiness_object_key": "capture/observations.json.readiness.v1.json",
        "ready": True,
        "code": "ready",
    }
    storage.upload.assert_called_once()


def test_readiness_task_rejects_non_array_payload() -> None:
    storage = Mock()

    def download(_key: str, destination: str) -> None:
        Path(destination).write_text("{}", encoding="utf-8")

    storage.download.side_effect = download
    with (
        patch("repwise_api.worker.MinioObjectStorage", return_value=storage),
        pytest.raises(ValueError, match="must be an array"),
    ):
        capture_readiness_task("capture/observations.json")


def test_practice_task_publishes_excluded_interval() -> None:
    storage = Mock()
    payload = [
        {
            "timestamp_seconds": index * 0.1,
            "knee_angle_degrees": angle,
            "required_landmark_coverage": 0.95,
        }
        for index, angle in enumerate((170, 165, 150, 135, 100, 106, 142, 160, 170))
    ]

    def download(_key: str, destination: str) -> None:
        Path(destination).write_text(json.dumps(payload), encoding="utf-8")

    storage.download.side_effect = download
    with patch("repwise_api.worker.MinioObjectStorage", return_value=storage):
        result = practice_rep_task("capture/practice-samples.json")
    assert result == {
        "practice_object_key": "capture/practice-samples.json.practice.v1.json",
        "suitable": True,
        "code": "suitable",
    }
    storage.upload.assert_called_once()


def test_practice_task_rejects_non_array_payload() -> None:
    storage = Mock()

    def download(_key: str, destination: str) -> None:
        Path(destination).write_text("{}", encoding="utf-8")

    storage.download.side_effect = download
    with (
        patch("repwise_api.worker.MinioObjectStorage", return_value=storage),
        pytest.raises(ValueError, match="must be an array"),
    ):
        practice_rep_task("capture/practice-samples.json")
