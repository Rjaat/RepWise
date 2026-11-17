from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class EvaluationRecord:
    participant_id: str
    split: str
    exercise: str
    subgroup: str
    eligible: bool
    accepted: bool
    ground_truth_count: int | None
    observed_count: int | None
    phase_error_seconds: float | None = None
    difficult_setup: bool = False
    setup_ready: bool | None = None
    check_id: str | None = None
    check_expected: bool | None = None
    check_observed: bool | None = None


@dataclass(frozen=True)
class IntervalMetric:
    value: float
    sample_size: int
    confidence_low: float
    confidence_high: float


@dataclass(frozen=True)
class CheckMetrics:
    precision: IntervalMetric
    recall: IntervalMetric


@dataclass(frozen=True)
class EvaluationResult:
    release_ready: bool
    blockers: tuple[str, ...]
    participants: int
    exact_count_agreement: IntervalMetric
    count_mae: float | None
    median_phase_error_seconds: float | None
    coverage: IntervalMetric
    false_ready_rate: IntervalMetric
    checks: Mapping[str, CheckMetrics]
    subgroup_coverage: Mapping[str, IntervalMetric]


def wilson_interval(successes: int, total: int) -> IntervalMetric:
    if total == 0:
        return IntervalMetric(0.0, 0, 0.0, 1.0)
    value = successes / total
    z = 1.959963984540054
    denominator = 1 + z * z / total
    centre = (value + z * z / (2 * total)) / denominator
    margin = (
        z
        * math.sqrt(value * (1 - value) / total + z * z / (4 * total * total))
        / denominator
    )
    return IntervalMetric(
        value, total, max(0.0, centre - margin), min(1.0, centre + margin)
    )


def assert_participant_disjoint(records: Iterable[EvaluationRecord]) -> None:
    participant_splits: dict[str, set[str]] = defaultdict(set)
    for record in records:
        participant_splits[record.participant_id].add(record.split)
    leaked = sorted(
        participant
        for participant, splits in participant_splits.items()
        if len(splits) > 1
    )
    if leaked:
        raise ValueError(f"participant split leakage: {', '.join(leaked)}")


def evaluate_release(
    records: Sequence[EvaluationRecord],
    *,
    approved_checks: set[str],
    adversarial_claims_supported: Sequence[bool],
    operational_gates: Mapping[str, bool],
    minimum_participants: int = 30,
) -> EvaluationResult:
    assert_participant_disjoint(records)
    test_records = [record for record in records if record.split == "test"]
    participants = len({record.participant_id for record in test_records})
    eligible = [record for record in test_records if record.eligible]
    accepted = [record for record in eligible if record.accepted]
    counted = [
        record
        for record in accepted
        if record.ground_truth_count is not None and record.observed_count is not None
    ]
    exact = wilson_interval(
        sum(record.ground_truth_count == record.observed_count for record in counted),
        len(counted),
    )
    coverage = wilson_interval(len(accepted), len(eligible))
    count_mae = (
        sum(
            abs(record.ground_truth_count - record.observed_count)
            for record in counted
            if record.ground_truth_count is not None
            and record.observed_count is not None
        )
        / len(counted)
        if counted
        else None
    )
    phase_errors = sorted(
        record.phase_error_seconds
        for record in accepted
        if record.phase_error_seconds is not None
    )
    median_phase_error = (
        phase_errors[len(phase_errors) // 2]
        if len(phase_errors) % 2 == 1
        else (
            phase_errors[len(phase_errors) // 2 - 1]
            + phase_errors[len(phase_errors) // 2]
        )
        / 2
        if phase_errors
        else None
    )
    difficult_setups = [record for record in test_records if record.difficult_setup]
    false_ready = wilson_interval(
        sum(record.setup_ready is True for record in difficult_setups),
        len(difficult_setups),
    )

    by_check: dict[str, list[EvaluationRecord]] = defaultdict(list)
    by_subgroup: dict[str, list[EvaluationRecord]] = defaultdict(list)
    for record in test_records:
        by_subgroup[record.subgroup].append(record)
        if record.check_id:
            by_check[record.check_id].append(record)

    checks: dict[str, CheckMetrics] = {}
    blockers: list[str] = []
    for check_id, check_records in sorted(by_check.items()):
        tp = sum(
            record.check_expected is True and record.check_observed is True
            for record in check_records
        )
        predicted = sum(record.check_observed is True for record in check_records)
        positives = sum(record.check_expected is True for record in check_records)
        metrics = CheckMetrics(
            precision=wilson_interval(tp, predicted),
            recall=wilson_interval(tp, positives),
        )
        checks[check_id] = metrics
        if check_id not in approved_checks:
            blockers.append(f"check_not_approved:{check_id}")
        if metrics.precision.value < 0.9:
            blockers.append(f"precision_below_gate:{check_id}")
        if metrics.recall.value < 0.7:
            blockers.append(f"recall_below_gate:{check_id}")

    subgroup_coverage = {
        subgroup: wilson_interval(
            sum(record.eligible and record.accepted for record in group),
            sum(record.eligible for record in group),
        )
        for subgroup, group in sorted(by_subgroup.items())
    }
    if participants < minimum_participants:
        blockers.append("insufficient_test_participants")
    if exact.sample_size == 0 or exact.value < 0.95:
        blockers.append("exact_count_agreement_below_gate")
    if coverage.sample_size == 0 or coverage.value < 0.8:
        blockers.append("coverage_below_gate")
    if median_phase_error is None or median_phase_error > 0.15:
        blockers.append("tempo_error_above_gate")
    if false_ready.sample_size == 0 or false_ready.value > 0.05:
        blockers.append("false_ready_above_gate")
    if not adversarial_claims_supported or not all(adversarial_claims_supported):
        blockers.append("unsupported_adversarial_report_claim")
    if not checks:
        blockers.append("no_check_evidence")
    for gate in ("device_experience", "upload_service", "reliability"):
        if not operational_gates.get(gate, False):
            blockers.append(f"operational_evidence_missing:{gate}")

    unique_blockers = tuple(dict.fromkeys(blockers))
    return EvaluationResult(
        release_ready=not unique_blockers,
        blockers=unique_blockers,
        participants=participants,
        exact_count_agreement=exact,
        count_mae=count_mae,
        median_phase_error_seconds=median_phase_error,
        coverage=coverage,
        false_ready_rate=false_ready,
        checks=checks,
        subgroup_coverage=subgroup_coverage,
    )
