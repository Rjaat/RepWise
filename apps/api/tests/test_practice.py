import pytest

from repwise_api.practice import (
    PracticeSample,
    evaluate_practice_rep,
    exclude_practice_interval,
)
from repwise_api.squat import AngleSample, segment_squats

ANGLES = (170, 165, 150, 135, 100, 106, 142, 160, 170)


def practice_samples(
    *, coverage: float = 0.95, angle_values: tuple[float | None, ...] = ANGLES
) -> list[PracticeSample]:
    return [
        PracticeSample(index * 0.1, angle, coverage)
        for index, angle in enumerate(angle_values)
    ]


@pytest.mark.parametrize(
    ("samples", "code"),
    [
        (practice_samples(), "suitable"),
        (practice_samples(coverage=0.4), "insufficient_coverage"),
        (practice_samples(angle_values=(170,) * 9), "insufficient_motion"),
        (practice_samples(angle_values=(None,) * 9), "insufficient_coverage"),
        (practice_samples()[:3], "too_short"),
    ],
)
def test_practice_suitability_has_explicit_outcomes(
    samples: list[PracticeSample], code: str
) -> None:
    result = evaluate_practice_rep(samples)
    assert result.code == code
    assert result.suitable is (code == "suitable")
    assert result.to_dict()["schema"] == "repwise.practice-rep.v1"


def test_practice_interval_cannot_enter_final_rep_count() -> None:
    practice = [
        AngleSample(item.timestamp_seconds, item.knee_angle_degrees)
        for item in practice_samples()
    ]
    recorded = [
        AngleSample(1.0 + index * 0.1, angle) for index, angle in enumerate(ANGLES)
    ]
    all_samples = practice + recorded
    result = evaluate_practice_rep(practice_samples())

    assert len(segment_squats(all_samples).complete_reps) == 2
    analysed = segment_squats(exclude_practice_interval(all_samples, result))
    assert len(analysed.complete_reps) == 1
    assert analysed.complete_reps[0].start_seconds >= 1


def test_rejects_empty_and_invalid_timestamps() -> None:
    with pytest.raises(ValueError, match="required"):
        evaluate_practice_rep([])
    for samples in (
        [PracticeSample(-1, 170, 1)],
        [PracticeSample(0, 170, 1), PracticeSample(0, 160, 1)],
    ):
        with pytest.raises(ValueError, match="timestamps"):
            evaluate_practice_rep(samples)
