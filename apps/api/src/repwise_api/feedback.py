from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from repwise_api.auth import authenticated_user
from repwise_api.database import request_session
from repwise_api.models import FeedbackCategory, ReportFeedback
from repwise_api.retention import owned_analysis

router = APIRouter(prefix="/v1/reports", tags=["report feedback"])


class FeedbackRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: FeedbackCategory
    rep_index: int | None = Field(default=None, gt=0)
    check_id: str | None = Field(default=None, min_length=1, max_length=128)
    comment: str | None = Field(default=None, max_length=1000)

    @field_validator("comment")
    @classmethod
    def reject_urls(cls, value: str | None) -> str | None:
        if value and ("http://" in value.lower() or "https://" in value.lower()):
            raise ValueError("feedback cannot contain external media URLs")
        return value


class FeedbackResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    analysis_id: uuid.UUID
    category: FeedbackCategory
    rep_index: int | None
    check_id: str | None
    comment: str | None
    report_schema_version: str
    rule_version: str
    created_at: datetime


@router.post(
    "/{analysis_id}/feedback",
    response_model=FeedbackResponse,
    status_code=status.HTTP_201_CREATED,
)
async def submit_feedback(  # pragma: no cover - ASGI integration covered
    analysis_id: uuid.UUID,
    body: FeedbackRequest,
    owner_id: Annotated[uuid.UUID, Depends(authenticated_user)],
    db: Annotated[AsyncSession, Depends(request_session)],
) -> ReportFeedback:
    analysis = await owned_analysis(db, analysis_id, owner_id)
    feedback = ReportFeedback(
        analysis_id=analysis.id,
        owner_id=owner_id,
        category=body.category,
        rep_index=body.rep_index,
        check_id=body.check_id,
        comment=body.comment,
        report_schema_version=analysis.report_schema_version,
        rule_version=analysis.rule_version,
    )
    db.add(feedback)
    await db.commit()
    return feedback


@router.get("/{analysis_id}/feedback", response_model=list[FeedbackResponse])
async def list_feedback(  # pragma: no cover - ASGI integration covered
    analysis_id: uuid.UUID,
    owner_id: Annotated[uuid.UUID, Depends(authenticated_user)],
    db: Annotated[AsyncSession, Depends(request_session)],
) -> list[ReportFeedback]:
    await owned_analysis(db, analysis_id, owner_id)
    feedback = await db.scalars(
        select(ReportFeedback)
        .where(
            ReportFeedback.analysis_id == analysis_id,
            ReportFeedback.owner_id == owner_id,
        )
        .order_by(ReportFeedback.created_at.asc())
    )
    return list(feedback)
