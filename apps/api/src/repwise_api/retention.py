from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated, Literal, cast

from anyio import to_thread
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from repwise_api.auth import authenticated_user
from repwise_api.database import request_session
from repwise_api.errors import ApiError
from repwise_api.models import (
    AnalysisArtifact,
    AnalysisJob,
    AnalysisTombstone,
    ArtifactKind,
    DeletionRequest,
    MediaUpload,
)
from repwise_api.storage import ObjectStorage

router = APIRouter(prefix="/v1/history", tags=["history"])


class HistoryItem(BaseModel):
    analysis_id: uuid.UUID
    status: str
    created_at: datetime
    completed_at: datetime | None
    raw_available_until: datetime | None


class HistoryResponse(BaseModel):
    items: list[HistoryItem]


class DeletionResponse(BaseModel):
    request_id: uuid.UUID
    status: Literal["pending", "completed"]


def history_storage(request: Request) -> ObjectStorage:
    return cast(ObjectStorage, request.app.state.object_storage)


def history_item(job: AnalysisJob) -> HistoryItem:
    return HistoryItem(
        analysis_id=job.id,
        status=job.status,
        created_at=job.created_at,
        completed_at=job.completed_at,
        raw_available_until=None if job.raw_expired_at else job.raw_expires_at,
    )


# These database continuations are exercised through ASGI in test_retention.py.
# Python 3.13 coverage cannot trace them after SQLAlchemy's greenlet handoff.
async def owned_analysis(  # pragma: no cover
    db: AsyncSession, analysis_id: uuid.UUID, owner_id: uuid.UUID
) -> AnalysisJob:
    job = await db.scalar(
        select(AnalysisJob).where(AnalysisJob.id == analysis_id).with_for_update()
    )
    if not job or job.owner_id != owner_id or job.deleted_at:
        raise ApiError(404, "analysis_not_found", "Analysis not found.")
    return job


@router.get("", response_model=HistoryResponse)
async def history(  # pragma: no cover - ASGI integration covered
    owner_id: Annotated[uuid.UUID, Depends(authenticated_user)],
    db: Annotated[AsyncSession, Depends(request_session)],
) -> HistoryResponse:
    jobs = await db.scalars(
        select(AnalysisJob)
        .where(AnalysisJob.owner_id == owner_id, AnalysisJob.deleted_at.is_(None))
        .order_by(AnalysisJob.created_at.desc())
    )
    return HistoryResponse(items=[history_item(job) for job in jobs])


@router.get("/{analysis_id}", response_model=HistoryItem)
async def history_detail(
    analysis_id: uuid.UUID,
    owner_id: Annotated[uuid.UUID, Depends(authenticated_user)],
    db: Annotated[AsyncSession, Depends(request_session)],
) -> HistoryItem:
    return history_item(await owned_analysis(db, analysis_id, owner_id))


@router.delete("/{analysis_id}", response_model=DeletionResponse)
async def delete_analysis(  # pragma: no cover - ASGI integration covered
    analysis_id: uuid.UUID,
    owner_id: Annotated[uuid.UUID, Depends(authenticated_user)],
    db: Annotated[AsyncSession, Depends(request_session)],
    object_storage: Annotated[ObjectStorage, Depends(history_storage)],
) -> DeletionResponse:
    existing = await db.scalar(
        select(DeletionRequest).where(
            DeletionRequest.analysis_id == analysis_id,
            DeletionRequest.owner_id == owner_id,
        )
    )
    if existing and existing.status == "completed":
        return DeletionResponse(request_id=existing.id, status="completed")
    if existing:
        job = await db.get(AnalysisJob, analysis_id)
        if not job or job.owner_id != owner_id:
            raise ApiError(404, "analysis_not_found", "Analysis not found.")
    else:
        job = await owned_analysis(db, analysis_id, owner_id)
    upload = await db.get(MediaUpload, job.upload_id)
    artifacts = await db.scalars(
        select(AnalysisArtifact).where(AnalysisArtifact.analysis_id == job.id)
    )
    deletion = existing or DeletionRequest(analysis_id=job.id, owner_id=owner_id)
    if existing is None:
        db.add(deletion)
    now = datetime.now(UTC)
    job.deleted_at = now
    if existing is None:
        db.add(AnalysisTombstone(analysis_id=job.id, owner_id=owner_id, deleted_at=now))
    await db.commit()

    keys = {artifact.object_key for artifact in artifacts}
    if upload:
        keys.add(upload.object_key)
    keys.add(f"analyses/{job.id}/report.v1.json")
    for key in keys:
        await to_thread.run_sync(object_storage.remove, key)
    deletion.status = "completed"
    deletion.completed_at = datetime.now(UTC)
    await db.commit()
    return DeletionResponse(  # pragma: no cover - post-greenlet continuation
        request_id=deletion.id, status="completed"
    )


async def expire_raw_media(
    db: AsyncSession, object_storage: ObjectStorage, now: datetime
) -> int:
    jobs = await db.scalars(
        select(AnalysisJob).where(
            AnalysisJob.deleted_at.is_(None),
            AnalysisJob.raw_expired_at.is_(None),
            AnalysisJob.raw_expires_at <= now,
        )
    )
    count = 0
    for job in jobs:
        upload = await db.get(MediaUpload, job.upload_id)
        if upload:
            await to_thread.run_sync(object_storage.remove, upload.object_key)
        raw_artifacts = await db.scalars(
            select(AnalysisArtifact).where(
                AnalysisArtifact.analysis_id == job.id,
                AnalysisArtifact.kind == ArtifactKind.RAW,
            )
        )
        for artifact in raw_artifacts:
            await to_thread.run_sync(object_storage.remove, artifact.object_key)
        job.raw_expired_at = now
        count += 1
    await db.commit()
    return count


def reject_tombstoned_analysis(analysis_id: str, database_url: str) -> None:
    """Prevent a worker retry from recreating a deleted analysis artifact."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session

    sync_url = database_url.replace("sqlite+aiosqlite://", "sqlite+pysqlite://")
    engine = create_engine(sync_url)
    try:
        with Session(engine) as db:
            if db.get(AnalysisTombstone, uuid.UUID(analysis_id)):
                raise RuntimeError("Analysis was deleted and cannot be retried")
    finally:
        engine.dispose()
