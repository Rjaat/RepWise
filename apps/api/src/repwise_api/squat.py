from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from itertools import pairwise
from typing import Any, Literal

Phase = Literal["standing", "descending", "bottom", "ascending"]
Outcome = Literal["assessed", "not_assessable"]


class SegmentationError(ValueError):
    pass


@dataclass(frozen=True)
class AngleSample:
    timestamp_seconds: float
    knee_angle_degrees: float | None


@dataclass(frozen=True)
class PhaseInterval:
    phase: Phase
    start_seconds: float
    end_seconds: float

    def to_dict(self) -> dict[str, str | float]:
        return {
            "phase": self.phase,
            "start_seconds": self.start_seconds,
            "end_seconds": self.end_seconds,
        }


@dataclass(frozen=True)
class SquatRep:
    index: int
    complete: bool
    start_seconds: float
    end_seconds: float
    phases: tuple[PhaseInterval, ...]
    reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "complete": self.complete,
            "start_seconds": self.start_seconds,
            "end_seconds": self.end_seconds,
            "duration_seconds": self.end_seconds - self.start_seconds,
            "reason": self.reason,
            "phases": [phase.to_dict() for phase in self.phases],
        }


@dataclass(frozen=True)
class SegmentationResult:
    outcome: Outcome
    complete_reps: tuple[SquatRep, ...]
    partial_reps: tuple[SquatRep, ...]
    coverage: float
    reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "repwise.squat-segmentation.v1",
            "outcome": self.outcome,
            "coverage": self.coverage,
            "reason": self.reason,
            "complete_reps": [rep.to_dict() for rep in self.complete_reps],
            "partial_reps": [rep.to_dict() for rep in self.partial_reps],
        }


def _point(
    landmarks: Mapping[str, Any], name: str, width: int, height: int
) -> tuple[float, float] | None:
    landmark = landmarks.get(name)
    if not isinstance(landmark, dict):
        return None
    x, y = landmark.get("x"), landmark.get("y")
    if (
        isinstance(x, bool)
        or isinstance(y, bool)
        or not isinstance(x, int | float)
        or not isinstance(y, int | float)
    ):
        return None
    return float(x) * width, float(y) * height


def _angle(
    hip: tuple[float, float],
    knee: tuple[float, float],
    ankle: tuple[float, float],
) -> float | None:
    first = hip[0] - knee[0], hip[1] - knee[1]
    second = ankle[0] - knee[0], ankle[1] - knee[1]
    denominator = math.hypot(*first) * math.hypot(*second)
    if denominator == 0:
        return None
    dot_product = first[0] * second[0] + first[1] * second[1]
    cosine = max(-1.0, min(1.0, dot_product / denominator))
    return math.degrees(math.acos(cosine))


def extract_knee_angle_samples(
    artifact: Mapping[str, Any], frame_width: int, frame_height: int
) -> tuple[AngleSample, ...]:
    if frame_width <= 0 or frame_height <= 0:
        raise SegmentationError("Frame dimensions must be positive")
    frames = artifact.get("frames")
    if not isinstance(frames, list):
        raise SegmentationError("Pose artifact frames are required")
    samples: list[AngleSample] = []
    for frame in frames:
        if not isinstance(frame, dict):
            raise SegmentationError("Pose artifact frame is invalid")
        timestamp = frame.get("timestamp_seconds")
        landmarks = frame.get("landmarks")
        if not isinstance(timestamp, int | float) or not isinstance(landmarks, dict):
            raise SegmentationError("Pose artifact frame metadata is invalid")
        angles: list[float] = []
        for side in ("left", "right"):
            points = tuple(
                _point(landmarks, f"{side}_{joint}", frame_width, frame_height)
                for joint in ("hip", "knee", "ankle")
            )
            if all(point is not None for point in points):
                angle = _angle(points[0], points[1], points[2])  # type: ignore[arg-type]
                if angle is not None:
                    angles.append(angle)
        samples.append(
            AngleSample(float(timestamp), sum(angles) / len(angles) if angles else None)
        )
    return tuple(samples)


