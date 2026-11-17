from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, Request, Response
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from repwise_api.auth import (
    Principal,
    authenticated_principal,
    issue_access_token,
    new_session,
    require_roles,
    session_by_refresh,
    verify_identity_assertion,
)
from repwise_api.database import request_session
from repwise_api.errors import ApiError
from repwise_api.models import AuthSession, UserAccount, UserRole
from repwise_api.settings import Settings

router = APIRouter(prefix="/v1", tags=["authentication"])
REFRESH_COOKIE = "repwise_refresh"


class ExchangeRequest(BaseModel):
    identity_assertion: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class SessionStatus(BaseModel):
    user_id: str
    role: UserRole


def _set_refresh(response: Response, token: str, settings: Settings) -> None:
    response.set_cookie(
        REFRESH_COOKIE,
        token,
        httponly=True,
        secure=settings.env != "development",
        samesite="strict",
        max_age=settings.refresh_token_ttl_seconds,
        path="/v1/auth",
    )


@router.post("/auth/exchange", response_model=TokenResponse)
async def exchange(  # pragma: no cover - exercised through ASGI across greenlet awaits
    body: ExchangeRequest,
    request: Request,
    response: Response,
    db: Annotated[AsyncSession, Depends(request_session)],
) -> TokenResponse:
    settings: Settings = request.app.state.settings
    claims = verify_identity_assertion(body.identity_assertion, settings)
    user = await db.scalar(
        select(UserAccount).where(UserAccount.external_subject == claims["sub"])
    )
    email = str(claims["email"]).strip().lower()
    if user is None:
        user = UserAccount(
            external_subject=claims["sub"], email=email, email_verified=True
        )
        db.add(user)
        await db.flush()
    elif user.disabled_at:
        raise ApiError(
            403, "account_unavailable", "This account cannot access RepWise."
        )
    else:
        user.email, user.email_verified = email, True
    auth_session, refresh = new_session(user.id, settings)
    db.add(auth_session)
    await db.commit()
    _set_refresh(response, refresh, settings)
    return TokenResponse(
        access_token=issue_access_token(user, auth_session, settings),
        expires_in=settings.access_token_ttl_seconds,
    )


@router.post("/auth/refresh", response_model=TokenResponse)
async def refresh(  # pragma: no cover - exercised through ASGI across greenlet awaits
    request: Request,
    response: Response,
    db: Annotated[AsyncSession, Depends(request_session)],
    repwise_refresh: Annotated[str | None, Cookie()] = None,
) -> TokenResponse:
    if not repwise_refresh:
        raise ApiError(401, "refresh_required", "A refresh session is required.")
    old = await session_by_refresh(db, repwise_refresh)
    now = datetime.now(UTC)
    if not old or old.revoked_at or old.expires_at.replace(tzinfo=UTC) < now:
        raise ApiError(
            401, "session_revoked", "This refresh session is no longer active."
        )
    user = await db.get(UserAccount, old.user_id)
    if not user or user.disabled_at or not user.email_verified:
        raise ApiError(
            403, "account_unavailable", "This account cannot access RepWise."
        )
    old.revoked_at = now
    replacement, refresh_token = new_session(
        user.id, request.app.state.settings, old.id
    )
    db.add(replacement)
    await db.commit()
    _set_refresh(response, refresh_token, request.app.state.settings)
    return TokenResponse(
        access_token=issue_access_token(user, replacement, request.app.state.settings),
        expires_in=request.app.state.settings.access_token_ttl_seconds,
    )


@router.post("/auth/logout", status_code=204)
async def logout(  # pragma: no cover - exercised through ASGI across greenlet awaits
    principal: Annotated[Principal, Depends(authenticated_principal)],
    db: Annotated[AsyncSession, Depends(request_session)],
    response: Response,
) -> None:
    auth_session = await db.get(AuthSession, principal.session_id)
    if auth_session and not auth_session.revoked_at:
        auth_session.revoked_at = datetime.now(UTC)
        await db.commit()
    response.delete_cookie(REFRESH_COOKIE, path="/v1/auth")


@router.post("/auth/logout-all", status_code=204)
async def logout_all(  # pragma: no cover - ASGI integration covered
    principal: Annotated[Principal, Depends(authenticated_principal)],
    db: Annotated[AsyncSession, Depends(request_session)],
    response: Response,
) -> None:
    await db.execute(
        update(AuthSession)
        .where(
            AuthSession.user_id == principal.user_id, AuthSession.revoked_at.is_(None)
        )
        .values(revoked_at=datetime.now(UTC))
    )
    await db.commit()
    response.delete_cookie(REFRESH_COOKIE, path="/v1/auth")


@router.get("/admin/auth-status", response_model=SessionStatus, tags=["administration"])
async def admin_auth_status(
    principal: Annotated[Principal, Depends(require_roles(UserRole.ADMIN))],
) -> SessionStatus:
    return SessionStatus(user_id=str(principal.user_id), role=principal.role)
