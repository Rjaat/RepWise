from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from itertools import pairwise
from typing import Any, Literal

ReadinessCode = Literal[
    "ready",
    "checking",
    "full_body_missing",
    "wrong_view",
    "camera_unstable",
    "tracking_insufficient",
]


@dataclass(frozen=True)
class ReadinessObservation:
    timestamp_seconds: float
    required_landmark_coverage: float
    full_body_visible: bool
    side_view_score: float
    motion_px: float


@dataclass(frozen=True)
class ReadinessResult:
    ready: bool
    code: ReadinessCode
    instruction: str
    checks: dict[str, bool]
    stable_frames: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "repwise.capture-readiness.v1",
            "ready": self.ready,
            "code": self.code,
            "instruction": self.instruction,
            "checks": self.checks,
            "stable_frames": self.stable_frames,
        }


INSTRUCTIONS: dict[ReadinessCode, str] = {
    "ready": "Suitable for side-view assessment.",
    "checking": "Hold this position while we check the view.",
    "full_body_missing": "Move back until your full body and feet are visible.",
    "wrong_view": "Turn sideways so we can assess this movement.",
    "camera_unstable": "Keep the camera still before continuing.",
    "tracking_insufficient": "Improve the lighting so your body remains visible.",
}


def _frame_code(
    observation: ReadinessObservation,
    *,
    minimum_coverage: float,
    minimum_side_score: float,
    maximum_motion_px: float,
) -> ReadinessCode:
    if not observation.full_body_visible:
        return "full_body_missing"
    if observation.side_view_score < minimum_side_score:
        return "wrong_view"
    if observation.motion_px > maximum_motion_px:
        return "camera_unstable"
    if observation.required_landmark_coverage < minimum_coverage:
        return "tracking_insufficient"
    return "ready"


def evaluate_readiness(
    observations: Sequence[ReadinessObservation],
    *,
    stable_frames: int = 5,
    minimum_coverage: float = 0.8,
    minimum_side_score: float = 0.75,
    maximum_motion_px: float = 4.0,
) -> ReadinessResult:
    if stable_frames < 1:
        raise ValueError("stable_frames must be positive")
    checks = {
        "full_movement_visible": False,
        "side_view_suitable": False,
        "camera_stable": False,
        "tracking_sufficient": False,
    }
    if not observations:
        return ReadinessResult(False, "checking", INSTRUCTIONS["checking"], checks, 0)
    timestamps = [item.timestamp_seconds for item in observations]
    if timestamps[0] < 0 or any(
        current <= previous for previous, current in pairwise(timestamps)
    ):
        raise ValueError("Observation timestamps must be non-negative and increasing")
    latest = observations[-1]
    checks = {
        "full_movement_visible": latest.full_body_visible,
        "side_view_suitable": latest.side_view_score >= minimum_side_score,
        "camera_stable": latest.motion_px <= maximum_motion_px,
        "tracking_sufficient": latest.required_landmark_coverage >= minimum_coverage,
    }
    window = observations[-stable_frames:]
    codes = [
        _frame_code(
            item,
            minimum_coverage=minimum_coverage,
            minimum_side_score=minimum_side_score,
            maximum_motion_px=maximum_motion_px,
        )
        for item in window
    ]
    trailing = 0
    for code in reversed(codes):
        if code != codes[-1]:
            break
        trailing += 1
    if len(window) < stable_frames or trailing < stable_frames:
        return ReadinessResult(
            False, "checking", INSTRUCTIONS["checking"], checks, trailing
        )
    code = Counter(codes).most_common(1)[0][0]
    return ReadinessResult(code == "ready", code, INSTRUCTIONS[code], checks, trailing)
