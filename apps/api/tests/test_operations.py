from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime, timedelta

from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine

from repwise_api.auth import issue_access_token, new_session
from repwise_api.database import Base, create_session_factory
from repwise_api.main import create_app
from repwise_api.models import (
    AnalysisArtifact,
    AnalysisJob,
    ArtifactKind,
    AuditEvent,
    MediaUpload,
    OperationalAlert,
    SupportAccessGrant,
    UploadStatus,
    UserAccount,
    UserRole,
)
from repwise_api.operations import record_failure
from repwise_api.settings import Settings


async def operations_app():
    application = create_app()
    await application.state.database_engine.dispose()
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    application.state.database_engine = engine
    application.state.session_factory = create_session_factory(engine)
    application.state.settings = Settings(allow_legacy_bearer_identity=False)
    users: dict[str, UserAccount] = {}
    tokens: dict[str, str] = {}
    async with application.state.session_factory() as db:
        for name, role in {
            "owner": UserRole.USER,
            "admin": UserRole.ADMIN,
            "support": UserRole.SUPPORT,
            "other_support": UserRole.SUPPORT,
        }.items():
            user = UserAccount(
                external_subject=f"idp|ops-{name}",
                email=f"ops-{name}@example.com",
                email_verified=True,
                role=role,
            )
            db.add(user)
            await db.flush()
            auth_session, _ = new_session(user.id, application.state.settings)
            db.add(auth_session)
            await db.flush()
            users[name] = user
            tokens[name] = issue_access_token(
                user, auth_session, application.state.settings
            )
        jobs: list[AnalysisJob] = []
        for index in range(2):
            upload = MediaUpload(
                owner_id=users["owner"].id,
                idempotency_key=f"ops-{index}",
                object_key=f"users/owner/uploads/ops-{index}/source",
                filename="squat.mp4",
                content_type="video/mp4",
                declared_size=10,
                expected_sha256="a" * 64,
                status=UploadStatus.COMPLETED,
            )
            db.add(upload)
            await db.flush()
            job = AnalysisJob(
                upload_id=upload.id,
                owner_id=users["owner"].id,
                status="queued",
                estimated_cost_micros=250,
            )
            db.add(job)
            await db.flush()
            db.add(
                AnalysisArtifact(
                    analysis_id=job.id,
                    object_key=f"analyses/{job.id}/artifact.json",
                    kind=ArtifactKind.DERIVED,
                    size_bytes=1024,
                )
            )
            jobs.append(job)
        await record_failure(db, jobs[0], "worker_timeout", "Worker timed out")
        await record_failure(
            db, jobs[1], "storage_unavailable", "Object storage unavailable"
        )
    return application, engine, users, tokens, jobs


def bearer(tokens: dict[str, str], name: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {tokens[name]}"}


def test_operations_alert_metrics_and_transient_retry() -> None:
    async def exercise() -> None:
        application, engine, _users, tokens, jobs = await operations_app()
        first_id, second_id = jobs[0].id, jobs[1].id
        async with AsyncClient(
            transport=ASGITransport(app=application), base_url="http://test"
        ) as client:
            forbidden = await client.get(
                "/v1/admin/operations/summary", headers=bearer(tokens, "owner")
            )
            summary = await client.get(
                "/v1/admin/operations/summary", headers=bearer(tokens, "admin")
            )
            alerts = await client.get(
                "/v1/admin/operations/alerts", headers=bearer(tokens, "admin")
            )
            retried = await client.post(
                f"/v1/admin/jobs/{first_id}/retry", headers=bearer(tokens, "admin")
            )
            recovered_summary = await client.get(
                "/v1/admin/operations/summary", headers=bearer(tokens, "admin")
            )
            async with application.state.session_factory() as db:
                second = await db.get(AnalysisJob, second_id)
                assert second is not None
                second.deleted_at = datetime.now(UTC)
                await db.commit()
            deleted_retry = await client.post(
                f"/v1/admin/jobs/{second_id}/retry", headers=bearer(tokens, "admin")
            )

        assert forbidden.status_code == 403
        assert summary.json() == {
            "queued_jobs": 0,
            "failed_jobs": 2,
            "active_alerts": 2,
            "storage_bytes": 2048,
            "estimated_cost_micros": 500,
        }
        assert {item["category"] for item in alerts.json()} == {
            "worker_timeout",
            "storage_unavailable",
        }
        assert retried.json()["status"] == "queued"
        assert retried.json()["retry_count"] == 1
        assert recovered_summary.json()["active_alerts"] == 1
        assert deleted_retry.status_code == 404
        async with application.state.session_factory() as db:
            first = await db.get(AnalysisJob, first_id)
            assert first and first.owner_id == jobs[0].owner_id
            events = (await db.scalars(select(AuditEvent))).all()
            assert any(event.action == "job.retry_requested" for event in events)
            assert len((await db.scalars(select(OperationalAlert))).all()) == 2
        await engine.dispose()

    asyncio.run(exercise())


def test_support_grants_are_scoped_expiring_and_deletion_aware() -> None:
    async def exercise() -> None:
        application, engine, users, tokens, jobs = await operations_app()
        analysis_id = jobs[0].id
        async with AsyncClient(
            transport=ASGITransport(app=application), base_url="http://test"
        ) as client:
            absent = await client.get(
                f"/v1/support/analyses/{analysis_id}",
                headers=bearer(tokens, "support"),
            )
            grant = await client.post(
                "/v1/admin/support-grants",
                headers=bearer(tokens, "admin"),
                json={
                    "analysis_id": str(analysis_id),
                    "support_user_id": str(users["support"].id),
                    "case_reference": "CASE-1042",
                    "duration_minutes": 30,
                },
            )
            allowed = await client.get(
                f"/v1/support/analyses/{analysis_id}",
                headers=bearer(tokens, "support"),
            )
            other_support = await client.get(
                f"/v1/support/analyses/{analysis_id}",
                headers=bearer(tokens, "other_support"),
            )
            async with application.state.session_factory() as db:
                access = await db.get(SupportAccessGrant, uuid.UUID(grant.json()["id"]))
                assert access is not None
                access.expires_at = datetime.now(UTC) - timedelta(seconds=1)
                await db.commit()
            expired = await client.get(
                f"/v1/support/analyses/{analysis_id}",
                headers=bearer(tokens, "support"),
            )

        assert absent.status_code == 404
        assert grant.status_code == 200
        assert allowed.status_code == 200
        assert allowed.json()["owner_id"] == str(users["owner"].id)
        assert other_support.status_code == 404
        assert expired.status_code == 404
        async with application.state.session_factory() as db:
            events = (await db.scalars(select(AuditEvent))).all()
            assert {event.action for event in events} >= {
                "support.granted",
                "support.analysis_accessed",
            }
        await engine.dispose()

    asyncio.run(exercise())
