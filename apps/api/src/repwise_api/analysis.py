from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated, Protocol, cast

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from repwise_api.auth import authenticated_user
from repwise_api.database import request_session
from repwise_api.errors import ApiError
from repwise_api.models import AnalysisJob
from repwise_api.worker import analysis_preflight_task

router = APIRouter(prefix="/v1/analyses", tags=["analyses"])


class AnalysisDispatcher(Protocol):
    def __call__(self, analysis_id: uuid.UUID, object_key: str, sha256: str) -> str: ...


class AnalysisStatusResponse(BaseModel):
    analysis_id: uuid.UUID
    status: str
    current_stage: str
    retry_count: int
    error_category: str | None
    worker_task_id: str | None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None


def enqueue_analysis(analysis_id: uuid.UUID, object_key: str, sha256: str) -> str:
    result = analysis_preflight_task.delay(str(analysis_id), object_key, sha256)
    if not result.id:
        raise RuntimeError("Analysis queue returned no task identifier")
    return str(result.id)


def request_dispatcher(request: Request) -> AnalysisDispatcher:
    return cast(AnalysisDispatcher, request.app.state.analysis_dispatcher)


def status_response(job: AnalysisJob) -> AnalysisStatusResponse:
    return AnalysisStatusResponse(
        analysis_id=job.id,
        status=job.status,
        current_stage=job.current_stage,
        retry_count=job.retry_count,
        error_category=job.last_error_category,
        worker_task_id=job.worker_task_id,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
    )


@router.get("/{analysis_id}", response_model=AnalysisStatusResponse)
async def analysis_status(  # pragma: no cover - ASGI integration covered
    analysis_id: uuid.UUID,
    owner_id: Annotated[uuid.UUID, Depends(authenticated_user)],
    db: Annotated[AsyncSession, Depends(request_session)],
) -> AnalysisStatusResponse:
    job = await db.scalar(
        select(AnalysisJob).where(
            AnalysisJob.id == analysis_id,
            AnalysisJob.owner_id == owner_id,
            AnalysisJob.deleted_at.is_(None),
        )
    )
    if not job:
        raise ApiError(404, "analysis_not_found", "Analysis not found.")
    return status_response(job)
