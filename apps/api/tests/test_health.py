import asyncio

from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine

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


def test_health_and_readiness_expose_separate_process_states() -> None:
    async def exercise() -> None:
        application = create_app()
        await application.state.database_engine.dispose()
        application.state.database_engine = create_async_engine("sqlite+aiosqlite://")
        transport = ASGITransport(app=application)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            live = await client.get("/health")
            ready = await client.get(
                "/ready",
                headers={"x-request-id": "dd94cdd8-c86f-47c1-a3a9-52d3e66069be"},
            )

        assert live.status_code == 200
        assert ready.status_code == 200
        assert ready.headers["x-request-id"] == "dd94cdd8-c86f-47c1-a3a9-52d3e66069be"
        await application.state.database_engine.dispose()

    asyncio.run(exercise())


def test_readiness_returns_503_when_database_is_unavailable() -> None:
    async def exercise() -> None:
        application = create_app()
        await application.state.database_engine.dispose()
        application.state.database_engine = create_async_engine(
            "sqlite+aiosqlite:////missing/repwise/database.sqlite"
        )
        transport = ASGITransport(app=application)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/ready", headers={"x-request-id": "invalid"})

        assert response.status_code == 503
        assert response.json()["status"] == "unavailable"
        assert response.headers["x-request-id"] != "invalid"
        await application.state.database_engine.dispose()

    asyncio.run(exercise())
