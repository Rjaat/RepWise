from __future__ import annotations

import asyncio
import uuid

from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import create_async_engine

from repwise_api.auth import issue_access_token, new_session
from repwise_api.database import Base, create_session_factory
from repwise_api.main import create_app
from repwise_api.models import (
    AnalysisJob,
    AuditEvent,
    MediaUpload,
    ReleaseApproval,
    ReleasePromotion,
    UploadStatus,
    UserAccount,
    UserRole,
)
from repwise_api.release_controls import in_canary_cohort
from repwise_api.settings import Settings


async def release_app():
    application = create_app()
    await application.state.database_engine.dispose()
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    application.state.database_engine = engine
    application.state.session_factory = create_session_factory(engine)
    application.state.settings = Settings(allow_legacy_bearer_identity=False)
    tokens: dict[str, str] = {}
    async with application.state.session_factory() as db:
        users: dict[str, UserAccount] = {}
        for name, role in {"admin": UserRole.ADMIN, "user": UserRole.USER}.items():
            user = UserAccount(
                external_subject=f"idp|release-{name}",
                email=f"release-{name}@example.com",
                email_verified=True,
                role=role,
            )
            db.add(user)
            await db.flush()
            session, _ = new_session(user.id, application.state.settings)
            db.add(session)
            await db.flush()
            users[name] = user
            tokens[name] = issue_access_token(user, session, application.state.settings)
        upload = MediaUpload(
            owner_id=users["user"].id,
            idempotency_key="release-history",
            object_key="users/release/history/source",
            filename="squat.mp4",
            content_type="video/mp4",
            declared_size=10,
            expected_sha256="a" * 64,
            status=UploadStatus.COMPLETED,
        )
        db.add(upload)
        await db.flush()
        historical = AnalysisJob(
            upload_id=upload.id,
            owner_id=users["user"].id,
            status="completed",
            rule_version="squat.side.historical",
        )
        db.add(historical)
        approvals: dict[str, ReleaseApproval] = {}
        for version in ("squat.side.v1", "squat.side.v2"):
            approval = ReleaseApproval(
                rule_version=version,
                adjudication_id=uuid.uuid4(),
                approver_id=users["admin"].id,
                decision="approved",
            )
            db.add(approval)
            await db.flush()
            approvals[version] = approval
        await db.commit()
    return application, engine, tokens, historical.id, approvals


def bearer(tokens: dict[str, str], name: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {tokens[name]}"}


def test_approval_gated_promotion_disable_and_rollback_preserve_history() -> None:
    async def exercise() -> None:
        application, engine, tokens, historical_id, approvals = await release_app()
        headers = bearer(tokens, "admin")
        async with AsyncClient(
            transport=ASGITransport(app=application), base_url="http://test"
        ) as client:
            forbidden = await client.post(
                "/v1/admin/release-controls",
                headers=bearer(tokens, "user"),
                json={"check_id": "squat.depth", "cohort_percent": 0},
            )
            configured = await client.post(
                "/v1/admin/release-controls",
                headers=headers,
                json={"check_id": "squat.depth", "cohort_percent": 0},
            )
            mismatch = await client.post(
                "/v1/admin/release-controls/squat.depth/promote",
                headers=headers,
                json={
                    "rule_version": "squat.side.v2",
                    "approval_id": str(approvals["squat.side.v1"].id),
                    "cohort_percent": 10,
                },
            )
            first = await client.post(
                "/v1/admin/release-controls/squat.depth/promote",
                headers=headers,
                json={
                    "rule_version": "squat.side.v1",
                    "approval_id": str(approvals["squat.side.v1"].id),
                    "cohort_percent": 10,
                },
            )
            second = await client.post(
                "/v1/admin/release-controls/squat.depth/promote",
                headers=headers,
                json={
                    "rule_version": "squat.side.v2",
                    "approval_id": str(approvals["squat.side.v2"].id),
                    "cohort_percent": 25,
                },
            )
            disabled = await client.post(
                "/v1/admin/release-controls/squat.depth/disable", headers=headers
            )
            rolled_back = await client.post(
                "/v1/admin/release-controls/squat.depth/rollback", headers=headers
            )

        assert forbidden.status_code == 403
        assert configured.json()["enabled"] is False
        assert mismatch.status_code == 409
        assert first.json()["active_version"] == "squat.side.v1"
        assert second.json()["active_version"] == "squat.side.v2"
        assert second.json()["last_known_good_version"] == "squat.side.v1"
        assert disabled.json()["enabled"] is False
        assert rolled_back.json()["active_version"] == "squat.side.v1"
        assert rolled_back.json()["enabled"] is True
        assert rolled_back.json()["cohort_percent"] == 100
        async with application.state.session_factory() as db:
            historical = await db.get(AnalysisJob, historical_id)
            assert historical and historical.rule_version == "squat.side.historical"
            assert await db.scalar(select(func.count(ReleasePromotion.id))) == 4
            actions = {event.action for event in await db.scalars(select(AuditEvent))}
            assert actions >= {
                "release.flag_configured",
                "release.promoted",
                "release.disabled",
                "release.rolled_back",
            }
        await engine.dispose()

    asyncio.run(exercise())


def test_canary_assignment_is_stable_and_honors_boundaries() -> None:
    user_id = uuid.UUID("10000000-0000-0000-0000-000000000001")
    first = in_canary_cohort(user_id, "squat.depth", 20)
    assert in_canary_cohort(user_id, "squat.depth", 20) is first
    assert in_canary_cohort(user_id, "squat.depth", 0) is False
    assert in_canary_cohort(user_id, "squat.depth", 100) is True
