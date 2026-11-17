from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from repwise_api.annotations import audit
from repwise_api.auth import Principal, require_roles
from repwise_api.database import request_session
from repwise_api.errors import ApiError
from repwise_api.models import (
    FeatureFlag,
    ReleaseApproval,
    ReleasePromotion,
    UserRole,
)

router = APIRouter(prefix="/v1/admin/release-controls", tags=["release controls"])


class FlagRequest(BaseModel):
    check_id: str = Field(min_length=1, max_length=128)
    enabled: bool = False
    cohort_percent: int = Field(default=0, ge=0, le=100)


class PromotionRequest(BaseModel):
    rule_version: str = Field(min_length=1, max_length=64)
    approval_id: uuid.UUID
    cohort_percent: int = Field(ge=1, le=100)


class FlagResponse(BaseModel):
    id: uuid.UUID
    check_id: str
    enabled: bool
    cohort_percent: int
    active_version: str | None
    last_known_good_version: str | None


def flag_response(flag: FeatureFlag) -> FlagResponse:
    return FlagResponse(
        id=flag.id,
        check_id=flag.check_id,
        enabled=flag.enabled,
        cohort_percent=flag.cohort_percent,
        active_version=flag.active_version,
        last_known_good_version=flag.last_known_good_version,
    )


def in_canary_cohort(user_id: uuid.UUID, check_id: str, percent: int) -> bool:
    if percent <= 0:
        return False
    if percent >= 100:
        return True
    digest = hashlib.sha256(f"{user_id}:{check_id}".encode()).digest()
    return int.from_bytes(digest[:8], "big") % 100 < percent


@router.post("", response_model=FlagResponse)
async def configure_flag(  # pragma: no cover - ASGI integration covered
    body: FlagRequest,
    principal: Annotated[Principal, Depends(require_roles(UserRole.ADMIN))],
    db: Annotated[AsyncSession, Depends(request_session)],
) -> FlagResponse:
    flag = await db.scalar(
        select(FeatureFlag).where(FeatureFlag.check_id == body.check_id)
    )
    if flag is None:
        flag = FeatureFlag(check_id=body.check_id)
        db.add(flag)
        await db.flush()
    flag.enabled = body.enabled
    flag.cohort_percent = body.cohort_percent
    flag.updated_at = datetime.now(UTC)
    audit(db, principal, "release.flag_configured", "feature_flag", flag.id)
    await db.commit()
    return flag_response(flag)


@router.post("/{check_id}/promote", response_model=FlagResponse)
async def promote(  # pragma: no cover - ASGI integration covered
    check_id: str,
    body: PromotionRequest,
    principal: Annotated[Principal, Depends(require_roles(UserRole.ADMIN))],
    db: Annotated[AsyncSession, Depends(request_session)],
) -> FlagResponse:
    flag = await db.scalar(
        select(FeatureFlag).where(FeatureFlag.check_id == check_id).with_for_update()
    )
    approval = await db.get(ReleaseApproval, body.approval_id)
    if not flag:
        raise ApiError(404, "feature_flag_not_found", "Feature flag not found.")
    if (
        not approval
        or approval.decision != "approved"
        or approval.rule_version != body.rule_version
    ):
        raise ApiError(
            409, "release_approval_required", "Matching approval is required."
        )
    if flag.active_version and flag.active_version != body.rule_version:
        flag.last_known_good_version = flag.active_version
    elif not flag.last_known_good_version:
        flag.last_known_good_version = body.rule_version
    flag.active_version = body.rule_version
    flag.enabled = True
    flag.cohort_percent = body.cohort_percent
    flag.updated_at = datetime.now(UTC)
    db.add(
        ReleasePromotion(
            feature_flag_id=flag.id,
            rule_version=body.rule_version,
            approval_id=approval.id,
            action="promoted",
            cohort_percent=body.cohort_percent,
            actor_id=principal.user_id,
        )
    )
    audit(db, principal, "release.promoted", "feature_flag", flag.id)
    await db.commit()
    return flag_response(flag)


@router.post("/{check_id}/disable", response_model=FlagResponse)
async def disable(  # pragma: no cover - ASGI integration covered
    check_id: str,
    principal: Annotated[Principal, Depends(require_roles(UserRole.ADMIN))],
    db: Annotated[AsyncSession, Depends(request_session)],
) -> FlagResponse:
    flag = await db.scalar(select(FeatureFlag).where(FeatureFlag.check_id == check_id))
    if not flag:
        raise ApiError(404, "feature_flag_not_found", "Feature flag not found.")
    flag.enabled = False
    flag.updated_at = datetime.now(UTC)
    db.add(
        ReleasePromotion(
            feature_flag_id=flag.id,
            rule_version=flag.active_version or "none",
            action="disabled",
            cohort_percent=0,
            actor_id=principal.user_id,
        )
    )
    audit(db, principal, "release.disabled", "feature_flag", flag.id)
    await db.commit()
    return flag_response(flag)


@router.post("/{check_id}/rollback", response_model=FlagResponse)
async def rollback(  # pragma: no cover - ASGI integration covered
    check_id: str,
    principal: Annotated[Principal, Depends(require_roles(UserRole.ADMIN))],
    db: Annotated[AsyncSession, Depends(request_session)],
) -> FlagResponse:
    flag = await db.scalar(select(FeatureFlag).where(FeatureFlag.check_id == check_id))
    if not flag or not flag.last_known_good_version:
        raise ApiError(
            409, "rollback_unavailable", "No last-known-good version exists."
        )
    flag.active_version = flag.last_known_good_version
    flag.enabled = True
    flag.cohort_percent = 100
    flag.updated_at = datetime.now(UTC)
    db.add(
        ReleasePromotion(
            feature_flag_id=flag.id,
            rule_version=flag.active_version,
            action="rolled_back",
            cohort_percent=100,
            actor_id=principal.user_id,
        )
    )
    audit(db, principal, "release.rolled_back", "feature_flag", flag.id)
    await db.commit()
    return flag_response(flag)
