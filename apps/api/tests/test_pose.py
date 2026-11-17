import hashlib
import json
from pathlib import Path

import pytest

from repwise_api.pose import (
    LANDMARK_NAMES,
    ModelIdentity,
    PoseArtifactError,
    adapt_mediapipe_landmarks,
    build_pose_artifact,
    build_pose_artifact_file,
)


def landmarks(*, hidden: int | None = None) -> list[dict[str, float]]:
    return [
        {
            "x": index / 100,
            "y": index / 50,
            "z": -index / 200,
            "visibility": 0.2 if index == hidden else 0.99,
            "presence": 0.99,
        }
        for index in range(len(LANDMARK_NAMES))
    ]


def model() -> ModelIdentity:
    return ModelIdentity("MediaPipe Pose Landmarker Full", "1.2.3", "a" * 64)


def test_artifact_is_deterministic_and_records_provenance_and_missingness() -> None:
    frames = [
        {"timestamp_seconds": 0.0, "landmarks": landmarks(hidden=29)},
        {"timestamp_seconds": 0.04, "landmarks": landmarks()},
    ]

    first = build_pose_artifact(source_sha256="b" * 64, model=model(), frames=frames)
    second = build_pose_artifact(source_sha256="b" * 64, model=model(), frames=frames)

    assert first == second
    assert first["schema"] == "repwise.pose-artifact.v1"
    assert first["landmark_schema"] == "mediapipe.pose-33.v1"
    assert first["model"] == model().to_dict()
    assert first["summary"] == {
        "frame_count": 2,
        "missing_landmark_count": 1,
        "observed_landmark_count": 65,
    }
    assert first["frames"][0]["landmarks"]["left_heel"] is None
    assert (
        first["artifact_sha256"]
        == "ec08edfb2b94497290c3011c7e9dc399a88155b11591ef3f35a327847b9a36b6"
    )


def test_file_builder_checks_input_and_writes_canonical_artifact(
    tmp_path: Path,
) -> None:
    source = tmp_path / "inference.json"
    destination = tmp_path / "artifact.json"
    source.write_text(
        json.dumps({"frames": [{"timestamp_seconds": 0, "landmarks": landmarks()}]}),
        encoding="utf-8",
    )
    checksum = hashlib.sha256(source.read_bytes()).hexdigest()

    artifact = build_pose_artifact_file(
        source,
        destination,
        source_sha256="b" * 64,
        model=model(),
        expected_input_sha256=checksum,
    )

    assert json.loads(destination.read_text()) == artifact
    with pytest.raises(PoseArtifactError, match="checksum mismatch") as error:
        build_pose_artifact_file(
            source,
            destination,
            source_sha256="b" * 64,
            model=model(),
            expected_input_sha256="c" * 64,
        )
    assert error.value.code == "checksum_mismatch"


@pytest.mark.parametrize(
    ("frames", "code"),
    [
        ([{"timestamp_seconds": -1, "landmarks": landmarks()}], "invalid_timestamps"),
        (
            [
                {"timestamp_seconds": 1, "landmarks": landmarks()},
                {"timestamp_seconds": 1, "landmarks": landmarks()},
            ],
            "invalid_timestamps",
        ),
        ([{"timestamp_seconds": 0, "landmarks": {}}], "invalid_landmarks"),
    ],
)
def test_artifact_rejects_invalid_frames(
    frames: list[dict[str, object]], code: str
) -> None:
    with pytest.raises(PoseArtifactError) as error:
        build_pose_artifact(source_sha256="b" * 64, model=model(), frames=frames)
    assert error.value.code == code


def test_adapter_rejects_wrong_count_and_non_numeric_values() -> None:
    with pytest.raises(PoseArtifactError) as count_error:
        adapt_mediapipe_landmarks([], 0.5)
    assert count_error.value.code == "invalid_landmark_count"

    invalid = landmarks()
    invalid[0]["x"] = True  # type: ignore[assignment]
    with pytest.raises(PoseArtifactError) as value_error:
        adapt_mediapipe_landmarks(invalid, 0.5)
    assert value_error.value.code == "invalid_landmark"


@pytest.mark.parametrize(
    ("kwargs", "code"),
    [
        ({"source_sha256": "bad"}, "invalid_checksum"),
        ({"minimum_visibility": 2.0}, "invalid_visibility_threshold"),
    ],
)
def test_artifact_rejects_invalid_configuration(
    kwargs: dict[str, object], code: str
) -> None:
    arguments = {
        "source_sha256": "b" * 64,
        "model": model(),
        "frames": [],
        **kwargs,
    }
    with pytest.raises(PoseArtifactError) as error:
        build_pose_artifact(**arguments)  # type: ignore[arg-type]
    assert error.value.code == code


def test_model_and_inference_validation(tmp_path: Path) -> None:
    with pytest.raises(PoseArtifactError, match="name and version"):
        ModelIdentity("", "1", "a" * 64)
    with pytest.raises(PoseArtifactError, match="model SHA"):
        ModelIdentity("model", "1", "BAD")

    source = tmp_path / "bad.json"
    source.write_bytes(b"not-json")
    checksum = hashlib.sha256(source.read_bytes()).hexdigest()
    with pytest.raises(PoseArtifactError) as decode_error:
        build_pose_artifact_file(
            source,
            tmp_path / "out",
            source_sha256="b" * 64,
            model=model(),
            expected_input_sha256=checksum,
        )
    assert decode_error.value.code == "invalid_inference"

    source.write_text("{}", encoding="utf-8")
    checksum = hashlib.sha256(source.read_bytes()).hexdigest()
    with pytest.raises(PoseArtifactError) as shape_error:
        build_pose_artifact_file(
            source,
            tmp_path / "out",
            source_sha256="b" * 64,
            model=model(),
            expected_input_sha256=checksum,
        )
    assert shape_error.value.code == "invalid_inference"
