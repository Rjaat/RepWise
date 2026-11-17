from __future__ import annotations

import hashlib
import json
import subprocess
from dataclasses import asdict, dataclass
from fractions import Fraction
from pathlib import Path
from typing import Any

MAX_DURATION_SECONDS = 180.0
SUPPORTED_VIDEO_CODECS = frozenset({"h264", "hevc", "vp8", "vp9", "av1", "mpeg4"})


class MediaPreflightError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


@dataclass(frozen=True)
class MediaProbe:
    codec: str
    width: int
    height: int
    duration_seconds: float
    rotation_degrees: int
    has_audio: bool
    variable_frame_rate: bool
    average_frame_rate: str
    nominal_frame_rate: str


@dataclass(frozen=True)
class TimestampMapping:
    frame_index: int
    source_seconds: float
    normalized_seconds: float


@dataclass(frozen=True)
class PreflightResult:
    source_sha256: str
    normalized_sha256: str
    source: MediaProbe
    normalized: MediaProbe
    timestamps: tuple[TimestampMapping, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _run(command: list[str], failure_code: str) -> str:
    try:
        completed = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
            timeout=MAX_DURATION_SECONDS,
        )
    except FileNotFoundError as error:
        raise MediaPreflightError(
            "media_tool_unavailable",
            f"Required media tool is unavailable: {command[0]}",
        ) from error
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
        detail = getattr(error, "stderr", "") or "media command failed"
        raise MediaPreflightError(failure_code, detail.strip()) from error
    return completed.stdout


def _rate(value: str) -> Fraction:
    try:
        return Fraction(value)
    except (ValueError, ZeroDivisionError) as error:
        raise MediaPreflightError(
            "invalid_media_metadata", "Invalid frame rate metadata."
        ) from error


def probe_media(path: Path) -> MediaProbe:
    output = _run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_streams",
            "-show_format",
            "-of",
            "json",
            str(path),
        ],
        "corrupt_media",
    )
    try:
        payload = json.loads(output)
        streams = payload["streams"]
        video = next(
            stream for stream in streams if stream.get("codec_type") == "video"
        )
        duration = float(video.get("duration") or payload["format"]["duration"])
        average_rate = str(video["avg_frame_rate"])
        nominal_rate = str(video["r_frame_rate"])
        rotation = next(
            (
                int(item["rotation"])
                for item in video.get("side_data_list", [])
                if "rotation" in item
            ),
            int(video.get("tags", {}).get("rotate", 0)),
        )
        result = MediaProbe(
            codec=str(video["codec_name"]),
            width=int(video["width"]),
            height=int(video["height"]),
            duration_seconds=duration,
            rotation_degrees=rotation % 360,
            has_audio=any(stream.get("codec_type") == "audio" for stream in streams),
            variable_frame_rate=_rate(average_rate) != _rate(nominal_rate),
            average_frame_rate=average_rate,
            nominal_frame_rate=nominal_rate,
        )
    except (KeyError, StopIteration, TypeError, ValueError) as error:
        raise MediaPreflightError(
            "invalid_media_metadata", "Video metadata is incomplete or invalid."
        ) from error
    validate_probe(result)
    return result


def validate_probe(probe: MediaProbe) -> None:
    if probe.codec not in SUPPORTED_VIDEO_CODECS:
        raise MediaPreflightError(
            "unsupported_codec", f"Unsupported video codec: {probe.codec}"
        )
    if probe.width < 16 or probe.height < 16:
        raise MediaPreflightError(
            "invalid_dimensions", "Video dimensions are too small."
        )
    if not 0 < probe.duration_seconds <= MAX_DURATION_SECONDS:
        raise MediaPreflightError(
            "invalid_duration", "Video duration must be between 0 and 180 seconds."
        )


def frame_timestamps(path: Path) -> tuple[float, ...]:
    output = _run(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "frame=best_effort_timestamp_time",
            "-of",
            "json",
            str(path),
        ],
        "timestamp_decode_failed",
    )
    try:
        return tuple(
            float(frame["best_effort_timestamp_time"])
            for frame in json.loads(output)["frames"]
        )
    except (KeyError, TypeError, ValueError) as error:
        raise MediaPreflightError(
            "invalid_timestamps", "Video frame timestamps are unavailable."
        ) from error


def normalize_media(
    source: Path, destination: Path, expected_sha256: str
) -> PreflightResult:
    actual_sha256 = sha256_file(source)
    if actual_sha256 != expected_sha256:
        raise MediaPreflightError(
            "checksum_mismatch", "Source checksum does not match the completed upload."
        )
    source_probe = probe_media(source)
    destination.parent.mkdir(parents=True, exist_ok=True)
    _run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-y",
            "-i",
            str(source),
            "-map",
            "0:v:0",
            "-an",
            "-map_metadata",
            "-1",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "18",
            "-pix_fmt",
            "yuv420p",
            "-vsync",
            "0",
            "-movflags",
            "+faststart",
            str(destination),
        ],
        "normalization_failed",
    )
    normalized_probe = probe_media(destination)
    source_timestamps = frame_timestamps(source)
    normalized_timestamps = frame_timestamps(destination)
    if not source_timestamps or len(source_timestamps) != len(normalized_timestamps):
        raise MediaPreflightError(
            "timestamp_mapping_failed", "Normalization did not preserve video frames."
        )
    timestamps = tuple(
        TimestampMapping(index, source_time, normalized_time)
        for index, (source_time, normalized_time) in enumerate(
            zip(source_timestamps, normalized_timestamps, strict=True)
        )
    )
    return PreflightResult(
        source_sha256=actual_sha256,
        normalized_sha256=sha256_file(destination),
        source=source_probe,
        normalized=normalized_probe,
        timestamps=timestamps,
    )
