from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated, Literal, cast

from fastapi import APIRouter, Depends, Request, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from repwise_api.auth import Principal, authenticated_principal, require_roles
from repwise_api.database import request_session
from repwise_api.errors import ApiError
from repwise_api.models import (
    Adjudication,
    AnalysisJob,
    Annotation,
    AnnotationAssignment,
    AuditEvent,
    MediaUpload,
    ReleaseApproval,
    ResearchConsent,
    UserAccount,
    UserRole,
)
from repwise_api.storage import ObjectStorage

router = APIRouter(prefix="/v1", tags=["annotation review"])


class ConsentRequest(BaseModel):
    purpose: str = Field(min_length=3, max_length=255)


class AssignmentRequest(BaseModel):
    analysis_id: uuid.UUID
    reviewer_id: uuid.UUID


class AnnotationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    labels: dict[str, object]
    uncertain: bool = False


class AdjudicationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decision: dict[str, object]


class ReleaseRequest(BaseModel):
    rule_version: str = Field(min_length=1, max_length=64)
    adjudication_id: uuid.UUID
    decision: Literal["approved", "rejected"]


class IdentifierResponse(BaseModel):
    id: uuid.UUID
    status: str


class AssignmentResponse(BaseModel):
    id: uuid.UUID
    analysis_id: uuid.UUID
    status: str


class AssetResponse(BaseModel):
    analysis_id: uuid.UUID
    url: str
    expires_in: int = 300


def annotation_storage(request: Request) -> ObjectStorage:
    return cast(ObjectStorage, request.app.state.object_storage)


def audit(
    db: AsyncSession,
    principal: Principal,
    action: str,
    resource_type: str,
    resource_id: uuid.UUID,
    details: dict[str, object] | None = None,
) -> None:
    db.add(
        AuditEvent(
            actor_id=principal.user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details or {},
        )
    )


async def assigned_and_consented(  # pragma: no cover - ASGI integration covered
    db: AsyncSession, assignment_id: uuid.UUID, reviewer_id: uuid.UUID
) -> tuple[AnnotationAssignment, AnalysisJob]:
    assignment = await db.get(AnnotationAssignment, assignment_id)
    if not assignment or assignment.reviewer_id != reviewer_id:
        raise ApiError(404, "assignment_not_found", "Assignment not found.")
    consent = await db.get(ResearchConsent, assignment.consent_id)
    analysis = await db.get(AnalysisJob, assignment.analysis_id)
    if not consent or consent.revoked_at or not analysis or analysis.deleted_at:
        raise ApiError(
            410, "asset_unavailable", "Consent or asset is no longer active."
        )
    return assignment, analysis


@router.post(
    "/privacy/analyses/{analysis_id}/consent", response_model=IdentifierResponse
)
async def grant_consent(  # pragma: no cover - ASGI integration covered
    analysis_id: uuid.UUID,
    body: ConsentRequest,
    principal: Annotated[Principal, Depends(authenticated_principal)],
    db: Annotated[AsyncSession, Depends(request_session)],
) -> IdentifierResponse:
    analysis = await db.get(AnalysisJob, analysis_id)
    if not analysis or analysis.owner_id != principal.user_id or analysis.deleted_at:
        raise ApiError(404, "analysis_not_found", "Analysis not found.")
    existing = await db.scalar(
        select(ResearchConsent).where(ResearchConsent.analysis_id == analysis_id)
    )
    if existing and not existing.revoked_at:
        return IdentifierResponse(id=existing.id, status="active")
    if existing:
        consent = existing
        consent.purpose = body.purpose
        consent.revoked_at = None
    else:
        consent = ResearchConsent(
            analysis_id=analysis_id, owner_id=principal.user_id, purpose=body.purpose
        )
        db.add(consent)
    await db.flush()
    audit(db, principal, "consent.granted", "research_consent", consent.id)
    await db.commit()
    return IdentifierResponse(id=consent.id, status="active")


@router.post("/admin/annotation-assignments", response_model=AssignmentResponse)
async def create_assignment(  # pragma: no cover - ASGI integration covered
    body: AssignmentRequest,
    principal: Annotated[Principal, Depends(require_roles(UserRole.ADMIN))],
    db: Annotated[AsyncSession, Depends(request_session)],
) -> AssignmentResponse:
    consent = await db.scalar(
        select(ResearchConsent).where(ResearchConsent.analysis_id == body.analysis_id)
    )
    analysis = await db.get(AnalysisJob, body.analysis_id)
    reviewer = await db.get(UserAccount, body.reviewer_id)
    if not consent or consent.revoked_at or not analysis or analysis.deleted_at:
        raise ApiError(409, "consent_required", "Active consent is required.")
    if not reviewer or reviewer.role is not UserRole.REVIEWER or reviewer.disabled_at:
        raise ApiError(422, "invalid_reviewer", "An active reviewer is required.")
    assignment = AnnotationAssignment(
        analysis_id=analysis.id,
        consent_id=consent.id,
        reviewer_id=reviewer.id,
        assigned_by=principal.user_id,
    )
    db.add(assignment)
    await db.flush()
    audit(db, principal, "annotation.assigned", "annotation_assignment", assignment.id)
    await db.commit()
    return AssignmentResponse(
        id=assignment.id, analysis_id=analysis.id, status="assigned"
    )


