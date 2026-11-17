from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from repwise_api.auth import authenticated_user
from repwise_api.database import request_session
from repwise_api.models import AnalysisJob
from repwise_api.retention import owned_analysis

router = APIRouter(prefix="/v1/progress", tags=["progress"])

MINIMUM_COMPARISON_COVERAGE = 0.8


class ProgressComparisonRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    baseline_id: uuid.UUID
    comparison_id: uuid.UUID


class SessionContext(BaseModel):
    analysis_id: uuid.UUID
    exercise: str
    variant: str
    view: str
    report_schema_version: str
    rule_version: str
    assessment_coverage: float | None
    rep_count: int | None


class ProgressComparisonResponse(BaseModel):
    comparable: bool
    reasons: list[str]
    baseline: SessionContext
    comparison: SessionContext
    rep_count_delta: int | None


def session_context(job: AnalysisJob) -> SessionContext:
    return SessionContext(
        analysis_id=job.id,
        exercise=job.exercise,
        variant=job.variant,
        view=job.view,
        report_schema_version=job.report_schema_version,
        rule_version=job.rule_version,
        assessment_coverage=job.assessment_coverage,
        rep_count=job.rep_count,
    )


def incompatibility_reasons(
    baseline: AnalysisJob, comparison: AnalysisJob
) -> list[str]:
    reasons: list[str] = []
    for field in (
        "exercise",
        "variant",
        "view",
        "report_schema_version",
        "rule_version",
    ):
        if getattr(baseline, field) != getattr(comparison, field):
            reasons.append(f"{field}_mismatch")
    if baseline.status != "completed" or comparison.status != "completed":
        reasons.append("analysis_incomplete")
    if baseline.rep_count is None or comparison.rep_count is None:
        reasons.append("rep_count_unavailable")
    if baseline.assessment_coverage is None or comparison.assessment_coverage is None:
        reasons.append("coverage_unavailable")
    elif (
        baseline.assessment_coverage < MINIMUM_COMPARISON_COVERAGE
        or comparison.assessment_coverage < MINIMUM_COMPARISON_COVERAGE
    ):
        reasons.append("coverage_below_threshold")
    return reasons


@router.post("/compare", response_model=ProgressComparisonResponse)
async def compare_progress(  # pragma: no cover - ASGI integration covered
    body: ProgressComparisonRequest,
    owner_id: Annotated[uuid.UUID, Depends(authenticated_user)],
    db: Annotated[AsyncSession, Depends(request_session)],
) -> ProgressComparisonResponse:
    baseline = await owned_analysis(db, body.baseline_id, owner_id)
    comparison = await owned_analysis(db, body.comparison_id, owner_id)
    reasons = incompatibility_reasons(baseline, comparison)
    return ProgressComparisonResponse(
        comparable=not reasons,
        reasons=reasons,
        baseline=session_context(baseline),
        comparison=session_context(comparison),
        rep_count_delta=(
            comparison.rep_count - baseline.rep_count
            if not reasons
            and comparison.rep_count is not None
            and baseline.rep_count is not None
            else None
        ),
    )
