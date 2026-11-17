from __future__ import annotations

import asyncio
import uuid

from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine

from repwise_api.database import Base, create_session_factory
from repwise_api.main import create_app
from repwise_api.models import AnalysisJob, MediaUpload, ReportFeedback, UploadStatus

OWNER = uuid.UUID("10000000-0000-0000-0000-000000000001")
OTHER = uuid.UUID("20000000-0000-0000-0000-000000000002")


async def feedback_app():
    application = create_app()
    await application.state.database_engine.dispose()
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    application.state.database_engine = engine
    application.state.session_factory = create_session_factory(engine)
    upload = MediaUpload(
        owner_id=OWNER,
        idempotency_key="feedback-upload",
        object_key="users/owner/uploads/feedback/source",
        filename="squat.mp4",
        content_type="video/mp4",
        declared_size=10,
        expected_sha256="a" * 64,
        status=UploadStatus.COMPLETED,
    )
    async with application.state.session_factory() as db:
        db.add(upload)
        await db.flush()
        analysis = AnalysisJob(
            upload_id=upload.id,
            owner_id=OWNER,
            status="completed",
            report_schema_version="repwise.evidence-report.v1",
            rule_version="squat.side.v3",
        )
        db.add(analysis)
        await db.commit()
    return application, engine, analysis.id


def test_feedback_is_owner_scoped_auditable_and_version_pinned() -> None:
    async def exercise() -> None:
        application, engine, analysis_id = await feedback_app()
        owner_headers = {"Authorization": f"Bearer {OWNER}"}
        foreign_headers = {"Authorization": f"Bearer {OTHER}"}
        async with AsyncClient(
            transport=ASGITransport(app=application), base_url="http://test"
        ) as client:
            first = await client.post(
                f"/v1/reports/{analysis_id}/feedback",
                headers=owner_headers,
                json={
                    "category": "wrong_count",
                    "rep_index": 2,
                    "comment": "Rep two was counted twice.",
                },
            )
            second = await client.post(
                f"/v1/reports/{analysis_id}/feedback",
                headers=owner_headers,
                json={
                    "category": "misleading_advice",
                    "check_id": "tempo.consistency",
                },
            )
            listed = await client.get(
                f"/v1/reports/{analysis_id}/feedback", headers=owner_headers
            )
            foreign_submit = await client.post(
                f"/v1/reports/{analysis_id}/feedback",
                headers=foreign_headers,
                json={"category": "bad_tracking"},
            )
            foreign_list = await client.get(
                f"/v1/reports/{analysis_id}/feedback", headers=foreign_headers
            )

        assert first.status_code == 201
        assert second.status_code == 201
        assert first.json()["rule_version"] == "squat.side.v3"
        assert first.json()["report_schema_version"] == "repwise.evidence-report.v1"
        assert "media_url" not in first.json()
        assert [item["category"] for item in listed.json()] == [
            "wrong_count",
            "misleading_advice",
        ]
        assert foreign_submit.status_code == 404
        assert foreign_list.status_code == 404
        async with application.state.session_factory() as db:
            records = (await db.scalars(select(ReportFeedback))).all()
            assert len(records) == 2
            assert all(record.owner_id == OWNER for record in records)
        await engine.dispose()

    asyncio.run(exercise())


def test_feedback_rejects_urls_unknown_fields_and_invalid_categories() -> None:
    async def exercise() -> None:
        application, engine, analysis_id = await feedback_app()
        headers = {"Authorization": f"Bearer {OWNER}"}
        endpoint = f"/v1/reports/{analysis_id}/feedback"
        async with AsyncClient(
            transport=ASGITransport(app=application), base_url="http://test"
        ) as client:
            public_url = await client.post(
                endpoint,
                headers=headers,
                json={
                    "category": "bad_tracking",
                    "comment": "Video: https://public.example/video.mp4",
                },
            )
            unknown = await client.post(
                endpoint,
                headers=headers,
                json={"category": "wrong_count", "media_url": "https://example.test"},
            )
            invalid = await client.post(
                endpoint, headers=headers, json={"category": "other"}
            )
            invalid_rep = await client.post(
                endpoint,
                headers=headers,
                json={"category": "wrong_count", "rep_index": 0},
            )

        assert public_url.status_code == 422
        assert unknown.status_code == 422
        assert invalid.status_code == 422
        assert invalid_rep.status_code == 422
        await engine.dispose()

    asyncio.run(exercise())
