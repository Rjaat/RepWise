from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from itertools import pairwise
from typing import Any, Literal

from repwise_api.squat import AngleSample

PracticeCode = Literal[
    "suitable",
    "insufficient_coverage",
    "insufficient_motion",
    "too_short",
]


@dataclass(frozen=True)
class PracticeSample:
    timestamp_seconds: float
    knee_angle_degrees: float | None
    required_landmark_coverage: float


@dataclass(frozen=True)
class PracticeResult:
    suitable: bool
    code: PracticeCode
    start_seconds: float
    end_seconds: float
    observed_coverage: float
    angle_excursion_degrees: float | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "repwise.practice-rep.v1",
            "suitable": self.suitable,
            "code": self.code,
            "excluded_interval": {
                "start_seconds": self.start_seconds,
                "end_seconds": self.end_seconds,
            },
            "observed_coverage": self.observed_coverage,
            "angle_excursion_degrees": self.angle_excursion_degrees,
        }


def evaluate_practice_rep(
    samples: Sequence[PracticeSample],
    *,
    minimum_duration_seconds: float = 0.5,
    minimum_coverage: float = 0.8,
    minimum_excursion_degrees: float = 30.0,
) -> PracticeResult:
    if not samples:
        raise ValueError("Practice samples are required")
    timestamps = [sample.timestamp_seconds for sample in samples]
    if timestamps[0] < 0 or any(b <= a for a, b in pairwise(timestamps)):
        raise ValueError("Practice timestamps must be non-negative and increasing")
    start, end = timestamps[0], timestamps[-1]
    observed_coverage = sum(
        sample.required_landmark_coverage for sample in samples
    ) / len(samples)
    angles = [
        sample.knee_angle_degrees
        for sample in samples
        if sample.knee_angle_degrees is not None
    ]
    excursion = max(angles) - min(angles) if angles else None
    if end - start < minimum_duration_seconds:
        code: PracticeCode = "too_short"
    elif (
        observed_coverage < minimum_coverage
        or len(angles) / len(samples) < minimum_coverage
    ):
        code = "insufficient_coverage"
    elif excursion is None or excursion < minimum_excursion_degrees:
        code = "insufficient_motion"
    else:
        code = "suitable"
    return PracticeResult(
        code == "suitable", code, start, end, observed_coverage, excursion
    )


def exclude_practice_interval(
    samples: Sequence[AngleSample], result: PracticeResult
) -> tuple[AngleSample, ...]:
    return tuple(
        sample
        for sample in samples
        if not result.start_seconds <= sample.timestamp_seconds <= result.end_seconds
    )
