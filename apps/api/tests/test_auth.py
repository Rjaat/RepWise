from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine

from repwise_api.auth import create_identity_assertion, verify_identity_assertion
from repwise_api.database import Base, create_session_factory
from repwise_api.errors import ApiError
from repwise_api.main import create_app
from repwise_api.models import AuthSession, UserAccount, UserRole
from repwise_api.settings import Settings


async def auth_app():
    application = create_app()
    await application.state.database_engine.dispose()
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    application.state.database_engine = engine
    application.state.session_factory = create_session_factory(engine)
    application.state.settings = Settings(allow_legacy_bearer_identity=False)
    return application, engine


async def exchange(client: AsyncClient, settings: Settings):
    assertion = create_identity_assertion(
        "idp|one", "athlete@example.com", True, settings
    )
    return await client.post(
        "/v1/auth/exchange", json={"identity_assertion": assertion}
    )


def test_verified_exchange_rotation_and_revocation() -> None:
    async def exercise() -> None:
        application, engine = await auth_app()
        settings = application.state.settings
        async with AsyncClient(
            transport=ASGITransport(app=application), base_url="http://test"
        ) as client:
            signed_in = await exchange(client, settings)
            first_access = signed_in.json()["access_token"]
            first_refresh = client.cookies["repwise_refresh"]
            refreshed = await client.post("/v1/auth/refresh")
            second_access = refreshed.json()["access_token"]
            second_refresh = client.cookies["repwise_refresh"]
            client.cookies.set("repwise_refresh", first_refresh, path="/v1/auth")
            replay = await client.post("/v1/auth/refresh")
            old_access = await client.post(
                "/v1/auth/logout", headers={"Authorization": f"Bearer {first_access}"}
            )
            logout = await client.post(
                "/v1/auth/logout", headers={"Authorization": f"Bearer {second_access}"}
            )
            revoked_access = await client.post(
                "/v1/auth/logout", headers={"Authorization": f"Bearer {second_access}"}
            )

        assert signed_in.status_code == 200
        assert "httponly" in signed_in.headers["set-cookie"].lower()
        assert first_refresh != second_refresh
        assert replay.status_code == 401
        assert old_access.status_code == 401
        assert logout.status_code == 204
        assert revoked_access.status_code == 401
        async with application.state.session_factory() as db:
            sessions = (await db.scalars(select(AuthSession))).all()
            assert len(sessions) == 2
            assert all(item.revoked_at is not None for item in sessions)
        await engine.dispose()

    asyncio.run(exercise())


def test_identity_verification_and_role_authorization() -> None:
    async def exercise() -> None:
        application, engine = await auth_app()
        settings = application.state.settings
        async with AsyncClient(
            transport=ASGITransport(app=application), base_url="http://test"
        ) as client:
            assertion = create_identity_assertion(
                "idp|unverified", "pending@example.com", False, settings
            )
            unverified = await client.post(
                "/v1/auth/exchange", json={"identity_assertion": assertion}
            )
            signed_in = await exchange(client, settings)
            user_access = signed_in.json()["access_token"]
            forbidden = await client.get(
                "/v1/admin/auth-status",
                headers={"Authorization": f"Bearer {user_access}"},
            )
            async with application.state.session_factory() as db:
                user = await db.scalar(
                    select(UserAccount).where(UserAccount.external_subject == "idp|one")
                )
                assert user is not None
                user.role = UserRole.ADMIN
                await db.commit()
            signed_in_admin = await exchange(client, settings)
            admin_access = signed_in_admin.json()["access_token"]
            allowed = await client.get(
                "/v1/admin/auth-status",
                headers={"Authorization": f"Bearer {admin_access}"},
            )
            async with application.state.session_factory() as db:
                user = await db.scalar(
                    select(UserAccount).where(UserAccount.external_subject == "idp|one")
                )
                assert user is not None
                user.disabled_at = datetime.now(UTC)
                await db.commit()
            disabled = await client.get(
                "/v1/admin/auth-status",
                headers={"Authorization": f"Bearer {admin_access}"},
            )

        assert unverified.status_code == 403
        assert forbidden.status_code == 403
        assert allowed.status_code == 200
        assert allowed.json()["role"] == "admin"
        assert disabled.status_code == 403
        await engine.dispose()

    asyncio.run(exercise())


def test_logout_all_revokes_every_session_and_invalid_tokens_fail() -> None:
    async def exercise() -> None:
        application, engine = await auth_app()
        settings = application.state.settings
        async with AsyncClient(
            transport=ASGITransport(app=application), base_url="http://test"
        ) as client:
            first = await exchange(client, settings)
            second = await exchange(client, settings)
            first_access = first.json()["access_token"]
            second_access = second.json()["access_token"]
            invalid = await client.get(
                "/v1/admin/auth-status", headers={"Authorization": "Bearer broken"}
            )
            logout_all = await client.post(
                "/v1/auth/logout-all",
                headers={"Authorization": f"Bearer {second_access}"},
            )
            first_revoked = await client.post(
                "/v1/auth/logout-all",
                headers={"Authorization": f"Bearer {first_access}"},
            )

        assert invalid.status_code == 401
        assert logout_all.status_code == 204
        assert first_revoked.status_code == 401
        await engine.dispose()

    asyncio.run(exercise())


def test_identity_assertions_reject_tampering_expiry_and_wrong_claims() -> None:
    settings = Settings(allow_legacy_bearer_identity=False)
    valid = create_identity_assertion("idp|one", "athlete@example.com", True, settings)
    with pytest.raises(ApiError):
        verify_identity_assertion(valid + "tampered", settings)
    expired = create_identity_assertion(
        "idp|one", "athlete@example.com", True, settings, ttl_seconds=-1
    )
    with pytest.raises(ApiError):
        verify_identity_assertion(expired, settings)
    missing_subject = create_identity_assertion(
        "", "athlete@example.com", True, settings
    )
    with pytest.raises(ApiError):
        verify_identity_assertion(missing_subject, settings)
