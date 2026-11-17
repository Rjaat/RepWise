from __future__ import annotations

import asyncio

from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine

from repwise_api.auth import issue_access_token, new_session
from repwise_api.database import Base, create_session_factory
from repwise_api.main import create_app
from repwise_api.models import (
    AnalysisJob,
    AuditEvent,
    MediaUpload,
    UploadStatus,
    UserAccount,
    UserRole,
)
from repwise_api.settings import Settings


class ReviewStorage:
    def presigned_get(self, object_key: str) -> str:
        return f"https://private.storage.test/{object_key}?expires=300"


async def annotation_app():
    application = create_app()
    await application.state.database_engine.dispose()
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    application.state.database_engine = engine
    application.state.session_factory = create_session_factory(engine)
    application.state.settings = Settings(allow_legacy_bearer_identity=False)
    application.state.object_storage = ReviewStorage()
    roles = {
        "owner": UserRole.USER,
        "reviewer": UserRole.REVIEWER,
        "other_reviewer": UserRole.REVIEWER,
        "admin": UserRole.ADMIN,
    }
    users: dict[str, UserAccount] = {}
    tokens: dict[str, str] = {}
    async with application.state.session_factory() as db:
        for name, role in roles.items():
            user = UserAccount(
                external_subject=f"idp|{name}",
                email=f"{name}@example.com",
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
        upload = MediaUpload(
            owner_id=users["owner"].id,
            idempotency_key="annotation-source",
            object_key="users/owner/uploads/annotation/source",
            filename="squat.mp4",
            content_type="video/mp4",
            declared_size=10,
            expected_sha256="a" * 64,
            status=UploadStatus.COMPLETED,
        )
        db.add(upload)
        await db.flush()
        analysis = AnalysisJob(
            upload_id=upload.id, owner_id=users["owner"].id, status="completed"
        )
        db.add(analysis)
        await db.commit()
    return application, engine, users, tokens, analysis.id


def bearer(tokens: dict[str, str], name: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {tokens[name]}"}


def test_consented_assignment_annotation_adjudication_and_release() -> None:
    async def exercise() -> None:
        application, engine, users, tokens, analysis_id = await annotation_app()
        async with AsyncClient(
            transport=ASGITransport(app=application), base_url="http://test"
        ) as client:
            consent = await client.post(
                f"/v1/privacy/analyses/{analysis_id}/consent",
                headers=bearer(tokens, "owner"),
                json={"purpose": "Improve side-view squat assessment"},
            )
            consent_again = await client.post(
                f"/v1/privacy/analyses/{analysis_id}/consent",
                headers=bearer(tokens, "owner"),
                json={"purpose": "Improve side-view squat assessment"},
            )
            forbidden_assignment = await client.post(
                "/v1/admin/annotation-assignments",
                headers=bearer(tokens, "owner"),
                json={
                    "analysis_id": str(analysis_id),
                    "reviewer_id": str(users["reviewer"].id),
                },
            )
            assignment = await client.post(
                "/v1/admin/annotation-assignments",
                headers=bearer(tokens, "admin"),
                json={
                    "analysis_id": str(analysis_id),
                    "reviewer_id": str(users["reviewer"].id),
                },
            )
            assignment_id = assignment.json()["id"]
            assigned = await client.get(
                "/v1/review/assignments", headers=bearer(tokens, "reviewer")
            )
            unassigned = await client.get(
                "/v1/review/assignments",
                headers=bearer(tokens, "other_reviewer"),
            )
            hidden_asset = await client.get(
                f"/v1/review/assignments/{assignment_id}/asset",
                headers=bearer(tokens, "other_reviewer"),
            )
            asset = await client.get(
                f"/v1/review/assignments/{assignment_id}/asset",
                headers=bearer(tokens, "reviewer"),
            )
            annotation = await client.post(
                f"/v1/review/assignments/{assignment_id}/annotations",
                headers=bearer(tokens, "reviewer"),
                json={
                    "labels": {"rep_boundaries": [[1.0, 3.0]], "visibility": "clear"},
                    "uncertain": False,
                },
            )
            adjudication = await client.post(
                f"/v1/admin/annotation-assignments/{assignment_id}/adjudicate",
                headers=bearer(tokens, "admin"),
                json={"decision": {"accepted": True, "reason": "clear"}},
            )
            release = await client.post(
                "/v1/admin/releases",
                headers=bearer(tokens, "admin"),
                json={
                    "rule_version": "squat.side.v2",
                    "adjudication_id": adjudication.json()["id"],
                    "decision": "approved",
                },
            )

        assert consent.status_code == 200
        assert consent_again.json() == consent.json()
        assert forbidden_assignment.status_code == 403
        assert assignment.status_code == 200
        assert len(assigned.json()) == 1
        assert unassigned.json() == []
        assert hidden_asset.status_code == 404
        assert asset.status_code == 200
        assert asset.json()["url"].startswith("https://private.storage.test/")
        assert annotation.status_code == 201
        assert adjudication.json()["status"] == "adjudicated"
        assert release.json()["status"] == "approved"
        async with application.state.session_factory() as db:
            events = (await db.scalars(select(AuditEvent))).all()
            assert {event.action for event in events} == {
                "consent.granted",
                "annotation.assigned",
                "annotation.asset_accessed",
                "annotation.submitted",
                "annotation.adjudicated",
                "release.decided",
            }
        await engine.dispose()

    asyncio.run(exercise())


def test_revoked_consent_immediately_hides_assigned_asset() -> None:
    async def exercise() -> None:
        application, engine, users, tokens, analysis_id = await annotation_app()
        async with AsyncClient(
            transport=ASGITransport(app=application), base_url="http://test"
        ) as client:
            await client.post(
                f"/v1/privacy/analyses/{analysis_id}/consent",
                headers=bearer(tokens, "owner"),
                json={"purpose": "Review consent"},
            )
            assignment = await client.post(
                "/v1/admin/annotation-assignments",
                headers=bearer(tokens, "admin"),
                json={
                    "analysis_id": str(analysis_id),
                    "reviewer_id": str(users["reviewer"].id),
                },
            )
            revoked = await client.delete(
                f"/v1/privacy/analyses/{analysis_id}/consent",
                headers=bearer(tokens, "owner"),
            )
            assignments = await client.get(
                "/v1/review/assignments", headers=bearer(tokens, "reviewer")
            )
            asset = await client.get(
                f"/v1/review/assignments/{assignment.json()['id']}/asset",
                headers=bearer(tokens, "reviewer"),
            )

        assert revoked.json()["status"] == "revoked"
        assert assignments.json() == []
        assert asset.status_code == 410
        await engine.dispose()

    asyncio.run(exercise())
