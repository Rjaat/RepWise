from __future__ import annotations

import asyncio
import uuid
from types import SimpleNamespace
from unittest.mock import Mock, patch

from fastapi import Request
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine

from repwise_api.analysis import enqueue_analysis, request_dispatcher
from repwise_api.database import Base, create_session_factory
from repwise_api.main import create_app
from repwise_api.models import AnalysisJob, MediaUpload, UploadStatus

OWNER = uuid.UUID("10000000-0000-0000-0000-000000000001")
OTHER = uuid.UUID("20000000-0000-0000-0000-000000000002")


def test_enqueue_analysis_requires_and_returns_task_identifier() -> None:
    task = Mock(id="celery-task-001")
    with patch("repwise_api.analysis.analysis_preflight_task.delay", return_value=task):
        assert enqueue_analysis(OWNER, "private/source", "a" * 64) == "celery-task-001"

    task.id = None
    with patch("repwise_api.analysis.analysis_preflight_task.delay", return_value=task):
        try:
            enqueue_analysis(OWNER, "private/source", "a" * 64)
        except RuntimeError as error:
            assert str(error) == "Analysis queue returned no task identifier"
        else:
            raise AssertionError("Expected a missing task identifier to fail")


def test_request_dispatcher_reads_application_state() -> None:
    dispatcher = Mock()
    request = Mock(spec=Request)
    request.app = SimpleNamespace(state=SimpleNamespace(analysis_dispatcher=dispatcher))
    assert request_dispatcher(request) is dispatcher


def test_analysis_status_is_private_and_reports_dispatch_state() -> None:
    async def exercise() -> None:
        application = create_app()
        await application.state.database_engine.dispose()
        engine = create_async_engine("sqlite+aiosqlite://")
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        application.state.database_engine = engine
        application.state.session_factory = create_session_factory(engine)

        async with application.state.session_factory() as session:
            upload = MediaUpload(
                owner_id=OWNER,
                idempotency_key="analysis-status",
                object_key="private/analysis-status",
                filename="squat.mp4",
                content_type="video/mp4",
                declared_size=10,
                expected_sha256="a" * 64,
                status=UploadStatus.COMPLETED,
            )
            session.add(upload)
            await session.flush()
            job = AnalysisJob(
                upload_id=upload.id,
                owner_id=OWNER,
                status="queued",
                current_stage="preflight",
                worker_task_id="celery-task-001",
            )
            session.add(job)
            await session.commit()
            job_id = job.id

        async with AsyncClient(
            transport=ASGITransport(app=application), base_url="http://test"
        ) as client:
            owned = await client.get(
                f"/v1/analyses/{job_id}",
                headers={"Authorization": f"Bearer {OWNER}"},
            )
            foreign = await client.get(
                f"/v1/analyses/{job_id}",
                headers={"Authorization": f"Bearer {OTHER}"},
            )

        assert owned.status_code == 200
        assert owned.json()["current_stage"] == "preflight"
        assert owned.json()["worker_task_id"] == "celery-task-001"
        assert foreign.status_code == 404
        assert foreign.json()["code"] == "analysis_not_found"
        await engine.dispose()

    asyncio.run(exercise())
