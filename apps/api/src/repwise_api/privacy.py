from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated, cast

from anyio import to_thread
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from repwise_api.auth import Principal, authenticated_principal
from repwise_api.database import request_session
from repwise_api.errors import ApiError
from repwise_api.models import (
    AccountDeletionRequest,
    AnalysisArtifact,
    AnalysisJob,
    AnalysisTombstone,
    AnnotationAssignment,
    AuthSession,
    DeletionRequest,
    ExportJob,
    MediaUpload,
    OperationalAlert,
    ReportFeedback,
    ResearchConsent,
    SupportAccessGrant,
    UserAccount,
)
from repwise_api.storage import ObjectStorage

router = APIRouter(prefix="/v1", tags=["privacy"])


class ExportAnalysis(BaseModel):
    id: uuid.UUID
    status: str
    rule_version: str
    report_schema_version: str
    created_at: datetime


class ExportFeedback(BaseModel):
    id: uuid.UUID
    analysis_id: uuid.UUID
    category: str
    rule_version: str
    created_at: datetime


class AccountExport(BaseModel):
    export_id: uuid.UUID
    generated_at: datetime
    account_id: uuid.UUID
    analyses: list[ExportAnalysis]
    feedback: list[ExportFeedback]


class AccountDeletionResponse(BaseModel):
    request_id: uuid.UUID
    status: str


def privacy_storage(request: Request) -> ObjectStorage:
    return cast(ObjectStorage, request.app.state.object_storage)


@router.post("/exports/account", response_model=AccountExport)
async def export_account(  # pragma: no cover - ASGI integration covered
    principal: Annotated[Principal, Depends(authenticated_principal)],
    db: Annotated[AsyncSession, Depends(request_session)],
) -> AccountExport:
    analyses = list(
        await db.scalars(
            select(AnalysisJob)
            .where(
                AnalysisJob.owner_id == principal.user_id,
                AnalysisJob.deleted_at.is_(None),
            )
            .order_by(AnalysisJob.created_at.asc())
        )
    )
    feedback = list(
        await db.scalars(
            select(ReportFeedback)
            .where(ReportFeedback.owner_id == principal.user_id)
            .order_by(ReportFeedback.created_at.asc())
        )
    )
    export = ExportJob(owner_id=principal.user_id)
    db.add(export)
    await db.commit()
    return AccountExport(
        export_id=export.id,
        generated_at=export.created_at,
        account_id=principal.user_id,
        analyses=[
            ExportAnalysis(
                id=item.id,
                status=item.status,
                rule_version=item.rule_version,
                report_schema_version=item.report_schema_version,
                created_at=item.created_at,
            )
            for item in analyses
        ],
        feedback=[
            ExportFeedback(
                id=item.id,
                analysis_id=item.analysis_id,
                category=item.category.value,
                rule_version=item.rule_version,
                created_at=item.created_at,
            )
            for item in feedback
        ],
    )


@router.post("/exports/reports/{analysis_id}", response_model=ExportAnalysis)
async def export_report(  # pragma: no cover - ASGI integration covered
    analysis_id: uuid.UUID,
    principal: Annotated[Principal, Depends(authenticated_principal)],
    db: Annotated[AsyncSession, Depends(request_session)],
) -> ExportAnalysis:
    analysis = await db.get(AnalysisJob, analysis_id)
    if not analysis or analysis.owner_id != principal.user_id or analysis.deleted_at:
        raise ApiError(404, "analysis_not_found", "Analysis not found.")
    return ExportAnalysis(
        id=analysis.id,
        status=analysis.status,
        rule_version=analysis.rule_version,
        report_schema_version=analysis.report_schema_version,
        created_at=analysis.created_at,
    )


@router.delete("/privacy/account", response_model=AccountDeletionResponse)
async def delete_account(  # pragma: no cover - ASGI integration covered
    principal: Annotated[Principal, Depends(authenticated_principal)],
    db: Annotated[AsyncSession, Depends(request_session)],
    storage: Annotated[ObjectStorage, Depends(privacy_storage)],
) -> AccountDeletionResponse:
    existing = await db.scalar(
        select(AccountDeletionRequest).where(
            AccountDeletionRequest.owner_id == principal.user_id
        )
    )
    if existing and existing.status == "completed":
        return AccountDeletionResponse(request_id=existing.id, status="completed")
    request = existing or AccountDeletionRequest(owner_id=principal.user_id)
    if existing is None:
        db.add(request)
    analyses = list(
        await db.scalars(
            select(AnalysisJob).where(AnalysisJob.owner_id == principal.user_id)
        )
    )
    analysis_ids = [analysis.id for analysis in analyses]
    uploads = list(
        await db.scalars(
            select(MediaUpload).where(MediaUpload.owner_id == principal.user_id)
        )
    )
    artifacts = (
        list(
            await db.scalars(
                select(AnalysisArtifact).where(
                    AnalysisArtifact.analysis_id.in_(analysis_ids)
                )
            )
        )
        if analysis_ids
        else []
    )
    now = datetime.now(UTC)
    for analysis in analyses:
        analysis.deleted_at = now
        if await db.get(AnalysisTombstone, analysis.id) is None:
            db.add(
                AnalysisTombstone(
                    analysis_id=analysis.id,
                    owner_id=principal.user_id,
                    deleted_at=now,
                )
            )
    await db.commit()

    keys = {upload.object_key for upload in uploads}
    keys.update(artifact.object_key for artifact in artifacts)
    keys.update(
        f"analyses/{analysis_id}/report.v1.json" for analysis_id in analysis_ids
    )
    for key in keys:
        await to_thread.run_sync(storage.remove, key)

    if analysis_ids:
        assignments = list(
            await db.scalars(
                select(AnnotationAssignment.id).where(
                    AnnotationAssignment.analysis_id.in_(analysis_ids)
                )
            )
        )
        if assignments:
            from repwise_api.models import Adjudication, Annotation, ReleaseApproval

            adjudications = list(
                await db.scalars(
                    select(Adjudication.id).where(
                        Adjudication.assignment_id.in_(assignments)
                    )
                )
            )
            if adjudications:
                await db.execute(
                    delete(ReleaseApproval).where(
                        ReleaseApproval.adjudication_id.in_(adjudications)
                    )
                )
            await db.execute(
                delete(Adjudication).where(Adjudication.assignment_id.in_(assignments))
            )
            await db.execute(
                delete(Annotation).where(Annotation.assignment_id.in_(assignments))
            )
        for model in (
            AnnotationAssignment,
            ResearchConsent,
            ReportFeedback,
            SupportAccessGrant,
            OperationalAlert,
            DeletionRequest,
            AnalysisArtifact,
        ):
            await db.execute(delete(model).where(model.analysis_id.in_(analysis_ids)))
        await db.execute(delete(AnalysisJob).where(AnalysisJob.id.in_(analysis_ids)))
    await db.execute(
        delete(MediaUpload).where(MediaUpload.owner_id == principal.user_id)
    )
    await db.execute(delete(ExportJob).where(ExportJob.owner_id == principal.user_id))
    await db.execute(
        delete(AuthSession).where(AuthSession.user_id == principal.user_id)
    )
    await db.execute(
        update(UserAccount)
        .where(UserAccount.id == principal.user_id)
        .values(
            external_subject=f"deleted:{principal.user_id}",
            email=f"deleted-{principal.user_id}@invalid.local",
            disabled_at=now,
        )
    )
    request.status = "completed"
    request.completed_at = now
    await db.commit()
    return AccountDeletionResponse(request_id=request.id, status="completed")
