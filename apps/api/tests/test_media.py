from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from repwise_api import media_cli
from repwise_api.media import (
    MediaPreflightError,
    MediaProbe,
    PreflightResult,
    _rate,
    _run,
    frame_timestamps,
    normalize_media,
    probe_media,
    sha256_file,
    validate_probe,
)


def generate(command: list[str]) -> None:
    subprocess.run(command, check=True, capture_output=True)


@pytest.fixture(scope="module")
def media_fixtures(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Path]:
    directory = tmp_path_factory.mktemp("media")
    standard = directory / "standard.mp4"
    rotated = directory / "rotated.mp4"
    vfr = directory / "vfr.mp4"
    corrupt = directory / "corrupt.mp4"
    generate(
        [
            "ffmpeg",
            "-v",
            "error",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "testsrc=size=96x64:rate=12:duration=1",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:duration=1",
            "-shortest",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            str(standard),
        ]
    )
    generate(
        [
            "ffmpeg",
            "-v",
            "error",
            "-y",
            "-i",
            str(standard),
            "-c",
            "copy",
            "-metadata:s:v:0",
            "rotate=90",
            str(rotated),
        ]
    )
    generate(
        [
            "ffmpeg",
            "-v",
            "error",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "testsrc=size=96x64:rate=30:duration=1",
            "-vf",
            "select='not(mod(n,3))+not(mod(n,5))'",
            "-vsync",
            "vfr",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            str(vfr),
        ]
    )
    corrupt.write_bytes(b"not a video")
    return {"rotated": rotated, "vfr": vfr, "corrupt": corrupt}


def test_rotation_audio_removal_and_timestamp_mapping(
    media_fixtures: dict[str, Path], tmp_path: Path
) -> None:
    source = media_fixtures["rotated"]
    result = normalize_media(source, tmp_path / "normalized.mp4", sha256_file(source))

    assert result.source.rotation_degrees == 90
    assert result.source.has_audio is True
    assert result.normalized.rotation_degrees == 0
    assert result.normalized.has_audio is False
    assert (result.normalized.width, result.normalized.height) == (64, 96)
    assert result.timestamps
    assert all(
        abs(item.source_seconds - item.normalized_seconds) < 0.002
        for item in result.timestamps
    )
    assert result.to_dict()["source_sha256"] == sha256_file(source)


def test_vfr_normalization_preserves_nonuniform_presentation_times(
    media_fixtures: dict[str, Path], tmp_path: Path
) -> None:
    source = media_fixtures["vfr"]
    result = normalize_media(
        source, tmp_path / "normalized-vfr.mp4", sha256_file(source)
    )
    deltas = {
        round(current.source_seconds - previous.source_seconds, 3)
        for previous, current in zip(
            result.timestamps, result.timestamps[1:], strict=False
        )
    }

    assert result.source.variable_frame_rate is True
    assert result.normalized.variable_frame_rate is True
    assert len(deltas) > 1
    assert all(
        abs(item.source_seconds - item.normalized_seconds) < 0.002
        for item in result.timestamps
    )


def test_corrupt_media_and_checksum_mismatch_are_distinct(
    media_fixtures: dict[str, Path], tmp_path: Path
) -> None:
    corrupt = media_fixtures["corrupt"]
    with pytest.raises(MediaPreflightError, match="Invalid data") as corrupt_error:
        normalize_media(corrupt, tmp_path / "never.mp4", sha256_file(corrupt))
    assert corrupt_error.value.code == "corrupt_media"

    with pytest.raises(MediaPreflightError, match="checksum") as checksum_error:
        normalize_media(corrupt, tmp_path / "never.mp4", "0" * 64)
    assert checksum_error.value.code == "checksum_mismatch"


