from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

ARTIFACT_SCHEMA: Final = "repwise.pose-artifact.v1"
MEDIAPIPE_SCHEMA: Final = "mediapipe.pose-33.v1"
LANDMARK_NAMES: Final = (
    "nose",
    "left_eye_inner",
    "left_eye",
    "left_eye_outer",
    "right_eye_inner",
    "right_eye",
    "right_eye_outer",
    "left_ear",
    "right_ear",
    "mouth_left",
    "mouth_right",
    "left_shoulder",
    "right_shoulder",
    "left_elbow",
    "right_elbow",
    "left_wrist",
    "right_wrist",
    "left_pinky",
    "right_pinky",
    "left_index",
    "right_index",
    "left_thumb",
    "right_thumb",
    "left_hip",
    "right_hip",
    "left_knee",
    "right_knee",
    "left_ankle",
    "right_ankle",
    "left_heel",
    "right_heel",
    "left_foot_index",
    "right_foot_index",
)


class PoseArtifactError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class ModelIdentity:
    name: str
    version: str
    sha256: str

    def __post_init__(self) -> None:
        if not self.name or not self.version:
            raise PoseArtifactError(
                "invalid_model", "Model name and version are required"
            )
        _validate_sha256(self.sha256, "model")

    def to_dict(self) -> dict[str, str]:
        return {"name": self.name, "version": self.version, "sha256": self.sha256}


def _validate_sha256(value: str, label: str) -> None:
    if len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
        raise PoseArtifactError("invalid_checksum", f"Invalid {label} SHA-256")


def _number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise PoseArtifactError("invalid_landmark", f"{label} must be numeric")
    return float(value)


def _canonical_bytes(payload: Mapping[str, Any]) -> bytes:
    return json.dumps(
        payload, allow_nan=False, separators=(",", ":"), sort_keys=True
    ).encode()


def adapt_mediapipe_landmarks(
    landmarks: Sequence[Mapping[str, Any]], minimum_visibility: float
) -> dict[str, dict[str, float] | None]:
    if len(landmarks) != len(LANDMARK_NAMES):
        raise PoseArtifactError(
            "invalid_landmark_count", "MediaPipe Pose output must have 33 landmarks"
        )
    adapted: dict[str, dict[str, float] | None] = {}
    for name, raw in zip(LANDMARK_NAMES, landmarks, strict=True):
        visibility = _number(raw.get("visibility"), f"{name}.visibility")
        presence = _number(raw.get("presence", visibility), f"{name}.presence")
        if visibility < minimum_visibility or presence < minimum_visibility:
            adapted[name] = None
            continue
        adapted[name] = {
            "x": _number(raw.get("x"), f"{name}.x"),
            "y": _number(raw.get("y"), f"{name}.y"),
            "z": _number(raw.get("z"), f"{name}.z"),
            "visibility": visibility,
            "presence": presence,
        }
    return adapted


def build_pose_artifact(
    *,
    source_sha256: str,
    model: ModelIdentity,
    frames: Sequence[Mapping[str, Any]],
    minimum_visibility: float = 0.5,
) -> dict[str, Any]:
    _validate_sha256(source_sha256, "source")
    if not 0 <= minimum_visibility <= 1:
        raise PoseArtifactError(
            "invalid_visibility_threshold",
            "Visibility threshold must be between 0 and 1",
        )
    output_frames: list[dict[str, Any]] = []
    previous_timestamp = -1.0
    missing_count = 0
    for index, frame in enumerate(frames):
        timestamp = _number(frame.get("timestamp_seconds"), "timestamp_seconds")
        if timestamp < 0 or timestamp <= previous_timestamp:
            raise PoseArtifactError(
                "invalid_timestamps",
                "Frame timestamps must be non-negative and increasing",
            )
        raw_landmarks = frame.get("landmarks")
        if not isinstance(raw_landmarks, list):
            raise PoseArtifactError(
                "invalid_landmarks", "Frame landmarks must be an array"
            )
        landmarks = adapt_mediapipe_landmarks(raw_landmarks, minimum_visibility)
        missing_count += sum(value is None for value in landmarks.values())
        output_frames.append(
            {
                "frame_index": index,
                "timestamp_seconds": timestamp,
                "landmarks": landmarks,
            }
        )
        previous_timestamp = timestamp

    landmark_total = len(output_frames) * len(LANDMARK_NAMES)
    payload: dict[str, Any] = {
        "schema": ARTIFACT_SCHEMA,
        "landmark_schema": MEDIAPIPE_SCHEMA,
        "source_sha256": source_sha256,
        "model": model.to_dict(),
        "preprocessing": {
            "coordinate_space": "normalized_image",
            "minimum_visibility": minimum_visibility,
            "timestamp_unit": "seconds",
        },
        "summary": {
            "frame_count": len(output_frames),
            "missing_landmark_count": missing_count,
            "observed_landmark_count": landmark_total - missing_count,
        },
        "frames": output_frames,
    }
    payload["artifact_sha256"] = hashlib.sha256(_canonical_bytes(payload)).hexdigest()
    return payload


def build_pose_artifact_file(
    source: Path,
    destination: Path,
    *,
    source_sha256: str,
    model: ModelIdentity,
    expected_input_sha256: str,
    minimum_visibility: float = 0.5,
) -> dict[str, Any]:
    actual = hashlib.sha256(source.read_bytes()).hexdigest()
    if actual != expected_input_sha256:
        raise PoseArtifactError("checksum_mismatch", "Pose inference checksum mismatch")
    try:
        decoded = json.loads(source.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise PoseArtifactError(
            "invalid_inference", "Invalid pose inference JSON"
        ) from error
    if not isinstance(decoded, dict) or not isinstance(decoded.get("frames"), list):
        raise PoseArtifactError(
            "invalid_inference", "Pose inference frames are required"
        )
    artifact = build_pose_artifact(
        source_sha256=source_sha256,
        model=model,
        frames=decoded["frames"],
        minimum_visibility=minimum_visibility,
    )
    destination.write_bytes(_canonical_bytes(artifact) + b"\n")
    return artifact
