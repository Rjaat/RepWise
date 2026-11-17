import hashlib
import subprocess
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from repwise_api.inference import (
    PoseInferenceError,
    _extract_frames,
    _load_mediapipe,
    run_pose_inference,
)
from repwise_api.pose import LANDMARK_NAMES


class FakeDetector:
    def __init__(self, results: list[object]) -> None:
        self.results = iter(results)

    def __enter__(self) -> "FakeDetector":
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def detect_for_video(self, _image: object, _timestamp: int) -> object:
        return next(self.results)


def fake_mediapipe(results: list[object]) -> object:
    detector = FakeDetector(results)
    vision = SimpleNamespace(
        PoseLandmarkerOptions=lambda **values: values,
        RunningMode=SimpleNamespace(VIDEO="video"),
        PoseLandmarker=SimpleNamespace(create_from_options=lambda _options: detector),
    )
    return SimpleNamespace(
        tasks=SimpleNamespace(
            BaseOptions=lambda **values: values,
            vision=vision,
        ),
        Image=SimpleNamespace(create_from_file=lambda value: value),
    )


def landmarks(count: int = 33) -> list[object]:
    return [
        SimpleNamespace(x=0.1, y=0.2, z=-0.1, visibility=0.9, presence=0.8)
        for _ in range(count)
    ]


def test_inference_emits_detected_and_missing_frames(tmp_path: Path) -> None:
    model = tmp_path / "model.task"
    model.write_bytes(b"pinned model")
    frames = [tmp_path / "0.png", tmp_path / "1.png"]
    runtime = fake_mediapipe(
        [
            SimpleNamespace(pose_landmarks=[landmarks()]),
            SimpleNamespace(pose_landmarks=[]),
        ]
    )
    destination = tmp_path / "inference.json"
    with (
        patch("repwise_api.inference._load_mediapipe", return_value=runtime),
        patch("repwise_api.inference._extract_frames", return_value=frames),
    ):
        result = run_pose_inference(
            tmp_path / "video.mp4",
            model,
            destination,
            expected_model_sha256=hashlib.sha256(b"pinned model").hexdigest(),
            sample_fps=10,
        )

    assert result["frame_count"] == 2
    assert result["detected_frame_count"] == 1
    assert len(str(result["inference_sha256"])) == 64
    assert '"timestamp_seconds":0.1' in destination.read_text()
    assert destination.read_text().count('"visibility":0.0') == len(LANDMARK_NAMES)


@pytest.mark.parametrize(
    ("model_exists", "checksum", "code"),
    [
        (False, "a" * 64, "model_not_found"),
        (True, "a" * 64, "model_checksum_mismatch"),
    ],
)
def test_inference_rejects_unverified_model(
    tmp_path: Path, model_exists: bool, checksum: str, code: str
) -> None:
    model = tmp_path / "model.task"
    if model_exists:
        model.write_bytes(b"model")
    with pytest.raises(PoseInferenceError) as raised:
        run_pose_inference(
            tmp_path / "video.mp4",
            model,
            tmp_path / "out.json",
            expected_model_sha256=checksum,
            sample_fps=10,
        )
    assert raised.value.code == code


def test_inference_rejects_no_pose_and_bad_landmark_count(tmp_path: Path) -> None:
    model = tmp_path / "model.task"
    model.write_bytes(b"model")
    checksum = hashlib.sha256(b"model").hexdigest()
    for result, code in [
        (SimpleNamespace(pose_landmarks=[]), "no_pose_detected"),
        (
            SimpleNamespace(pose_landmarks=[landmarks(1)]),
            "invalid_landmark_count",
        ),
    ]:
        with (
            patch(
                "repwise_api.inference._load_mediapipe",
                return_value=fake_mediapipe([result]),
            ),
            patch(
                "repwise_api.inference._extract_frames",
                return_value=[tmp_path / "0.png"],
            ),
            pytest.raises(PoseInferenceError) as raised,
        ):
            run_pose_inference(
                tmp_path / "video.mp4",
                model,
                tmp_path / "out.json",
                expected_model_sha256=checksum,
                sample_fps=10,
            )
        assert raised.value.code == code


def test_inference_wraps_runtime_failure(tmp_path: Path) -> None:
    model = tmp_path / "model.task"
    model.write_bytes(b"model")
    runtime = fake_mediapipe([RuntimeError("unreachable")])
    detector = runtime.tasks.vision.PoseLandmarker.create_from_options(None)
    detector.detect_for_video = Mock(side_effect=RuntimeError("runtime"))
    with (
        patch("repwise_api.inference._load_mediapipe", return_value=runtime),
        patch(
            "repwise_api.inference._extract_frames",
            return_value=[tmp_path / "0.png"],
        ),
        pytest.raises(PoseInferenceError) as raised,
    ):
        run_pose_inference(
            tmp_path / "video.mp4",
            model,
            tmp_path / "out.json",
            expected_model_sha256=hashlib.sha256(b"model").hexdigest(),
            sample_fps=10,
        )
    assert raised.value.code == "inference_failed"


def test_frame_extraction_handles_process_and_empty_output(tmp_path: Path) -> None:
    with (
        patch("repwise_api.inference.subprocess.run") as run,
        pytest.raises(PoseInferenceError, match="no inference frames"),
    ):
        _extract_frames(tmp_path / "video", tmp_path / "empty", 10)
    run.assert_called_once()

    for error in [OSError(), subprocess.CalledProcessError(1, ["ffmpeg"])]:
        with (
            patch("repwise_api.inference.subprocess.run", side_effect=error),
            pytest.raises(PoseInferenceError) as raised,
        ):
            _extract_frames(tmp_path / "video", tmp_path / str(id(error)), 10)
        assert raised.value.code == "frame_extraction_failed"


def test_frame_extraction_returns_sorted_pngs(tmp_path: Path) -> None:
    destination = tmp_path / "frames"

    def create_frames(*_args: object, **_kwargs: object) -> None:
        (destination / "00000001.png").write_bytes(b"1")
        (destination / "00000000.png").write_bytes(b"0")

    with patch("repwise_api.inference.subprocess.run", side_effect=create_frames):
        assert [
            item.name for item in _extract_frames(tmp_path / "video", destination, 5)
        ] == [
            "00000000.png",
            "00000001.png",
        ]


def test_runtime_import_error_has_stable_code() -> None:
    with (
        patch("repwise_api.inference.importlib.import_module", side_effect=ImportError),
        pytest.raises(PoseInferenceError) as raised,
    ):
        _load_mediapipe()
    assert raised.value.code == "runtime_unavailable"
