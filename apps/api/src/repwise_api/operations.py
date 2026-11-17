from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from repwise_api.analysis import AnalysisDispatcher, request_dispatcher
from repwise_api.annotations import audit
from repwise_api.auth import Principal, require_roles
from repwise_api.database import request_session
from repwise_api.errors import ApiError
from repwise_api.models import (
    AnalysisArtifact,
    AnalysisJob,
    MediaUpload,
    OperationalAlert,
    SupportAccessGrant,
    UserAccount,
    UserRole,
)

router = APIRouter(prefix="/v1", tags=["operations"])
TRANSIENT_FAILURES = {
    "broker_unavailable",
    "worker_timeout",
    "worker_crash",
    "storage_unavailable",
}
MAX_RETRIES = 3


class OperationsSummary(BaseModel):
    queued_jobs: int
    failed_jobs: int
    active_alerts: int
    storage_bytes: int
    estimated_cost_micros: int


class RetryResponse(BaseModel):
    analysis_id: uuid.UUID
    status: str
    retry_count: int


class AlertResponse(BaseModel):
    id: uuid.UUID
    analysis_id: uuid.UUID
    category: str
    message: str


class SupportGrantRequest(BaseModel):
    analysis_id: uuid.UUID
    support_user_id: uuid.UUID
    case_reference: str = Field(min_length=3, max_length=128)
    duration_minutes: int = Field(default=30, ge=5, le=60)


class SupportGrantResponse(BaseModel):
    id: uuid.UUID
    expires_at: datetime


class SupportAnalysisResponse(BaseModel):
    analysis_id: uuid.UUID
    owner_id: uuid.UUID
    status: str
    error_category: str | None


async def record_failure(
    db: AsyncSession, analysis: AnalysisJob, category: str, message: str
) -> OperationalAlert:
    analysis.status = "failed"
    analysis.last_error_category = category
    alert = OperationalAlert(
        analysis_id=analysis.id, category=category, message=message
    )
    db.add(alert)
    await db.commit()
    return alert


@router.get("/admin/operations/summary", response_model=OperationsSummary)
async def operations_summary(  # pragma: no cover - ASGI integration covered
    _principal: Annotated[Principal, Depends(require_roles(UserRole.ADMIN))],
    db: Annotated[AsyncSession, Depends(request_session)],
) -> OperationsSummary:
    queued = await db.scalar(
        select(func.count(AnalysisJob.id)).where(AnalysisJob.status == "queued")
    )
    failed = await db.scalar(
        select(func.count(AnalysisJob.id)).where(AnalysisJob.status == "failed")
    )
    alerts = await db.scalar(
        select(func.count(OperationalAlert.id)).where(
            OperationalAlert.resolved_at.is_(None)
        )
    )
    storage = await db.scalar(
        select(func.coalesce(func.sum(AnalysisArtifact.size_bytes), 0))
    )
    cost = await db.scalar(
        select(func.coalesce(func.sum(AnalysisJob.estimated_cost_micros), 0))
    )
    return OperationsSummary(
        queued_jobs=queued or 0,
        failed_jobs=failed or 0,
        active_alerts=alerts or 0,
        storage_bytes=storage or 0,
        estimated_cost_micros=cost or 0,
    )


@router.get("/admin/operations/alerts", response_model=list[AlertResponse])
async def active_alerts(  # pragma: no cover - ASGI integration covered
    _principal: Annotated[Principal, Depends(require_roles(UserRole.ADMIN))],
    db: Annotated[AsyncSession, Depends(request_session)],
) -> list[AlertResponse]:
    alerts = await db.scalars(
        select(OperationalAlert)
        .where(OperationalAlert.resolved_at.is_(None))
        .order_by(OperationalAlert.created_at.desc())
    )
    return [
        AlertResponse(
            id=alert.id,
            analysis_id=alert.analysis_id,
            category=alert.category,
            message=alert.message,
        )
        for alert in alerts
    ]


