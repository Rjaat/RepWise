from __future__ import annotations

import asyncio
import uuid

from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine

from repwise_api.database import Base, create_session_factory
from repwise_api.main import create_app
from repwise_api.models import AnalysisJob, MediaUpload, UploadStatus
from repwise_api.progress import incompatibility_reasons

OWNER = uuid.UUID("10000000-0000-0000-0000-000000000001")
OTHER = uuid.UUID("20000000-0000-0000-0000-000000000002")


async def progress_app(**comparison_overrides: object):
    application = create_app()
    await application.state.database_engine.dispose()
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    application.state.database_engine = engine
    application.state.session_factory = create_session_factory(engine)

    jobs: list[AnalysisJob] = []
    async with application.state.session_factory() as db:
        for label, overrides in (
            ("baseline", {}),
            ("comparison", comparison_overrides),
        ):
            upload = MediaUpload(
                owner_id=OWNER,
                idempotency_key=f"progress-{label}",
                object_key=f"users/owner/uploads/{label}/source",
                filename="squat.mp4",
                content_type="video/mp4",
                declared_size=10,
                expected_sha256="a" * 64,
                status=UploadStatus.COMPLETED,
            )
            db.add(upload)
            await db.flush()
            values = {
                "upload_id": upload.id,
                "owner_id": OWNER,
                "status": "completed",
                "exercise": "bodyweight_squat",
                "variant": "bodyweight",
                "view": "side",
                "report_schema_version": "repwise.evidence-report.v1",
                "rule_version": "squat.side.v3",
                "assessment_coverage": 0.94,
                "rep_count": 10 if label == "baseline" else 13,
            }
            values.update(overrides)
            job = AnalysisJob(**values)
            db.add(job)
            jobs.append(job)
        await db.commit()
    return application, engine, jobs[0].id, jobs[1].id


def test_compatible_sessions_return_only_observed_delta_and_context() -> None:
    async def exercise() -> None:
        application, engine, baseline_id, comparison_id = await progress_app()
        async with AsyncClient(
            transport=ASGITransport(app=application), base_url="http://test"
        ) as client:
            response = await client.post(
                "/v1/progress/compare",
                headers={"Authorization": f"Bearer {OWNER}"},
                json={
                    "baseline_id": str(baseline_id),
                    "comparison_id": str(comparison_id),
                },
            )

        assert response.status_code == 200
        assert response.json()["comparable"] is True
        assert response.json()["reasons"] == []
        assert response.json()["rep_count_delta"] == 3
        assert response.json()["baseline"]["assessment_coverage"] == 0.94
        assert "form_score" not in response.json()
        await engine.dispose()

    asyncio.run(exercise())


def test_incompatible_context_never_emits_a_misleading_delta() -> None:
    async def exercise() -> None:
        application, engine, baseline_id, comparison_id = await progress_app(
            view="front", rule_version="squat.front.v1", rep_count=10
        )
        async with AsyncClient(
            transport=ASGITransport(app=application), base_url="http://test"
        ) as client:
            response = await client.post(
                "/v1/progress/compare",
                headers={"Authorization": f"Bearer {OWNER}"},
                json={
                    "baseline_id": str(baseline_id),
                    "comparison_id": str(comparison_id),
                },
            )

        assert response.status_code == 200
        assert response.json()["comparable"] is False
        assert response.json()["rep_count_delta"] is None
        assert response.json()["reasons"] == ["view_mismatch", "rule_version_mismatch"]
        await engine.dispose()

    asyncio.run(exercise())


def test_missing_or_low_coverage_and_counts_are_explicitly_incomparable() -> None:
    baseline = AnalysisJob(
        exercise="bodyweight_squat",
        variant="bodyweight",
        view="side",
        report_schema_version="v1",
        rule_version="rules-v1",
        status="completed",
        assessment_coverage=0.9,
        rep_count=10,
    )
    missing = AnalysisJob(
        exercise="bodyweight_squat",
        variant="bodyweight",
        view="side",
        report_schema_version="v1",
        rule_version="rules-v1",
        status="completed",
        assessment_coverage=None,
        rep_count=None,
    )
    low = AnalysisJob(
        exercise="bodyweight_squat",
        variant="bodyweight",
        view="side",
        report_schema_version="v1",
        rule_version="rules-v1",
        status="processing",
        assessment_coverage=0.79,
        rep_count=10,
    )

    assert incompatibility_reasons(baseline, missing) == [
        "rep_count_unavailable",
        "coverage_unavailable",
    ]
    assert incompatibility_reasons(baseline, low) == [
        "analysis_incomplete",
        "coverage_below_threshold",
    ]


def test_progress_comparison_is_owner_scoped_and_rejects_unknown_fields() -> None:
    async def exercise() -> None:
        application, engine, baseline_id, comparison_id = await progress_app()
        body = {
            "baseline_id": str(baseline_id),
            "comparison_id": str(comparison_id),
        }
        async with AsyncClient(
            transport=ASGITransport(app=application), base_url="http://test"
        ) as client:
            foreign = await client.post(
                "/v1/progress/compare",
                headers={"Authorization": f"Bearer {OTHER}"},
                json=body,
            )
            unknown = await client.post(
                "/v1/progress/compare",
                headers={"Authorization": f"Bearer {OWNER}"},
                json={**body, "form_score": 100},
            )

        assert foreign.status_code == 404
        assert unknown.status_code == 422
        await engine.dispose()

    asyncio.run(exercise())