@router.delete(
    "/privacy/analyses/{analysis_id}/consent", response_model=IdentifierResponse
)
async def revoke_consent(  # pragma: no cover - ASGI integration covered
    analysis_id: uuid.UUID,
    principal: Annotated[Principal, Depends(authenticated_principal)],
    db: Annotated[AsyncSession, Depends(request_session)],
) -> IdentifierResponse:
    consent = await db.scalar(
        select(ResearchConsent).where(
            ResearchConsent.analysis_id == analysis_id,
            ResearchConsent.owner_id == principal.user_id,
        )
    )
    if not consent:
        raise ApiError(404, "consent_not_found", "Consent not found.")
    if not consent.revoked_at:
        consent.revoked_at = datetime.now(UTC)
        audit(db, principal, "consent.revoked", "research_consent", consent.id)
        await db.commit()
    return IdentifierResponse(id=consent.id, status="revoked")


@router.get("/review/assignments", response_model=list[AssignmentResponse])
async def reviewer_assignments(  # pragma: no cover - ASGI integration covered
    principal: Annotated[Principal, Depends(require_roles(UserRole.REVIEWER))],
    db: Annotated[AsyncSession, Depends(request_session)],
) -> list[AssignmentResponse]:
    assignments = await db.scalars(
        select(AnnotationAssignment).where(
            AnnotationAssignment.reviewer_id == principal.user_id
        )
    )
    visible: list[AssignmentResponse] = []
    for assignment in assignments:
        try:
            await assigned_and_consented(db, assignment.id, principal.user_id)
        except ApiError:
            continue
        visible.append(
            AssignmentResponse(
                id=assignment.id,
                analysis_id=assignment.analysis_id,
                status=assignment.status,
            )
        )
    return visible


@router.get("/review/assignments/{assignment_id}/asset", response_model=AssetResponse)
async def assigned_asset(  # pragma: no cover - ASGI integration covered
    assignment_id: uuid.UUID,
    principal: Annotated[Principal, Depends(require_roles(UserRole.REVIEWER))],
    db: Annotated[AsyncSession, Depends(request_session)],
    storage: Annotated[ObjectStorage, Depends(annotation_storage)],
) -> AssetResponse:
    assignment, analysis = await assigned_and_consented(
        db, assignment_id, principal.user_id
    )
    upload = await db.get(MediaUpload, analysis.upload_id)
    if not upload or analysis.raw_expired_at:
        raise ApiError(410, "asset_unavailable", "The review asset has expired.")
    audit(
        db,
        principal,
        "annotation.asset_accessed",
        "annotation_assignment",
        assignment.id,
    )
    await db.commit()
    return AssetResponse(
        analysis_id=analysis.id, url=storage.presigned_get(upload.object_key)
    )


@router.post(
    "/review/assignments/{assignment_id}/annotations",
    response_model=IdentifierResponse,
    status_code=status.HTTP_201_CREATED,
)
async def submit_annotation(  # pragma: no cover - ASGI integration covered
    assignment_id: uuid.UUID,
    body: AnnotationRequest,
    principal: Annotated[Principal, Depends(require_roles(UserRole.REVIEWER))],
    db: Annotated[AsyncSession, Depends(request_session)],
) -> IdentifierResponse:
    assignment, _ = await assigned_and_consented(db, assignment_id, principal.user_id)
    annotation = Annotation(
        assignment_id=assignment.id,
        reviewer_id=principal.user_id,
        labels=body.labels,
        uncertain=body.uncertain,
    )
    db.add(annotation)
    assignment.status = "annotated"
    await db.flush()
    audit(db, principal, "annotation.submitted", "annotation", annotation.id)
    await db.commit()
    return IdentifierResponse(id=annotation.id, status="annotated")


@router.post(
    "/admin/annotation-assignments/{assignment_id}/adjudicate",
    response_model=IdentifierResponse,
)
async def adjudicate(  # pragma: no cover - ASGI integration covered
    assignment_id: uuid.UUID,
    body: AdjudicationRequest,
    principal: Annotated[Principal, Depends(require_roles(UserRole.ADMIN))],
    db: Annotated[AsyncSession, Depends(request_session)],
) -> IdentifierResponse:
    assignment = await db.get(AnnotationAssignment, assignment_id)
    annotation = await db.scalar(
        select(Annotation).where(Annotation.assignment_id == assignment_id)
    )
    if not assignment or not annotation:
        raise ApiError(409, "annotation_required", "Submitted annotation is required.")
    adjudication = Adjudication(
        assignment_id=assignment.id,
        adjudicator_id=principal.user_id,
        decision=body.decision,
    )
    db.add(adjudication)
    assignment.status = "adjudicated"
    await db.flush()
    audit(db, principal, "annotation.adjudicated", "adjudication", adjudication.id)
    await db.commit()
    return IdentifierResponse(id=adjudication.id, status="adjudicated")


@router.post("/admin/releases", response_model=IdentifierResponse)
async def approve_release(  # pragma: no cover - ASGI integration covered
    body: ReleaseRequest,
    principal: Annotated[Principal, Depends(require_roles(UserRole.ADMIN))],
    db: Annotated[AsyncSession, Depends(request_session)],
) -> IdentifierResponse:
    adjudication = await db.get(Adjudication, body.adjudication_id)
    if not adjudication:
        raise ApiError(409, "adjudication_required", "Adjudication is required.")
    approval = ReleaseApproval(
        rule_version=body.rule_version,
        adjudication_id=adjudication.id,
        approver_id=principal.user_id,
        decision=body.decision,
    )
    db.add(approval)
    await db.flush()
    audit(db, principal, "release.decided", "release_approval", approval.id)
    await db.commit()
    return IdentifierResponse(id=approval.id, status=body.decision)
