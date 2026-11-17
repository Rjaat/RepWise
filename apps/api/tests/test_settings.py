import pytest
from pydantic import ValidationError

from repwise_api.settings import Settings


def test_settings_reject_unknown_database_drivers() -> None:
    with pytest.raises(ValidationError, match="psycopg or test-only aiosqlite"):
        Settings(database_url="mysql://localhost/repwise")


def test_settings_accept_test_sqlite_driver() -> None:
    settings = Settings(database_url="sqlite+aiosqlite://")
    assert settings.database_url == "sqlite+aiosqlite://"


def test_production_requires_secure_session_configuration() -> None:
    with pytest.raises(ValidationError, match="legacy bearer"):
        Settings(env="production")
    with pytest.raises(ValidationError, match="at least 32"):
        Settings(
            env="production",
            allow_legacy_bearer_identity=False,
            auth_signing_secret="short",
            identity_assertion_secret="short",
        )
    configured = Settings(
        env="production",
        allow_legacy_bearer_identity=False,
        auth_signing_secret="a" * 32,
        identity_assertion_secret="b" * 32,
    )
    assert configured.allow_legacy_bearer_identity is False
