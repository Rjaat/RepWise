import pytest
from pydantic import ValidationError

from repwise_api.settings import Settings


def test_settings_reject_unknown_database_drivers() -> None:
    with pytest.raises(ValidationError, match="psycopg or test-only aiosqlite"):
        Settings(database_url="mysql://localhost/repwise")


def test_settings_accept_test_sqlite_driver() -> None:
    settings = Settings(database_url="sqlite+aiosqlite://")
    assert settings.database_url == "sqlite+aiosqlite://"
