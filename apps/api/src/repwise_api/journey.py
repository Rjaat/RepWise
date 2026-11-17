from __future__ import annotations

import hashlib
import json
import math
import subprocess
import uuid
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from repwise_api.settings import get_settings
from repwise_api.storage import MinioObjectStorage
from repwise_api.worker import (
    media_preflight_task,
    pose_artifact_task,
    publish_report_task,
    squat_segmentation_task,
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _landmarks(angle: float) -> list[dict[str, float]]:
    points = [
        {"x": 0.5, "y": 0.5, "z": 0.0, "visibility": 0.99, "presence": 0.99}
        for _ in range(33)
    ]
    radians = math.radians(angle)
    ankle = {"x": 0.5 + math.sin(radians) * 0.15, "y": 0.5 - math.cos(radians) * 0.2}
    for indices in ((23, 25, 27), (24, 26, 28)):
        points[indices[0]].update(x=0.5, y=0.3)
        points[indices[1]].update(x=0.5, y=0.5)
        points[indices[2]].update(**ankle)
    return points


def _inference_payload() -> dict[str, Any]:
    angles = (170, 165, 150, 135, 100, 106, 142, 160, 170)
    return {
        "frames": [
            {"timestamp_seconds": index * 0.25, "landmarks": _landmarks(angle)}
            for index, angle in enumerate(angles)
        ]
    }


def _task_result(task: Any, *args: Any) -> dict[str, Any]:
    result = task.delay(*args)
    try:
        payload = result.get(timeout=60)
        if not isinstance(payload, dict):
            raise RuntimeError("Worker returned a non-object result")
        return payload
    finally:
        result.forget()


def main() -> None:  # pragma: no cover - exercised against real local services
    settings = get_settings()
    storage = MinioObjectStorage(settings)
    run_id = uuid.uuid4().hex
    prefix = f"e2e/{run_id}"
    with TemporaryDirectory(prefix="repwise-e2e-") as directory:
        root = Path(directory)
        video = root / "source.mp4"
        subprocess.run(
            [
                "ffmpeg",
                "-loglevel",
                "error",
                "-f",
                "lavfi",
                "-i",
                "color=c=black:s=320x240:r=12:d=3",
                "-an",
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                str(video),
            ],
            check=True,
        )
        source_sha256 = _sha256(video)
        source_key = f"{prefix}/source"
        storage.client.fput_object(
            storage.bucket,
            source_key,
            str(video),
            content_type="video/mp4",
            metadata={"sha256": source_sha256},
        )
        preflight = _task_result(media_preflight_task, source_key, source_sha256)

        inference = root / "inference.json"
        inference.write_text(
            json.dumps(_inference_payload(), separators=(",", ":"), sort_keys=True),
            encoding="utf-8",
        )
        inference_key = f"{prefix}/inference.json"
        storage.upload(inference_key, str(inference), "application/json")
        pose = _task_result(
            pose_artifact_task,
            inference_key,
            _sha256(inference),
            preflight["preflight"]["normalized_sha256"],
            "MediaPipe Pose Landmarker Full",
            "fixture-v1",
            "d" * 64,
        )
        pose_file = root / "pose.json"
        storage.download(pose["artifact_object_key"], str(pose_file))
        pose_file_sha256 = _sha256(pose_file)
        segmentation = _task_result(
            squat_segmentation_task,
            pose["artifact_object_key"],
            pose_file_sha256,
            320,
            240,
        )
        segmentation_file = root / "segmentation.json"
        storage.download(
            segmentation["segmentation_object_key"], str(segmentation_file)
        )
        segmentation_sha256 = _sha256(segmentation_file)

        try:
            _task_result(
                publish_report_task,
                segmentation["segmentation_object_key"],
                "0" * 64,
                run_id,
                source_sha256,
                pose["artifact_sha256"],
            )
        except ValueError as error:
            if "checksum mismatch" not in str(error):
                raise
        else:
            raise RuntimeError("Failure injection did not reject corrupt checksum")

        report_args = (
            segmentation["segmentation_object_key"],
            segmentation_sha256,
            run_id,
            source_sha256,
            pose["artifact_sha256"],
        )
        first_report = _task_result(publish_report_task, *report_args)
        retried_report = _task_result(publish_report_task, *report_args)
        if first_report != retried_report:
            raise RuntimeError("Report retry produced a duplicate or changed artifact")
        if first_report["rep_count"] != 1:
            raise RuntimeError("Expected one complete synthetic repetition")
        print(
            "RepWise upload-to-report journey completed; corruption was rejected "
            "and retry remained idempotent."
        )


if __name__ == "__main__":  # pragma: no cover
    main()
