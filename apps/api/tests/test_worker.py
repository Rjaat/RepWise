from typing import Any
from unittest.mock import Mock, patch

import pytest

from repwise_api.smoke import main
from repwise_api.worker import celery_app, smoke_task


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
