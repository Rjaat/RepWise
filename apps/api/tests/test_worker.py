from typing import Any
from unittest.mock import Mock, patch

import pytest

from repwise_api.media import MediaProbe, PreflightResult
from repwise_api.smoke import main
from repwise_api.worker import celery_app, media_preflight_task, smoke_task


def test_smoke_task_has_deterministic_json_result() -> None:
    celery_app.conf.task_always_eager = True
    celery_app.conf.task_store_eager_result = False

    result = smoke_task.delay()

    assert result.get() == {"status": "ok", "worker": "media"}


@pytest.mark.parametrize(
    ("payload", "raises"),
    [
        ({"status": "ok", "worker": "media"}, False),
        ({"status": "unexpected"}, True),
    ],
)
def test_smoke_entrypoint_validates_and_removes_result(
    payload: dict[str, Any], raises: bool, capsys: pytest.CaptureFixture[str]
) -> None:
    result = Mock()
    result.get.return_value = payload

    with patch("repwise_api.smoke.smoke_task.delay", return_value=result):
        if raises:
            with pytest.raises(RuntimeError, match="Unexpected smoke result"):
                main()
            result.forget.assert_not_called()
        else:
            main()
            result.forget.assert_called_once_with()
            assert "completed" in capsys.readouterr().out

    result.get.assert_called_once_with(timeout=20)


def test_media_task_moves_private_artifacts_and_returns_manifest() -> None:
    storage = Mock()
    probe = MediaProbe("h264", 100, 100, 1, 0, False, False, "1", "1")
    preflight = PreflightResult("a" * 64, "b" * 64, probe, probe, ())
    with (
        patch("repwise_api.worker.MinioObjectStorage", return_value=storage),
        patch("repwise_api.worker.normalize_media", return_value=preflight),
    ):
        result = media_preflight_task("users/1/uploads/2/source", "a" * 64)

    assert result["normalized_object_key"].endswith(".normalized.mp4")
    assert result["manifest_object_key"].endswith(".preflight.json")
    assert result["preflight"]["normalized_sha256"] == "b" * 64
    storage.download.assert_called_once()
    assert storage.upload.call_count == 2