@pytest.mark.parametrize(
    ("probe", "code"),
    [
        (
            MediaProbe("rawvideo", 100, 100, 1, 0, False, False, "1", "1"),
            "unsupported_codec",
        ),
        (
            MediaProbe("h264", 8, 100, 1, 0, False, False, "1", "1"),
            "invalid_dimensions",
        ),
        (
            MediaProbe("h264", 100, 100, 181, 0, False, False, "1", "1"),
            "invalid_duration",
        ),
    ],
)
def test_probe_policy_rejects_unsupported_media(probe: MediaProbe, code: str) -> None:
    with pytest.raises(MediaPreflightError) as error:
        validate_probe(probe)
    assert error.value.code == code


def test_invalid_probe_metadata_rates_and_timestamps_are_safe(tmp_path: Path) -> None:
    with pytest.raises(MediaPreflightError, match="frame rate"):
        _rate("0/0")
    with (
        patch("repwise_api.media._run", return_value='{"streams": []}'),
        pytest.raises(MediaPreflightError) as probe_error,
    ):
        probe_media(tmp_path / "missing.mp4")
    assert probe_error.value.code == "invalid_media_metadata"
    with (
        patch("repwise_api.media._run", return_value='{"frames": [{}]}'),
        pytest.raises(MediaPreflightError) as timestamp_error,
    ):
        frame_timestamps(tmp_path / "missing.mp4")
    assert timestamp_error.value.code == "invalid_timestamps"


def test_media_tool_failures_have_stable_categories() -> None:
    with (
        patch("repwise_api.media.subprocess.run", side_effect=FileNotFoundError),
        pytest.raises(MediaPreflightError) as unavailable,
    ):
        _run(["ffprobe"], "probe_failed")
    assert unavailable.value.code == "media_tool_unavailable"

    failure = subprocess.CalledProcessError(1, ["ffmpeg"], stderr="decode failed")
    with (
        patch("repwise_api.media.subprocess.run", side_effect=failure),
        pytest.raises(MediaPreflightError, match="decode failed") as failed,
    ):
        _run(["ffmpeg"], "normalization_failed")
    assert failed.value.code == "normalization_failed"


def test_frame_count_changes_are_rejected(
    media_fixtures: dict[str, Path], tmp_path: Path
) -> None:
    source = media_fixtures["vfr"]
    with (
        patch("repwise_api.media.frame_timestamps", side_effect=[(0.0,), ()]),
        pytest.raises(MediaPreflightError) as error,
    ):
        normalize_media(source, tmp_path / "mismatch.mp4", sha256_file(source))
    assert error.value.code == "timestamp_mapping_failed"


def test_cli_writes_manifest_and_returns_structured_rejection(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    result = PreflightResult(
        source_sha256="a" * 64,
        normalized_sha256="b" * 64,
        source=MediaProbe("h264", 100, 100, 1, 0, False, False, "1", "1"),
        normalized=MediaProbe("h264", 100, 100, 1, 0, False, False, "1", "1"),
        timestamps=(),
    )
    manifest = tmp_path / "manifest.json"
    with (
        patch.object(
            sys,
            "argv",
            [
                "media",
                "in.mp4",
                "out.mp4",
                "--sha256",
                "a",
                "--manifest",
                str(manifest),
            ],
        ),
        patch("repwise_api.media_cli.normalize_media", return_value=result),
    ):
        assert media_cli.main() == 0
    assert json.loads(manifest.read_text())["normalized_sha256"] == "b" * 64

    with (
        patch.object(sys, "argv", ["media", "in.mp4", "out.mp4", "--sha256", "a"]),
        patch("repwise_api.media_cli.normalize_media", return_value=result),
    ):
        assert media_cli.main() == 0
    assert '"normalized_sha256"' in capsys.readouterr().out

    with (
        patch.object(sys, "argv", ["media", "in.mp4", "out.mp4", "--sha256", "a"]),
        patch(
            "repwise_api.media_cli.normalize_media",
            side_effect=MediaPreflightError("corrupt_media", "bad video"),
        ),
    ):
        assert media_cli.main() == 1
