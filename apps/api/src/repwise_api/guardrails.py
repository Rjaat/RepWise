from __future__ import annotations

import uuid
from datetime import UTC, datetime, time, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
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
    resets_at: datetime
    daily_used_units: int
    daily_limit_units: int
    daily_remaining_units: int
    daily_resets_at: datetime
    payments_enabled: bool


def quota_windows(now: datetime) -> tuple[datetime, datetime, datetime]:
    current = now.astimezone(UTC)
    cycle_end = current + timedelta(days=30)
    daily_reset = datetime.combine(current.date() + timedelta(days=1), time(), UTC)
    return current, cycle_end, daily_reset


def timezone_aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=UTC)


async def consume_analysis_usage(
    db: AsyncSession,
    *,
    owner_id: uuid.UUID,
    analysis_id: uuid.UUID,
    event_key: str,
    monthly_limit_units: int,
    daily_limit_units: int,
    payments_enabled: bool,
    now: datetime | None = None,
) -> UsageLedger:
    existing = await db.scalar(
        select(UsageLedger).where(UsageLedger.event_key == event_key)
    )
    if existing:
        return existing

    current, cycle_end, daily_reset = quota_windows(now or datetime.now(UTC))
    quota = await db.scalar(
        select(BetaQuota).where(BetaQuota.owner_id == owner_id).with_for_update()
    )
    if quota is None:
        quota = BetaQuota(
            owner_id=owner_id,
            limit_units=monthly_limit_units,
            cycle_started_at=current,
            resets_at=cycle_end,
        )
        db.add(quota)
        await db.flush()
    elif timezone_aware(quota.resets_at) <= current:
        quota.used_units = 0
        quota.limit_units = monthly_limit_units
        quota.cycle_started_at = current
        quota.resets_at = cycle_end
    if quota.used_units >= quota.limit_units:
        raise ApiError(
            429,
            "monthly_analysis_limit_reached",
            "Monthly beta analysis limit reached. "
            "Try again after the shown reset time.",
        )
    day_start = datetime.combine(current.date(), time(), UTC)
    daily_used = await db.scalar(
        select(func.coalesce(func.sum(UsageLedger.units), 0)).where(
            UsageLedger.owner_id == owner_id,
            UsageLedger.created_at >= day_start,
            UsageLedger.created_at < daily_reset,
        )
    )
    if int(daily_used or 0) >= daily_limit_units:
        raise ApiError(
            429,
            "daily_analysis_limit_reached",
            "Daily beta analysis limit reached. Try again after the shown reset time.",
        )

    usage = UsageLedger(
        owner_id=owner_id,
        analysis_id=analysis_id,
        event_key=event_key,
        created_at=current,
    )
    db.add(usage)
    quota.used_units += 1
    quota.updated_at = current
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
    current, cycle_end, daily_reset = quota_windows(datetime.now(UTC))
    quota = await db.get(BetaQuota, owner_id)
    if quota is None:
        return UsageSummary(
            used_units=0,
            limit_units=settings.beta_monthly_analysis_quota,
            remaining_units=settings.beta_monthly_analysis_quota,
            resets_at=cycle_end,
            daily_used_units=0,
            daily_limit_units=settings.beta_daily_analysis_quota,
            daily_remaining_units=settings.beta_daily_analysis_quota,
            daily_resets_at=daily_reset,
            payments_enabled=settings.payments_enabled,
        )
    if timezone_aware(quota.resets_at) <= current:
        monthly_used = 0
        monthly_limit = settings.beta_monthly_analysis_quota
        monthly_reset = cycle_end
    else:
        monthly_used = quota.used_units
        monthly_limit = quota.limit_units
        monthly_reset = timezone_aware(quota.resets_at)
    day_start = datetime.combine(current.date(), time(), UTC)
    daily_used = int(
        await db.scalar(
            select(func.coalesce(func.sum(UsageLedger.units), 0)).where(
                UsageLedger.owner_id == owner_id,
                UsageLedger.created_at >= day_start,
                UsageLedger.created_at < daily_reset,
            )
        )
        or 0
    )
    return UsageSummary(
        used_units=monthly_used,
        limit_units=monthly_limit,
        remaining_units=max(0, monthly_limit - monthly_used),
        resets_at=monthly_reset,
        daily_used_units=daily_used,
        daily_limit_units=settings.beta_daily_analysis_quota,
        daily_remaining_units=max(0, settings.beta_daily_analysis_quota - daily_used),
        daily_resets_at=daily_reset,
        payments_enabled=settings.payments_enabled,
    )
