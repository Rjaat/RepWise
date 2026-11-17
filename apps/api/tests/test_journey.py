import hashlib
from pathlib import Path
from unittest.mock import Mock

import pytest

from repwise_api.journey import _inference_payload, _sha256, _task_result


def test_fixture_payload_is_deterministic_and_has_one_motion_cycle() -> None:
    first = _inference_payload()
    second = _inference_payload()
    assert first == second
    assert len(first["frames"]) == 9
    assert len(first["frames"][0]["landmarks"]) == 33
    assert first["frames"][0]["landmarks"][27] != first["frames"][4]["landmarks"][27]


def test_sha256_reads_fixture_bytes(tmp_path: Path) -> None:
    fixture = tmp_path / "fixture"
    fixture.write_bytes(b"repwise")
    assert _sha256(fixture) == hashlib.sha256(b"repwise").hexdigest()


def test_task_result_returns_objects_and_always_forgets() -> None:
    task = Mock()
    result = task.delay.return_value
    result.get.return_value = {"status": "ok"}
    assert _task_result(task, "value") == {"status": "ok"}
    task.delay.assert_called_once_with("value")
    result.get.assert_called_once_with(timeout=60)
    result.forget.assert_called_once_with()


def test_task_result_rejects_non_object_and_forgets() -> None:
    task = Mock()
    result = task.delay.return_value
    result.get.return_value = []
    with pytest.raises(RuntimeError, match="non-object"):
        _task_result(task)
    result.forget.assert_called_once_with()
