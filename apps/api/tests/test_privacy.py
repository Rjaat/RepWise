from __future__ import annotations

import asyncio

from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import create_async_engine

from repwise_api.auth import issue_access_token, new_session
from repwise_api.database import Base, create_session_factory
from repwise_api.main import create_app
from repwise_api.models import (
    AccountDeletionRequest,
    AnalysisArtifact,
    AnalysisJob,
    AnalysisTombstone,
    AnnotationAssignment,
    ArtifactKind,
    AuthSession,
    FeedbackCategory,
    MediaUpload,
    OperationalAlert,
    ReportFeedback,
    ResearchConsent,
    SupportAccessGrant,
    UploadStatus,
    UserAccount,
    UserRole,
)
from repwise_api.settings import Settings


class PrivacyStorage:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}
        self.removed: list[str] = []

    def remove(self, object_key: str) -> None:
        self.removed.append(object_key)
        self.objects.pop(object_key, None)


async def privacy_app():
    application = create_app()
    await application.state.database_engine.dispose()
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    application.state.database_engine = engine
    application.state.session_factory = create_session_factory(engine)
    application.state.settings = Settings(allow_legacy_bearer_identity=False)
    storage = PrivacyStorage()
    application.state.object_storage = storage
    users: dict[str, UserAccount] = {}
    tokens: dict[str, str] = {}
    async with application.state.session_factory() as db:
        for name, role in {
            "owner": UserRole.USER,
            "other": UserRole.USER,
            "reviewer": UserRole.REVIEWER,
            "support": UserRole.SUPPORT,
        }.items():
            user = UserAccount(
                external_subject=f"idp|privacy-{name}",
                email=f"privacy-{name}@example.com",
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
            owner_id=users["owner"].id,
            idempotency_key="privacy-upload",
            object_key="users/owner/uploads/privacy/source",
            filename="squat.mp4",
            content_type="video/mp4",
            declared_size=10,
            expected_sha256="a" * 64,
            status=UploadStatus.COMPLETED,
        )
        db.add(upload)
        await db.flush()
        analysis = AnalysisJob(
            upload_id=upload.id,
            owner_id=users["owner"].id,
            status="completed",
            rule_version="squat.side.v3",
        )
        db.add(analysis)
        await db.flush()
        artifact = AnalysisArtifact(
            analysis_id=analysis.id,
            object_key=f"analyses/{analysis.id}/pose.json",
            kind=ArtifactKind.DERIVED,
            size_bytes=100,
        )
        feedback = ReportFeedback(
            analysis_id=analysis.id,
            owner_id=users["owner"].id,
            category=FeedbackCategory.BAD_TRACKING,
            comment="Wrist tracking dropped.",
            report_schema_version="repwise.evidence-report.v1",
            rule_version="squat.side.v3",
        )
        consent = ResearchConsent(
            analysis_id=analysis.id,
            owner_id=users["owner"].id,
            purpose="Evaluation",
        )
        db.add_all([artifact, feedback, consent])
        await db.flush()
        db.add_all(
            [
                AnnotationAssignment(
                    analysis_id=analysis.id,
                    consent_id=consent.id,
                    reviewer_id=users["reviewer"].id,
                    assigned_by=users["owner"].id,
                ),
                SupportAccessGrant(
                    analysis_id=analysis.id,
                    support_user_id=users["support"].id,
                    granted_by=users["owner"].id,
                    case_reference="CASE-PRIVACY",
                    expires_at=analysis.raw_expires_at,
                ),
                OperationalAlert(
                    analysis_id=analysis.id,
                    category="worker_timeout",
                    message="Timed out",
                ),
            ]
        )
        await db.commit()
    report_key = f"analyses/{analysis.id}/report.v1.json"
    storage.objects.update(
        {
            upload.object_key: b"raw",
            artifact.object_key: b"pose",
            report_key: b"report",
        }
    )
    return application, engine, storage, users, tokens, analysis.id


def bearer(tokens: dict[str, str], name: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {tokens[name]}"}


def test_exports_are_owner_scoped_structured_and_private() -> None:
    async def exercise() -> None:
        application, engine, _storage, _users, tokens, analysis_id = await privacy_app()
        async with AsyncClient(
            transport=ASGITransport(app=application), base_url="http://test"
        ) as client:
            account = await client.post(
                "/v1/exports/account", headers=bearer(tokens, "owner")
            )
            report = await client.post(
                f"/v1/exports/reports/{analysis_id}",
                headers=bearer(tokens, "owner"),
            )
            foreign = await client.post(
                f"/v1/exports/reports/{analysis_id}",
                headers=bearer(tokens, "other"),
            )

        assert account.status_code == 200
        assert len(account.json()["analyses"]) == 1
        assert account.json()["feedback"][0]["category"] == "bad_tracking"
        assert "object_key" not in str(account.json())
        assert "url" not in str(account.json())
        assert report.json()["rule_version"] == "squat.side.v3"
        assert foreign.status_code == 404
        await engine.dispose()

    asyncio.run(exercise())


def test_account_deletion_completes_across_database_sessions_and_storage() -> None:
    async def exercise() -> None:
        application, engine, storage, users, tokens, analysis_id = await privacy_app()
        owner_id = users["owner"].id
        async with AsyncClient(
            transport=ASGITransport(app=application), base_url="http://test"
        ) as client:
            deleted = await client.delete(
                "/v1/privacy/account", headers=bearer(tokens, "owner")
            )
            former_session = await client.post(
                "/v1/exports/account", headers=bearer(tokens, "owner")
            )

        assert deleted.status_code == 200
        assert deleted.json()["status"] == "completed"
        assert former_session.status_code == 401
        assert not storage.objects
        async with application.state.session_factory() as db:
            assert await db.get(AnalysisTombstone, analysis_id)
            assert await db.scalar(select(func.count(AnalysisJob.id))) == 0
            assert await db.scalar(select(func.count(MediaUpload.id))) == 0
            assert await db.scalar(select(func.count(AnalysisArtifact.id))) == 0
            assert await db.scalar(select(func.count(ReportFeedback.id))) == 0
            assert await db.scalar(select(func.count(ResearchConsent.id))) == 0
            assert await db.scalar(select(func.count(AnnotationAssignment.id))) == 0
            assert await db.scalar(select(func.count(SupportAccessGrant.id))) == 0
            assert await db.scalar(select(func.count(OperationalAlert.id))) == 0
            assert (
                await db.scalar(
                    select(func.count(AuthSession.id)).where(
                        AuthSession.user_id == owner_id
                    )
                )
                == 0
            )
            account = await db.get(UserAccount, owner_id)
            assert account and account.disabled_at
            assert account.email.endswith("@invalid.local")
            deletion = await db.scalar(
                select(AccountDeletionRequest).where(
                    AccountDeletionRequest.owner_id == owner_id
                )
            )
            assert deletion and deletion.status == "completed"
        await engine.dispose()

    asyncio.run(exercise())
