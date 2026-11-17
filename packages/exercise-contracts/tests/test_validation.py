from __future__ import annotations

import copy
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

import pytest

from repwise_exercise_contracts import ContractValidationError, validate_contract

PACKAGE_ROOT = Path(__file__).parents[1]
CONTRACT_PATH = PACKAGE_ROOT / "contracts/bodyweight-squat.side.v1.json"
PUSHUP_PATH = PACKAGE_ROOT / "contracts/push-up.side.v1.json"
PUSHUP_EVALUATION_PATH = PACKAGE_ROOT / "evaluation/push-up.side.v1.held-out.json"
CURL_PATH = PACKAGE_ROOT / "contracts/standing-curl.side.v1.json"
CURL_EVALUATION_PATH = PACKAGE_ROOT / "evaluation/standing-curl.side.v1.held-out.json"


@pytest.fixture
def contract() -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(CONTRACT_PATH.read_text(encoding="utf-8")))


def test_seed_contract_is_valid(contract: dict[str, Any]) -> None:
    validate_contract(contract)


def test_pushup_contract_is_valid_and_keeps_unreviewed_checks_disabled() -> None:
    pushup = cast(dict[str, Any], json.loads(PUSHUP_PATH.read_text(encoding="utf-8")))
    validate_contract(pushup)
    assert pushup["validation"]["coach_review_required"] is True
    assert all(check["enabled"] is False for check in pushup["supported_checks"])
    assert "pain_or_injury_risk" in pushup["unavailable_checks"]


def test_pushup_checks_have_independent_release_evaluation() -> None:
    evaluation = cast(
        dict[str, Any],
        json.loads(PUSHUP_EVALUATION_PATH.read_text(encoding="utf-8")),
    )
    thresholds = evaluation["release_thresholds"]
    assert evaluation["coach_signoff"] is None
    results: dict[str, tuple[float, float]] = {}
    for check_id, evidence in evaluation["checks"].items():
        cases = evidence["cases"]
        true_positive = sum(case["expected"] and case["observed"] for case in cases)
        false_positive = sum(
            not case["expected"] and case["observed"] for case in cases
        )
        false_negative = sum(
            case["expected"] and not case["observed"] for case in cases
        )
        precision = true_positive / (true_positive + false_positive)
        recall = true_positive / (true_positive + false_negative)
        results[check_id] = (precision, recall)

    assert set(results) == {
        "rep_count",
        "phase_timing",
        "visible_depth_consistency",
        "incomplete_lockout",
        "trunk_line_consistency",
    }
    assert results["rep_count"] >= (
        thresholds["precision"],
        thresholds["recall"],
    )
    assert results["visible_depth_consistency"][0] < thresholds["precision"]
    assert results["trunk_line_consistency"][0] < thresholds["precision"]


def test_curl_contract_is_valid_and_keeps_unreviewed_checks_disabled() -> None:
    curl = cast(dict[str, Any], json.loads(CURL_PATH.read_text(encoding="utf-8")))
    validate_contract(curl)
    assert curl["validation"]["coach_review_required"] is True
    assert all(check["enabled"] is False for check in curl["supported_checks"])
    assert "pain_or_injury_risk" in curl["unavailable_checks"]


def test_curl_checks_have_independent_release_evaluation() -> None:
    evaluation = cast(
        dict[str, Any],
        json.loads(CURL_EVALUATION_PATH.read_text(encoding="utf-8")),
    )
    thresholds = evaluation["release_thresholds"]
    assert evaluation["coach_signoff"] is None
    results: dict[str, tuple[float, float]] = {}
    for check_id, evidence in evaluation["checks"].items():
        cases = evidence["cases"]
        true_positive = sum(case["expected"] and case["observed"] for case in cases)
        false_positive = sum(
            not case["expected"] and case["observed"] for case in cases
        )
        false_negative = sum(
            case["expected"] and not case["observed"] for case in cases
        )
        results[check_id] = (
            true_positive / (true_positive + false_positive),
            true_positive / (true_positive + false_negative),
        )

    assert set(results) == {
        "rep_count",
        "phase_timing",
        "visible_range_consistency",
        "incomplete_extension",
        "upper_arm_drift",
    }
    assert results["rep_count"][0] >= thresholds["precision"]
    assert results["rep_count"][1] >= thresholds["recall"]
    assert results["visible_range_consistency"][0] < thresholds["precision"]
    assert results["upper_arm_drift"][0] < thresholds["precision"]


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (
            lambda value: value["required_landmarks"].append("left_wing"),
            "unsupported landmarks",
        ),
        (
            lambda value: value["thresholds"].update({"bad": {"min": 10, "max": 5}}),
            "min must be less than max",
        ),
        (
            lambda value: value["supported_checks"].append(
                {
                    "id": "frontal_knee_tracking",
                    "enabled": False,
                    "validation_status": "candidate",
                }
            ),
            "unsupported for bodyweight_squat/side",
        ),
    ],
)
def test_rejects_invalid_domain_rules(
    contract: dict[str, Any], mutate: Callable[[dict[str, Any]], object], message: str
) -> None:
    invalid = copy.deepcopy(contract)
    mutate(invalid)
    with pytest.raises(ContractValidationError, match=message):
        validate_contract(invalid)