@router.post("/admin/jobs/{analysis_id}/retry", response_model=RetryResponse)
async def retry_job(  # pragma: no cover - ASGI integration covered
    analysis_id: uuid.UUID,
    principal: Annotated[Principal, Depends(require_roles(UserRole.ADMIN))],
    db: Annotated[AsyncSession, Depends(request_session)],
    dispatcher: Annotated[AnalysisDispatcher, Depends(request_dispatcher)],
) -> RetryResponse:
    analysis = await db.get(AnalysisJob, analysis_id, with_for_update=True)
    if not analysis or analysis.deleted_at:
        raise ApiError(404, "analysis_not_found", "Analysis not found.")
    if analysis.last_error_category not in TRANSIENT_FAILURES:
        raise ApiError(409, "retry_not_allowed", "Only transient failures can retry.")
    if analysis.retry_count >= MAX_RETRIES:
        raise ApiError(409, "retry_limit_reached", "Retry limit reached.")
    analysis.retry_count += 1
    analysis.status = "queued"
    analysis.current_stage = "dispatch"
    alerts = await db.scalars(
        select(OperationalAlert).where(
            OperationalAlert.analysis_id == analysis.id,
            OperationalAlert.resolved_at.is_(None),
        )
    )
    for alert in alerts:
        alert.resolved_at = datetime.now(UTC)
    audit(
        db,
        principal,
        "job.retry_requested",
        "analysis_job",
        analysis.id,
        {"retry_count": analysis.retry_count},
    )
    await db.commit()
    upload = await db.get(MediaUpload, analysis.upload_id)
    if not upload:
        raise ApiError(409, "upload_not_found", "Analysis source upload is missing.")
    try:
        analysis.worker_task_id = dispatcher(
            analysis.id, upload.object_key, upload.expected_sha256
        )
        analysis.current_stage = "preflight"
        analysis.last_error_category = None
    except Exception:
        analysis.status = "dispatch_failed"
        analysis.last_error_category = "broker_unavailable"
    await db.commit()
    return RetryResponse(
        analysis_id=analysis.id,
        status=analysis.status,
        retry_count=analysis.retry_count,
    )


@router.post("/admin/support-grants", response_model=SupportGrantResponse)
async def create_support_grant(  # pragma: no cover - ASGI integration covered
    body: SupportGrantRequest,
    principal: Annotated[Principal, Depends(require_roles(UserRole.ADMIN))],
    db: Annotated[AsyncSession, Depends(request_session)],
) -> SupportGrantResponse:
    analysis = await db.get(AnalysisJob, body.analysis_id)
    support_user = await db.get(UserAccount, body.support_user_id)
    if not analysis or analysis.deleted_at:
        raise ApiError(404, "analysis_not_found", "Analysis not found.")
    if (
        not support_user
        or support_user.role is not UserRole.SUPPORT
        or support_user.disabled_at
    ):
        raise ApiError(
            422, "invalid_support_user", "An active support user is required."
        )
    grant = SupportAccessGrant(
        analysis_id=analysis.id,
        support_user_id=support_user.id,
        granted_by=principal.user_id,
        case_reference=body.case_reference,
        expires_at=datetime.now(UTC) + timedelta(minutes=body.duration_minutes),
    )
    db.add(grant)
    await db.flush()
    audit(db, principal, "support.granted", "support_access_grant", grant.id)
    await db.commit()
    return SupportGrantResponse(id=grant.id, expires_at=grant.expires_at)


@router.get("/support/analyses/{analysis_id}", response_model=SupportAnalysisResponse)
async def support_analysis(  # pragma: no cover - ASGI integration covered
    analysis_id: uuid.UUID,
    principal: Annotated[Principal, Depends(require_roles(UserRole.SUPPORT))],
    db: Annotated[AsyncSession, Depends(request_session)],
) -> SupportAnalysisResponse:
    now = datetime.now(UTC)
    grant = await db.scalar(
        select(SupportAccessGrant).where(
            SupportAccessGrant.analysis_id == analysis_id,
            SupportAccessGrant.support_user_id == principal.user_id,
            SupportAccessGrant.revoked_at.is_(None),
            SupportAccessGrant.expires_at > now,
        )
    )
    analysis = await db.get(AnalysisJob, analysis_id)
    if not grant or not analysis or analysis.deleted_at:
        raise ApiError(404, "support_access_not_found", "Support access not found.")
    audit(db, principal, "support.analysis_accessed", "analysis_job", analysis.id)
    await db.commit()
    return SupportAnalysisResponse(
        analysis_id=analysis.id,
        owner_id=analysis.owner_id,
        status=analysis.status,
        error_category=analysis.last_error_category,
    )
