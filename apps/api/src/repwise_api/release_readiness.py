from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

REQUIRED_EVIDENCE = (
    "coach_signoff_pushup",
    "coach_signoff_curl",
    "participant_evaluation",
    "device_matrix",
    "legal_privacy",
    "database_restore_drill",
    "media_restore_drill",
    "rule_rollback_rehearsal",
    "deployment_rollback_rehearsal",
    "production_security_review",
)


def validate_release_manifest(manifest: Mapping[str, Any]) -> tuple[str, ...]:
    blockers: list[str] = []
    if manifest.get("release_status") != "approved":
        blockers.append("release_status_not_approved")

    evidence = manifest.get("evidence")
    if not isinstance(evidence, Mapping):
        return (*blockers, "evidence_missing")
    for evidence_id in REQUIRED_EVIDENCE:
        item = evidence.get(evidence_id)
        if not isinstance(item, Mapping):
            blockers.append(f"evidence_missing:{evidence_id}")
            continue
        if item.get("status") != "approved":
            blockers.append(f"evidence_not_approved:{evidence_id}")
        reference = item.get("reference")
        if not isinstance(reference, str) or not reference.strip():
            blockers.append(f"evidence_reference_missing:{evidence_id}")

    enabled_checks = manifest.get("enabled_checks")
    if not isinstance(enabled_checks, list) or not enabled_checks:
        blockers.append("enabled_checks_missing")
    else:
        for index, check in enumerate(enabled_checks):
            if not isinstance(check, Mapping):
                blockers.append(f"enabled_check_invalid:{index}")
                continue
            check_id = check.get("check_id", index)
            if check.get("coach_approval") != "approved":
                blockers.append(f"check_coach_approval_missing:{check_id}")
            if check.get("evaluation_gate") != "passed":
                blockers.append(f"check_evaluation_missing:{check_id}")

    devices = manifest.get("supported_devices")
    if not isinstance(devices, list) or not devices:
        blockers.append("supported_devices_missing")
    else:
        for index, device in enumerate(devices):
            if not isinstance(device, Mapping):
                blockers.append(f"supported_device_invalid:{index}")
                continue
            device_id = device.get("device_id", index)
            if device.get("physical_test") != "passed":
                blockers.append(f"physical_device_evidence_missing:{device_id}")
            if not device.get("reference"):
                blockers.append(f"device_reference_missing:{device_id}")
    return tuple(blockers)


def load_and_validate(path: Path) -> tuple[str, ...]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        return ("manifest_must_be_an_object",)
    return validate_release_manifest(payload)


def main(arguments: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Validate signed beta evidence")
    parser.add_argument("manifest", type=Path)
    options = parser.parse_args(arguments)
    blockers = load_and_validate(options.manifest)
    if blockers:
        print("BLOCKED")
        for blocker in blockers:
            print(f"- {blocker}")
        return 1
    print("APPROVED")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
