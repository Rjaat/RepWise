from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from repwise_api.auth import authenticated_user
from repwise_api.database import request_session
from repwise_api.errors import ApiError
from repwise_api.models import BetaQuota, PaymentAttempt, UsageLedger
from repwise_api.settings import Settings, get_settings

router = APIRouter(prefix="/v1/usage", tags=["usage"])


class UsageSummary(BaseModel):
    used_units: int
    limit_units: int
    remaining_units: int
    payments_enabled: bool


async def consume_analysis_usage(
    db: AsyncSession,
    *,
    owner_id: uuid.UUID,
    analysis_id: uuid.UUID,
    event_key: str,
    limit_units: int,
    payments_enabled: bool,
) -> UsageLedger:
    existing = await db.scalar(
        select(UsageLedger).where(UsageLedger.event_key == event_key)
    )
    if existing:
        return existing

    quota = await db.scalar(
        select(BetaQuota).where(BetaQuota.owner_id == owner_id).with_for_update()
    )
    if quota is None:
        quota = BetaQuota(owner_id=owner_id, limit_units=limit_units)
        db.add(quota)
        await db.flush()
    if quota.used_units >= quota.limit_units:
        raise ApiError(
            429,
            "beta_quota_exhausted",
            "Beta analysis limit reached. No usage or payment was recorded.",
        )

    usage = UsageLedger(
        owner_id=owner_id,
        analysis_id=analysis_id,
        event_key=event_key,
    )
    db.add(usage)
    quota.used_units += 1
    quota.updated_at = datetime.now(UTC)
    await db.flush()
    if payments_enabled:
        db.add(PaymentAttempt(usage_id=usage.id))
    return usage


@router.get("", response_model=UsageSummary)
async def usage_summary(  # pragma: no cover - ASGI integration covered
    owner_id: Annotated[uuid.UUID, Depends(authenticated_user)],
    db: Annotated[AsyncSession, Depends(request_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> UsageSummary:
    quota = await db.get(BetaQuota, owner_id)
    if quota is None:
        return UsageSummary(
            used_units=0,
            limit_units=0,
            remaining_units=0,
            payments_enabled=settings.payments_enabled,
        )
    return UsageSummary(
        used_units=quota.used_units,
        limit_units=quota.limit_units,
        remaining_units=max(0, quota.limit_units - quota.used_units),
        payments_enabled=settings.payments_enabled,
    )
