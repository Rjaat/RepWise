from __future__ import annotations

import json
from pathlib import Path

import pytest

from repwise_api.release_readiness import (
    REQUIRED_EVIDENCE,
    load_and_validate,
    main,
    validate_release_manifest,
)

REPOSITORY_ROOT = Path(__file__).parents[3]
MANIFEST = REPOSITORY_ROOT / "docs/releases/validated-beta-evidence.json"


def approved_manifest() -> dict[str, object]:
    return {
        "release_status": "approved",
        "evidence": {
            evidence_id: {"status": "approved", "reference": f"ref:{evidence_id}"}
            for evidence_id in REQUIRED_EVIDENCE
        },
        "enabled_checks": [
            {
                "check_id": "rep_count",
                "coach_approval": "approved",
                "evaluation_gate": "passed",
            }
        ],
        "supported_devices": [
            {
                "device_id": "device-browser-version",
                "physical_test": "passed",
                "reference": "ref:device-run",
            }
        ],
    }


def test_complete_signed_manifest_is_approved(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    manifest = approved_manifest()
    path = tmp_path / "approved.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")

    assert validate_release_manifest(manifest) == ()
    assert load_and_validate(path) == ()
    assert main([str(path)]) == 0
    assert "APPROVED" in capsys.readouterr().out


def test_checked_in_manifest_truthfully_blocks_release(
    capsys: pytest.CaptureFixture[str],
) -> None:
    blockers = load_and_validate(MANIFEST)

    assert "release_status_not_approved" in blockers
    assert "evidence_not_approved:participant_evaluation" in blockers
    assert "check_coach_approval_missing:pushup.rep_count" in blockers
    assert "physical_device_evidence_missing:pending-physical-device-matrix" in blockers
    assert main([str(MANIFEST)]) == 1
    output = capsys.readouterr().out
    assert output.startswith("BLOCKED")
    assert "participant_evaluation" in output


def test_missing_and_malformed_evidence_fails_closed(tmp_path: Path) -> None:
    assert validate_release_manifest({}) == (
        "release_status_not_approved",
        "evidence_missing",
    )
    malformed = {
        "release_status": "approved",
        "evidence": {"coach_signoff_pushup": {"status": "approved", "reference": ""}},
        "enabled_checks": ["bad"],
        "supported_devices": ["bad"],
    }
    blockers = validate_release_manifest(malformed)
    assert "evidence_reference_missing:coach_signoff_pushup" in blockers
    assert "evidence_missing:coach_signoff_curl" in blockers
    assert "enabled_check_invalid:0" in blockers
    assert "supported_device_invalid:0" in blockers

    path = tmp_path / "array.json"
    path.write_text("[]", encoding="utf-8")
    assert load_and_validate(path) == ("manifest_must_be_an_object",)

    no_scope = approved_manifest()
    no_scope["enabled_checks"] = []
    no_scope["supported_devices"] = []
    assert validate_release_manifest(no_scope) == (
        "enabled_checks_missing",
        "supported_devices_missing",
    )


def test_each_check_and_device_requires_signed_evidence() -> None:
    manifest = approved_manifest()
    manifest["enabled_checks"] = [
        {"check_id": "tempo", "coach_approval": "pending", "evaluation_gate": "pending"}
    ]
    manifest["supported_devices"] = [
        {"device_id": "phone", "physical_test": "pending", "reference": ""}
    ]

    blockers = validate_release_manifest(manifest)
    assert blockers == (
        "check_coach_approval_missing:tempo",
        "check_evaluation_missing:tempo",
        "physical_device_evidence_missing:phone",
        "device_reference_missing:phone",
    )
