from __future__ import annotations

import hashlib
import importlib
import json
import subprocess
from pathlib import Path
from typing import Any, Final

from repwise_api.pose import LANDMARK_NAMES

ZERO_LANDMARK: Final = {
    "x": 0.0,
    "y": 0.0,
    "z": 0.0,
    "visibility": 0.0,
    "presence": 0.0,
}


class PoseInferenceError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _verify_model(path: Path, expected_sha256: str) -> None:
    if not path.is_file():
        raise PoseInferenceError("model_not_found", "Pose model file was not found")
    if _sha256(path) != expected_sha256:
        raise PoseInferenceError(
            "model_checksum_mismatch", "Pose model checksum mismatch"
        )


def _extract_frames(video: Path, destination: Path, sample_fps: float) -> list[Path]:
    destination.mkdir()
    command = [
        "ffmpeg",
        "-v",
        "error",
        "-i",
        str(video),
        "-vf",
        f"fps={sample_fps}",
        "-start_number",
        "0",
        str(destination / "%08d.png"),
    ]
    try:
        subprocess.run(command, check=True, capture_output=True)
    except (OSError, subprocess.CalledProcessError) as error:
        raise PoseInferenceError(
            "frame_extraction_failed", "Could not sample video frames"
        ) from error
    frames = sorted(destination.glob("*.png"))
    if not frames:
        raise PoseInferenceError("no_frames", "Video produced no inference frames")
    return frames


def _load_mediapipe() -> Any:
    try:
        return importlib.import_module("mediapipe")
    except ImportError as error:
        raise PoseInferenceError(
            "runtime_unavailable", "MediaPipe inference runtime is not installed"
        ) from error


def _landmark_payload(landmark: Any) -> dict[str, float]:
    return {
        "x": float(landmark.x),
        "y": float(landmark.y),
        "z": float(landmark.z),
        "visibility": float(landmark.visibility),
        "presence": float(landmark.presence),
    }


def run_pose_inference(
    video: Path,
    model: Path,
    destination: Path,
    *,
    expected_model_sha256: str,
    sample_fps: float,
) -> dict[str, int | str]:
    """Run pinned MediaPipe VIDEO inference and emit deterministic adapter JSON."""
    _verify_model(model, expected_model_sha256)
    mediapipe = _load_mediapipe()
    frames_dir = destination.parent / "frames"
    frames = _extract_frames(video, frames_dir, sample_fps)
    options = mediapipe.tasks.vision.PoseLandmarkerOptions(
        base_options=mediapipe.tasks.BaseOptions(model_asset_path=str(model)),
        running_mode=mediapipe.tasks.vision.RunningMode.VIDEO,
        num_poses=1,
    )
    output: list[dict[str, Any]] = []
    detected = 0
    try:
        with mediapipe.tasks.vision.PoseLandmarker.create_from_options(
            options
        ) as detector:
            for index, frame in enumerate(frames):
                timestamp_ms = round(index * 1000 / sample_fps)
                result = detector.detect_for_video(
                    mediapipe.Image.create_from_file(str(frame)), timestamp_ms
                )
                if result.pose_landmarks:
                    landmarks = [
                        _landmark_payload(item) for item in result.pose_landmarks[0]
                    ]
                    if len(landmarks) != len(LANDMARK_NAMES):
                        raise PoseInferenceError(
                            "invalid_landmark_count",
                            "Pose runtime did not return 33 landmarks",
                        )
                    detected += 1
                else:
                    landmarks = [dict(ZERO_LANDMARK) for _ in LANDMARK_NAMES]
                output.append(
                    {
                        "timestamp_seconds": timestamp_ms / 1000,
                        "landmarks": landmarks,
                    }
                )
    except PoseInferenceError:
        raise
    except Exception as error:
        raise PoseInferenceError("inference_failed", "Pose inference failed") from error
    if detected == 0:
        raise PoseInferenceError("no_pose_detected", "No person pose was detected")
    destination.write_text(
        json.dumps({"frames": output}, separators=(",", ":"), sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return {
        "inference_sha256": _sha256(destination),
        "frame_count": len(output),
        "detected_frame_count": detected,
    }
