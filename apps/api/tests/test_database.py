import asyncio

from sqlalchemy.ext.asyncio import create_async_engine

from repwise_api.database import (
    create_session_factory,
    database_ready,
    session_scope,
)


def test_session_scope_and_readiness_use_async_database_boundary() -> None:
    async def exercise() -> None:
        engine = create_async_engine("sqlite+aiosqlite://")
        assert await database_ready(engine) is True
        factory = create_session_factory(engine)
        sessions = [session async for session in session_scope(factory)]
        assert len(sessions) == 1
        await engine.dispose()

    asyncio.run(exercise())
