import pytest
from pydantic import ValidationError

from repwise_api.reports import EvidenceLink, EvidenceReport, ReportMetric, ReportRep


def metric(**overrides: object) -> ReportMetric:
    values = {
        "id": "tempo",
        "label": "Lowering time",
        "unit": "seconds",
        "state": "assessed",
        "value": 1.2,
        **overrides,
    }
    return ReportMetric.model_validate(values)


def report() -> EvidenceReport:
    return EvidenceReport(
        schema_version="repwise.evidence-report.v1",
        analysis_id="analysis-1",
        exercise="Bodyweight squat",
        variant="Bodyweight",
        view="Side",
        source_sha256="a" * 64,
        pose_artifact_sha256="b" * 64,
        segmentation_artifact_sha256="c" * 64,
        reps=(
            ReportRep(
                index=1,
                complete=True,
                evidence=EvidenceLink(start_seconds=2.5, end_seconds=4.1),
                metrics=(metric(),),
            ),
        ),
    )


def test_report_is_immutable_and_has_deterministic_checksum() -> None:
    first = report()
    second = report()
    assert first.checksum() == second.checksum()
    assert len(first.checksum()) == 64
    with pytest.raises(ValidationError):
        first.exercise = "Changed"  # type: ignore[misc]


@pytest.mark.parametrize(
    "values",
    [
        {"state": "assessed", "value": None},
        {"state": "not_assessable", "value": 0, "reason": "Hip hidden"},
        {"state": "uncertain", "value": None, "reason": None},
    ],
)
def test_metric_states_never_encode_missing_values_as_zero(
    values: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        metric(**values)


def test_unavailable_metric_requires_reason_and_serializes_as_null() -> None:
    unavailable = metric(state="not_assessable", value=None, reason="Hip was hidden")
    assert unavailable.value is None
    assert unavailable.reason == "Hip was hidden"


def test_rejects_reversed_evidence_and_unknown_fields() -> None:
    with pytest.raises(ValidationError, match="Evidence end"):
        EvidenceLink(start_seconds=2, end_seconds=1)
    with pytest.raises(ValidationError):
        ReportMetric(
            id="tempo",
            label="Tempo",
            unit="seconds",
            state="assessed",
            value=1,
            unknown=True,  # type: ignore[call-arg]
        )
