from __future__ import annotations

import copy
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

import pytest

from repwise_exercise_contracts import ContractValidationError, validate_contract

CONTRACT_PATH = Path(__file__).parents[1] / "contracts/bodyweight-squat.side.v1.json"


@pytest.fixture
def contract() -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(CONTRACT_PATH.read_text(encoding="utf-8")))


def test_seed_contract_is_valid(contract: dict[str, Any]) -> None:
    validate_contract(contract)


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
