from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, TypeGuard

MEDIAPIPE_POSE_33 = frozenset(
    {
        "nose",
        "left_eye_inner",
        "left_eye",
        "left_eye_outer",
        "right_eye_inner",
        "right_eye",
        "right_eye_outer",
        "left_ear",
        "right_ear",
        "mouth_left",
        "mouth_right",
        "left_shoulder",
        "right_shoulder",
        "left_elbow",
        "right_elbow",
        "left_wrist",
        "right_wrist",
        "left_pinky",
        "right_pinky",
        "left_index",
        "right_index",
        "left_thumb",
        "right_thumb",
        "left_hip",
        "right_hip",
        "left_knee",
        "right_knee",
        "left_ankle",
        "right_ankle",
        "left_heel",
        "right_heel",
        "left_foot_index",
        "right_foot_index",
    }
)
VIEW_CHECKS = {
    ("bodyweight_squat", "side"): frozenset(
        {
            "rep_count",
            "phase_timing",
            "visible_depth_consistency",
            "apparent_knee_angle_excursion",
            "incomplete_return",
        }
    )
}
REQUIRED_FIELDS = frozenset(
    {
        "schema_version",
        "contract_id",
        "contract_version",
        "exercise",
        "variant",
        "view",
        "pose_schema",
        "required_landmarks",
        "view_constraints",
        "minimum_observation",
        "phase_states",
        "thresholds",
        "supported_checks",
        "unavailable_checks",
        "explanation_templates",
        "validation",
    }
)


@dataclass(frozen=True)
class ContractValidationError(ValueError):
    errors: tuple[str, ...]

    def __str__(self) -> str:
        return "\n".join(self.errors)


def _is_number(value: object) -> TypeGuard[int | float]:
    return isinstance(value, int | float) and not isinstance(value, bool)


def validate_contract(contract: Mapping[str, Any]) -> None:
    errors: list[str] = []
    missing = sorted(REQUIRED_FIELDS - contract.keys())
    if missing:
        errors.append(f"missing required fields: {', '.join(missing)}")
    if contract.get("schema_version") != "1.0.0":
        errors.append("schema_version must be 1.0.0")
    version = contract.get("contract_version")
    if not isinstance(version, int) or isinstance(version, bool) or version < 1:
        errors.append("contract_version must be a positive integer")
    if contract.get("pose_schema") != "mediapipe_pose_33@1":
        errors.append("pose_schema must be mediapipe_pose_33@1")

    landmarks = contract.get("required_landmarks")
    if not isinstance(landmarks, list) or not landmarks:
        errors.append("required_landmarks must be a non-empty list")
    else:
        unknown = sorted(set(landmarks) - MEDIAPIPE_POSE_33)
        if unknown:
            errors.append(f"unsupported landmarks: {', '.join(unknown)}")

    thresholds = contract.get("thresholds")
    if not isinstance(thresholds, Mapping) or not thresholds:
        errors.append("thresholds must be a non-empty object")
    else:
        for name, threshold in thresholds.items():
            if not isinstance(threshold, Mapping):
                errors.append(f"thresholds.{name} must be an object")
                continue
            minimum, maximum = threshold.get("min"), threshold.get("max")
            if not _is_number(minimum) or not _is_number(maximum):
                errors.append(f"thresholds.{name} min and max must be numbers")
            elif minimum >= maximum:
                errors.append(f"thresholds.{name} min must be less than max")

    observation = contract.get("minimum_observation")
    if isinstance(observation, Mapping):
        for name in ("landmark_visibility", "required_landmark_coverage"):
            value = observation.get(name)
            if not _is_number(value) or not 0 <= value <= 1:
                errors.append(f"minimum_observation.{name} must be between 0 and 1")
    else:
        errors.append("minimum_observation must be an object")

    checks = contract.get("supported_checks")
    check_ids: list[str] = []
    if not isinstance(checks, list) or not checks:
        errors.append("supported_checks must be a non-empty list")
    else:
        for index, check in enumerate(checks):
            if not isinstance(check, Mapping) or not isinstance(check.get("id"), str):
                errors.append(f"supported_checks[{index}] must have a string id")
                continue
            check_id = check["id"]
            check_ids.append(check_id)
            status = check.get("validation_status")
            if status not in {"candidate", "approved"}:
                errors.append(f"supported_checks[{index}].validation_status is invalid")
            if check.get("enabled") is True and status != "approved":
                errors.append(f"candidate check {check_id} cannot be enabled")

    exercise = contract.get("exercise")
    view = contract.get("view")
    exercise_view = (
        exercise if isinstance(exercise, str) else "",
        view if isinstance(view, str) else "",
    )
    unsupported = sorted(set(check_ids) - VIEW_CHECKS.get(exercise_view, frozenset()))
    if unsupported:
        errors.append(
            f"checks unsupported for {exercise_view[0]}/{exercise_view[1]}: "
            + ", ".join(unsupported)
        )
    if len(check_ids) != len(set(check_ids)):
        errors.append("supported check ids must be unique")
    unavailable = contract.get("unavailable_checks")
    unavailable_ids = (
        {item for item in unavailable if isinstance(item, str)}
        if isinstance(unavailable, list)
        else set()
    )
    overlap = sorted(set(check_ids) & unavailable_ids)
    if overlap:
        errors.append(
            f"checks cannot be both supported and unavailable: {', '.join(overlap)}"
        )
    if errors:
        raise ContractValidationError(tuple(errors))
