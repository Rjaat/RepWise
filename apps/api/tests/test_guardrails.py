from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime, timedelta

from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import create_async_engine

from repwise_api.database import Base, create_session_factory
from repwise_api.errors import ApiError
from repwise_api.guardrails import consume_analysis_usage
from repwise_api.main import create_app
from repwise_api.models import BetaQuota, PaymentAttempt, UsageLedger

OWNER = uuid.UUID("10000000-0000-0000-0000-000000000001")


def test_usage_is_idempotent_and_payment_attempts_are_flag_gated() -> None:
    async def exercise() -> None:
        engine = create_async_engine("sqlite+aiosqlite://")
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        factory = create_session_factory(engine)
        analysis_id = uuid.uuid4()
        async with factory() as db:
            first = await consume_analysis_usage(
                db,
                owner_id=OWNER,
                analysis_id=analysis_id,
                event_key="analysis:one",
                monthly_limit_units=2,
                daily_limit_units=2,
                payments_enabled=True,
            )
            second = await consume_analysis_usage(
                db,
                owner_id=OWNER,
                analysis_id=analysis_id,
                event_key="analysis:one",
                monthly_limit_units=2,
                daily_limit_units=2,
                payments_enabled=True,
            )
            await db.commit()

            assert first.id == second.id
            assert await db.scalar(select(func.count(UsageLedger.id))) == 1
            assert await db.scalar(select(func.count(PaymentAttempt.id))) == 1
            quota = await db.get(BetaQuota, OWNER)
            assert quota is not None
            assert quota.used_units == 1
            assert quota.limit_units == 2
        await engine.dispose()

    asyncio.run(exercise())


def test_quota_failure_records_neither_usage_nor_payment() -> None:
    async def exercise() -> None:
        engine = create_async_engine("sqlite+aiosqlite://")
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        factory = create_session_factory(engine)
        async with factory() as db:
            await consume_analysis_usage(
                db,
                owner_id=OWNER,
                analysis_id=uuid.uuid4(),
                event_key="analysis:first",
                monthly_limit_units=1,
                daily_limit_units=5,
                payments_enabled=False,
            )
            await db.commit()
            try:
                await consume_analysis_usage(
                    db,
                    owner_id=OWNER,
                    analysis_id=uuid.uuid4(),
                    event_key="analysis:rejected",
                    monthly_limit_units=1,
                    daily_limit_units=5,
                    payments_enabled=True,
                )
            except ApiError as error:
                assert error.status_code == 429
                assert error.code == "monthly_analysis_limit_reached"
            else:
                raise AssertionError("quota exhaustion must reject usage")
            await db.rollback()

            assert await db.scalar(select(func.count(UsageLedger.id))) == 1
            assert await db.scalar(select(func.count(PaymentAttempt.id))) == 0
        await engine.dispose()

    asyncio.run(exercise())


def test_usage_summary_is_owner_scoped_and_transparent() -> None:
    async def exercise() -> None:
        application = create_app()
        await application.state.database_engine.dispose()
        engine = create_async_engine("sqlite+aiosqlite://")
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        application.state.database_engine = engine
        application.state.session_factory = create_session_factory(engine)

        async with AsyncClient(
            transport=ASGITransport(app=application), base_url="http://test"
        ) as client:
            empty = await client.get(
                "/v1/usage", headers={"Authorization": f"Bearer {OWNER}"}
            )
            unauthenticated = await client.get("/v1/usage")
            async with application.state.session_factory() as db:
                await consume_analysis_usage(
                    db,
                    owner_id=OWNER,
                    analysis_id=uuid.uuid4(),
                    event_key="analysis:summary",
                    monthly_limit_units=3,
                    daily_limit_units=2,
                    payments_enabled=False,
                )
                await db.commit()
            used = await client.get(
                "/v1/usage", headers={"Authorization": f"Bearer {OWNER}"}
            )

        assert empty.json()["used_units"] == 0
        assert empty.json()["limit_units"] == 30
        assert empty.json()["remaining_units"] == 30
        assert empty.json()["daily_limit_units"] == 5
        assert empty.json()["daily_remaining_units"] == 5
        assert empty.json()["payments_enabled"] is False
        assert empty.json()["resets_at"]
        assert empty.json()["daily_resets_at"]
        assert unauthenticated.status_code == 401
        assert used.json()["used_units"] == 1
        assert used.json()["limit_units"] == 3
        assert used.json()["remaining_units"] == 2
        assert used.json()["daily_used_units"] == 1
        assert used.json()["daily_limit_units"] == 5
        assert used.json()["daily_remaining_units"] == 4
        assert used.json()["payments_enabled"] is False
        await engine.dispose()

    asyncio.run(exercise())


def test_daily_burst_limit_and_monthly_cycle_reset() -> None:
    async def exercise() -> None:
        engine = create_async_engine("sqlite+aiosqlite://")
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        factory = create_session_factory(engine)
        first_day = datetime(2026, 11, 17, 10, tzinfo=UTC)
        async with factory() as db:
            await consume_analysis_usage(
                db,
                owner_id=OWNER,
                analysis_id=uuid.uuid4(),
                event_key="analysis:day-one",
                monthly_limit_units=30,
                daily_limit_units=1,
                payments_enabled=False,
                now=first_day,
            )
            await db.commit()
            try:
                await consume_analysis_usage(
                    db,
                    owner_id=OWNER,
                    analysis_id=uuid.uuid4(),
                    event_key="analysis:burst",
                    monthly_limit_units=30,
                    daily_limit_units=1,
                    payments_enabled=False,
                    now=first_day + timedelta(hours=1),
                )
            except ApiError as error:
                assert error.code == "daily_analysis_limit_reached"
            else:
                raise AssertionError("daily burst limit must reject usage")
            await db.rollback()

            quota = await db.get(BetaQuota, OWNER)
            assert quota is not None
            quota.resets_at = first_day - timedelta(seconds=1)
            await db.commit()
            await consume_analysis_usage(
                db,
                owner_id=OWNER,
                analysis_id=uuid.uuid4(),
                event_key="analysis:new-cycle",
                monthly_limit_units=30,
                daily_limit_units=5,
                payments_enabled=False,
                now=first_day + timedelta(days=1),
            )
            await db.commit()
            await db.refresh(quota)
            assert quota.used_units == 1
            assert quota.limit_units == 30
            assert quota.resets_at.replace(tzinfo=UTC) > first_day + timedelta(days=1)
        await engine.dispose()

    asyncio.run(exercise())
