import asyncio

from repwise_api.main import create_app, health
from repwise_api.settings import Settings, get_settings


def test_health_reports_process_readiness() -> None:
    response = asyncio.run(health(Settings(env="test")))

    assert response.model_dump() == {
        "status": "ok",
        "service": "repwise-api",
        "environment": "test",
    }


def test_openapi_describes_health_contract() -> None:
    schema = create_app().openapi()

    assert schema["info"] == {
        "title": "RepWise API",
        "description": "Evidence-linked exercise analysis API",
        "version": "0.1.0",
    }
    assert "/health" in schema["paths"]


def test_settings_have_safe_development_defaults() -> None:
    get_settings.cache_clear()

    settings = get_settings()

    assert settings.env == "development"
    assert settings.log_level == "INFO"
