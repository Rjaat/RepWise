import json
from pathlib import Path

import pytest

from repwise_api.readiness import ReadinessObservation, evaluate_readiness


def observations(**changes: object) -> list[ReadinessObservation]:
    values = {
        "required_landmark_coverage": 0.95,
        "full_body_visible": True,
        "side_view_score": 0.9,
        "motion_px": 1.0,
        **changes,
    }
    return [ReadinessObservation(index * 0.1, **values) for index in range(5)]  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("changes", "code"),
    [
        ({}, "ready"),
        ({"full_body_visible": False}, "full_body_missing"),
        ({"side_view_score": 0.2}, "wrong_view"),
        ({"motion_px": 10.0}, "camera_unstable"),
        ({"required_landmark_coverage": 0.2}, "tracking_insufficient"),
    ],
)
def test_emits_one_stable_prioritized_instruction(
    changes: dict[str, object], code: str
) -> None:
    result = evaluate_readiness(observations(**changes))
    assert result.code == code
    assert result.ready is (code == "ready")
    assert result.stable_frames == 5
    assert result.to_dict()["schema"] == "repwise.capture-readiness.v1"


def test_hysteresis_withholds_flapping_prompts() -> None:
    frames = observations()
    frames[-1] = ReadinessObservation(0.4, 0.95, False, 0.9, 1)
    result = evaluate_readiness(frames)
    assert result.code == "checking"
    assert result.stable_frames == 1
    assert result.instruction == "Hold this position while we check the view."


def test_empty_short_and_invalid_sequences_are_safe() -> None:
    assert evaluate_readiness([]).code == "checking"
    assert evaluate_readiness(observations()[:2]).code == "checking"
    with pytest.raises(ValueError, match="stable_frames"):
        evaluate_readiness(observations(), stable_frames=0)
    for invalid in (
        [ReadinessObservation(-1, 1, True, 1, 0)],
        [ReadinessObservation(0, 1, True, 1, 0)] * 2,
    ):
        with pytest.raises(ValueError, match="timestamps"):
            evaluate_readiness(invalid)


def test_difficult_setup_fixture_has_zero_false_ready_results() -> None:
    fixture = Path(__file__).parent / "fixtures/readiness/difficult-setups.json"
    cases = json.loads(fixture.read_text(encoding="utf-8"))
    false_ready = 0
    unsuitable = 0
    for case in cases:
        result = evaluate_readiness(
            observations(
                required_landmark_coverage=case["coverage"],
                full_body_visible=case["full_body"],
                side_view_score=case["side_score"],
                motion_px=case["motion_px"],
            )
        )
        if not case["suitable"]:
            unsuitable += 1
            false_ready += int(result.ready)
    assert unsuitable == 4
    assert false_ready / unsuitable == 0
