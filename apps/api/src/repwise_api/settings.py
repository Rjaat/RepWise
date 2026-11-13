from functools import lru_cache
from typing import Literal

from pydantic import field_validator
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

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value: str) -> str:
        if not value.startswith(("postgresql+psycopg://", "sqlite+aiosqlite://")):
            raise ValueError("database_url must use psycopg or test-only aiosqlite")
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
