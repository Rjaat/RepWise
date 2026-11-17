import json
from pathlib import Path
from typing import Any

import pytest

from repwise_api.squat import (
    AngleSample,
    SegmentationError,
    extract_knee_angle_samples,
    segment_squats,
)


def motion(start: float = 0.0) -> list[AngleSample]:
    angles = (170, 165, 150, 135, 100, 105, 140, 160, 170)
    return [
        AngleSample(start + index * 0.1, angle) for index, angle in enumerate(angles)
    ]


def test_held_out_fixture_count_gate_or_abstains() -> None:
    fixture = Path(__file__).parent / "fixtures/squat/held-out-cases.json"
    cases = json.loads(fixture.read_text(encoding="utf-8"))

    for case in cases:
        result = segment_squats(
            [AngleSample(timestamp, angle) for timestamp, angle in case["samples"]]
        )
        assert result.outcome == case["expected_outcome"], case["id"]
        assert len(result.complete_reps) == case["expected_complete_reps"], case["id"]


def test_counts_complete_reps_and_uses_timestamps_for_phase_tempo() -> None:
    samples = motion() + motion(1.0)

    result = segment_squats(samples)

    assert result.outcome == "assessed"
    assert len(result.complete_reps) == 2
    assert result.partial_reps == ()
    first = result.complete_reps[0]
    assert first.start_seconds == pytest.approx(0.1)
    assert first.end_seconds == pytest.approx(0.7)
    assert [phase.phase for phase in first.phases] == [
        "descending",
        "bottom",
        "ascending",
        "standing",
    ]
    assert first.phases[0].end_seconds - first.phases[0].start_seconds == pytest.approx(
        0.2
    )
    assert result.to_dict()["schema"] == "repwise.squat-segmentation.v1"
    assert first.to_dict()["duration_seconds"] == pytest.approx(0.6)


@pytest.mark.parametrize(
    ("samples", "reason"),
    [
        ([], "no_pose_samples"),
        ([AngleSample(0, 170), AngleSample(0.1, None)], "insufficient_pose_coverage"),
        ([AngleSample(0, 170), AngleSample(1, 160)], "pose_gap_too_long"),
        ([AngleSample(0, 170), AngleSample(0.1, 165)], "no_squat_motion"),
    ],
)
def test_abstains_with_explicit_reason(samples: list[AngleSample], reason: str) -> None:
    result = segment_squats(samples)
    assert result.outcome == "not_assessable"
    assert result.reason == reason


def test_records_partial_reps_without_counting_them_complete() -> None:
    incomplete_return = motion()[:-2]
    incomplete_depth = [
        AngleSample(0, 170),
        AngleSample(0.1, 160),
        AngleSample(0.2, 150),
        AngleSample(0.3, 145),
    ]

    return_result = segment_squats(incomplete_return)
    depth_result = segment_squats(incomplete_depth)

    assert return_result.complete_reps == ()
    assert return_result.partial_reps[0].reason == "incomplete_return"
    assert depth_result.partial_reps[0].reason == "incomplete_depth"
    assert return_result.partial_reps[0].to_dict()["complete"] is False


def test_rejects_invalid_timestamp_order() -> None:
    for samples in (
        [AngleSample(-1, 170)],
        [AngleSample(0, 170), AngleSample(0, 160)],
    ):
        with pytest.raises(SegmentationError, match="timestamps"):
            segment_squats(samples)


def artifact(landmarks: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "frames": [
            {
                "timestamp_seconds": 0,
                "landmarks": landmarks
                if landmarks is not None
                else {
                    "left_hip": {"x": 0.5, "y": 0.25},
                    "left_knee": {"x": 0.5, "y": 0.5},
                    "left_ankle": {"x": 0.75, "y": 0.5},
                },
            }
        ]
    }


def test_extracts_aspect_correct_knee_angles_and_averages_visible_sides() -> None:
    landmarks = artifact()["frames"][0]["landmarks"]
    landmarks.update(
        {
            "right_hip": {"x": 0.5, "y": 0.25},
            "right_knee": {"x": 0.5, "y": 0.5},
            "right_ankle": {"x": 0.75, "y": 0.5},
        }
    )
    samples = extract_knee_angle_samples(artifact(landmarks), 100, 200)
    assert samples == (AngleSample(0, pytest.approx(90)),)


def test_extracts_missing_and_degenerate_landmarks_as_unobserved() -> None:
    assert (
        extract_knee_angle_samples(artifact({}), 100, 200)[0].knee_angle_degrees is None
    )
    degenerate = {
        f"left_{joint}": {"x": 0.5, "y": 0.5} for joint in ("hip", "knee", "ankle")
    }
    assert (
        extract_knee_angle_samples(artifact(degenerate), 100, 200)[0].knee_angle_degrees
        is None
    )


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ({}, "frames"),
        ({"frames": [None]}, "frame is invalid"),
        ({"frames": [{}]}, "metadata is invalid"),
    ],
)
def test_rejects_invalid_pose_artifacts(payload: dict[str, Any], message: str) -> None:
    with pytest.raises(SegmentationError, match=message):
        extract_knee_angle_samples(payload, 100, 200)


def test_rejects_invalid_dimensions_and_ignores_malformed_points() -> None:
    with pytest.raises(SegmentationError, match="dimensions"):
        extract_knee_angle_samples(artifact(), 0, 200)
    malformed = {
        "left_hip": {"x": True, "y": 0.2},
        "left_knee": {"x": 0.5, "y": 0.5},
        "left_ankle": {"x": 0.5, "y": 0.8},
    }
    assert (
        extract_knee_angle_samples(artifact(malformed), 100, 200)[0].knee_angle_degrees
        is None
    )