def segment_squats(
    samples: Sequence[AngleSample],
    *,
    standing_angle: float = 155.0,
    bottom_angle: float = 140.0,
    minimum_coverage: float = 0.8,
    minimum_phase_seconds: float = 0.1,
    maximum_gap_seconds: float = 0.5,
    direction_hysteresis_degrees: float = 3.0,
) -> SegmentationResult:
    if not samples:
        return SegmentationResult("not_assessable", (), (), 0.0, "no_pose_samples")
    timestamps = [sample.timestamp_seconds for sample in samples]
    if timestamps[0] < 0 or any(b <= a for a, b in pairwise(timestamps)):
        raise SegmentationError("Sample timestamps must be non-negative and increasing")
    observed = [sample for sample in samples if sample.knee_angle_degrees is not None]
    coverage = len(observed) / len(samples)
    if coverage < minimum_coverage:
        return SegmentationResult(
            "not_assessable", (), (), coverage, "insufficient_pose_coverage"
        )
    if any(
        b.timestamp_seconds - a.timestamp_seconds > maximum_gap_seconds
        for a, b in pairwise(observed)
    ):
        return SegmentationResult(
            "not_assessable", (), (), coverage, "pose_gap_too_long"
        )

    complete: list[SquatRep] = []
    partial: list[SquatRep] = []
    rep_start: float | None = None
    phase: Phase = "standing"
    phase_start = observed[0].timestamp_seconds
    phases: list[PhaseInterval] = []
    minimum_angle = float("inf")
    minimum_timestamp = phase_start

    def transition(next_phase: Phase, timestamp: float) -> None:
        nonlocal phase, phase_start
        if timestamp - phase_start >= minimum_phase_seconds - 1e-9:
            phases.append(PhaseInterval(phase, phase_start, timestamp))
        phase = next_phase
        phase_start = timestamp

    previous = observed[0]
    for current in observed[1:]:
        angle = current.knee_angle_degrees
        previous_angle = previous.knee_angle_degrees
        assert angle is not None and previous_angle is not None
        if (
            rep_start is None
            and previous_angle >= standing_angle
            and angle < standing_angle
        ):
            rep_start = previous.timestamp_seconds
            phases = []
            phase = "descending"
            phase_start = previous.timestamp_seconds
            minimum_angle = angle
            minimum_timestamp = current.timestamp_seconds
        elif rep_start is not None:
            if angle < minimum_angle:
                minimum_angle = angle
                minimum_timestamp = current.timestamp_seconds
            if phase == "descending" and angle <= bottom_angle:
                transition("bottom", current.timestamp_seconds)
            elif (
                phase == "bottom"
                and angle >= minimum_angle + direction_hysteresis_degrees
            ):
                transition("ascending", minimum_timestamp)
            elif phase == "ascending" and angle >= standing_angle:
                transition("standing", current.timestamp_seconds)
                phases.append(
                    PhaseInterval(
                        "standing", current.timestamp_seconds, current.timestamp_seconds
                    )
                )
                complete.append(
                    SquatRep(
                        len(complete) + 1,
                        True,
                        rep_start,
                        current.timestamp_seconds,
                        tuple(phases),
                    )
                )
                rep_start = None
        previous = current

    if rep_start is not None:
        end = observed[-1].timestamp_seconds
        if end > phase_start:
            phases.append(PhaseInterval(phase, phase_start, end))
        partial.append(
            SquatRep(
                len(complete) + 1,
                False,
                rep_start,
                end,
                tuple(phases),
                "incomplete_return"
                if minimum_angle <= bottom_angle
                else "incomplete_depth",
            )
        )
    if not complete and not partial:
        return SegmentationResult("not_assessable", (), (), coverage, "no_squat_motion")
    return SegmentationResult("assessed", tuple(complete), tuple(partial), coverage)
