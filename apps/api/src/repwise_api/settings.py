from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Validated process configuration loaded from REPWISE_ variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="REPWISE_",
        extra="ignore",
    )

    env: Literal["development", "test", "staging", "production"] = "development"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    database_url: str = "postgresql+psycopg://repwise:repwise@127.0.0.1:55432/repwise"
    redis_url: str = "redis://127.0.0.1:56379/0"
    media_endpoint: str = "http://127.0.0.1:59000"
    media_bucket: str = "repwise-private"
    media_access_key: str = "repwise-local"
    media_secret_key: str = "repwise-local-only"
    web_origin: str = "http://127.0.0.1:5173"
    auth_issuer: str = "repwise"
    auth_audience: str = "repwise-api"
    auth_signing_secret: str = "repwise-development-signing-secret-change-me"
    identity_assertion_secret: str = "repwise-development-identity-secret-change-me"
    access_token_ttl_seconds: int = 900
    refresh_token_ttl_seconds: int = 30 * 24 * 60 * 60
    allow_legacy_bearer_identity: bool = True
    beta_analysis_quota: int = Field(default=20, gt=0)
    payments_enabled: bool = False

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value: str) -> str:
        if not value.startswith(("postgresql+psycopg://", "sqlite+aiosqlite://")):
            raise ValueError("database_url must use psycopg or test-only aiosqlite")
        return value

    @model_validator(mode="after")
    def validate_production_auth(self) -> "Settings":
        if self.env == "production":
            if self.allow_legacy_bearer_identity:
                raise ValueError(
                    "legacy bearer identity must be disabled in production"
                )
            if (
                min(len(self.auth_signing_secret), len(self.identity_assertion_secret))
                < 32
            ):
                raise ValueError(
                    "production authentication secrets must be at least 32 characters"
                )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
