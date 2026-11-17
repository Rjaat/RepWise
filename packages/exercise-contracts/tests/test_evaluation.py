from __future__ import annotations

import pytest

from repwise_exercise_contracts import (
    EvaluationRecord,
    assert_participant_disjoint,
    evaluate_release,
    wilson_interval,
)


def record(
    participant: str,
    *,
    split: str = "test",
    accepted: bool = True,
    observed_count: int = 10,
    check_expected: bool = True,
    check_observed: bool = True,
    setup_ready: bool = False,
) -> EvaluationRecord:
    return EvaluationRecord(
        participant_id=participant,
        split=split,
        exercise="bodyweight_squat",
        subgroup="mobile/side",
        eligible=True,
        accepted=accepted,
        ground_truth_count=10,
        observed_count=observed_count,
        phase_error_seconds=0.1,
        difficult_setup=True,
        setup_ready=setup_ready,
        check_id="visible_depth_consistency",
        check_expected=check_expected,
        check_observed=check_observed,
    )


def test_release_passes_only_when_every_gate_has_evidence() -> None:
    synthetic_test_only = [record(f"participant-{index}") for index in range(30)]
    result = evaluate_release(
        synthetic_test_only,
        approved_checks={"visible_depth_consistency"},
        adversarial_claims_supported=[True, True],
        operational_gates={
            "device_experience": True,
            "upload_service": True,
            "reliability": True,
        },
    )

    assert result.release_ready is True
    assert result.blockers == ()
    assert result.participants == 30
    assert result.exact_count_agreement.value == 1
    assert result.count_mae == 0
    assert result.median_phase_error_seconds == 0.1
    assert result.coverage.value == 1
    assert result.false_ready_rate.value == 0
    assert result.checks["visible_depth_consistency"].precision.value == 1
    assert result.subgroup_coverage["mobile/side"].sample_size == 30


def test_release_fails_closed_with_specific_scope_blockers() -> None:
    synthetic_test_only = [
        record(
            "one",
            accepted=False,
            observed_count=9,
            check_observed=False,
            setup_ready=True,
        ),
        record("two", observed_count=9, check_expected=False),
    ]
    result = evaluate_release(
        synthetic_test_only,
        approved_checks=set(),
        adversarial_claims_supported=[True, False],
        operational_gates={},
    )

    assert result.release_ready is False
    assert set(result.blockers) == {
        "check_not_approved:visible_depth_consistency",
        "precision_below_gate:visible_depth_consistency",
        "recall_below_gate:visible_depth_consistency",
        "insufficient_test_participants",
        "exact_count_agreement_below_gate",
        "coverage_below_gate",
        "unsupported_adversarial_report_claim",
        "false_ready_above_gate",
        "operational_evidence_missing:device_experience",
        "operational_evidence_missing:upload_service",
        "operational_evidence_missing:reliability",
    }
    assert result.count_mae == 1


def test_empty_evidence_cannot_pass() -> None:
    result = evaluate_release(
        [], approved_checks=set(), adversarial_claims_supported=[], operational_gates={}
    )

    assert result.release_ready is False
    assert result.exact_count_agreement == wilson_interval(0, 0)
    assert "no_check_evidence" in result.blockers


def test_participant_split_leakage_is_rejected_before_scoring() -> None:
    records = [record("same", split="train"), record("same", split="test")]

    with pytest.raises(ValueError, match="participant split leakage: same"):
        assert_participant_disjoint(records)
    with pytest.raises(ValueError, match="participant split leakage: same"):
        evaluate_release(
            records,
            approved_checks={"visible_depth_consistency"},
            adversarial_claims_supported=[True],
            operational_gates={
                "device_experience": True,
                "upload_service": True,
                "reliability": True,
            },
        )


def test_wilson_interval_reports_sample_size_and_uncertainty() -> None:
    interval = wilson_interval(19, 20)

    assert interval.value == 0.95
    assert interval.sample_size == 20
    assert 0 < interval.confidence_low < interval.value
    assert interval.value < interval.confidence_high < 1
