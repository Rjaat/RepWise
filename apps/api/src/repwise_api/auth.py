from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any, cast

from fastapi import Depends, Header, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from repwise_api.database import request_session
from repwise_api.errors import ApiError
from repwise_api.models import AuthSession, UserAccount, UserRole
from repwise_api.settings import Settings


@dataclass(frozen=True)
class Principal:
    user_id: uuid.UUID
    session_id: uuid.UUID
    role: UserRole


def _encode(payload: dict[str, Any], secret: str) -> str:
    body = base64.urlsafe_b64encode(
        json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
    ).rstrip(b"=")
    signature = base64.urlsafe_b64encode(
        hmac.new(secret.encode(), body, hashlib.sha256).digest()
    ).rstrip(b"=")
    return f"{body.decode()}.{signature.decode()}"


def _decode(token: str, secret: str) -> dict[str, Any]:
    try:
        body_text, signature_text = token.split(".", 1)
        body = body_text.encode()
        expected = base64.urlsafe_b64encode(
            hmac.new(secret.encode(), body, hashlib.sha256).digest()
        ).rstrip(b"=")
        if not hmac.compare_digest(expected, signature_text.encode()):
            raise ValueError
        payload = json.loads(base64.urlsafe_b64decode(body + b"=" * (-len(body) % 4)))
        if not isinstance(payload, dict) or int(payload["exp"]) <= int(time.time()):
            raise ValueError
        return payload
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        raise ApiError(
            401, "invalid_identity", "Authentication token is invalid or expired."
        ) from error


def create_identity_assertion(
    subject: str, email: str, verified: bool, settings: Settings, ttl_seconds: int = 60
) -> str:
    """Create an assertion for identity-provider adapters and integration tests."""
    return _encode(
        {
            "typ": "identity",
            "sub": subject,
            "email": email,
            "email_verified": verified,
            "iss": settings.auth_issuer,
            "aud": settings.auth_audience,
            "exp": int(time.time()) + ttl_seconds,
        },
        settings.identity_assertion_secret,
    )


def verify_identity_assertion(token: str, settings: Settings) -> dict[str, Any]:
    claims = _decode(token, settings.identity_assertion_secret)
    if (
        (claims.get("typ"), claims.get("iss"), claims.get("aud"))
        != ("identity", settings.auth_issuer, settings.auth_audience)
        or not claims.get("sub")
        or not claims.get("email")
    ):
        raise ApiError(401, "invalid_identity", "Identity assertion is invalid.")
    if claims.get("email_verified") is not True:
        raise ApiError(
            403, "unverified_account", "A verified email account is required."
        )
    return claims


def refresh_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def issue_access_token(
    user: UserAccount, auth_session: AuthSession, settings: Settings
) -> str:
    return _encode(
        {
            "typ": "access",
            "sub": str(user.id),
            "sid": str(auth_session.id),
            "role": user.role.value,
            "iss": settings.auth_issuer,
            "aud": settings.auth_audience,
            "exp": int(time.time()) + settings.access_token_ttl_seconds,
        },
        settings.auth_signing_secret,
    )


def new_session(
    user_id: uuid.UUID, settings: Settings, rotated_from: uuid.UUID | None = None
) -> tuple[AuthSession, str]:
    refresh = secrets.token_urlsafe(48)
    return AuthSession(
        user_id=user_id,
        refresh_token_hash=refresh_hash(refresh),
        expires_at=datetime.now(UTC)
        + timedelta(seconds=settings.refresh_token_ttl_seconds),
        rotated_from_id=rotated_from,
    ), refresh


# SQLAlchemy's greenlet handoff is integration-tested through ASGI in test_auth.py,
# but Python 3.13 coverage cannot trace the continuation after the database await.
async def authenticated_principal(  # pragma: no cover
    request: Request,
    session: Annotated[AsyncSession, Depends(request_session)],
    authorization: Annotated[str | None, Header()] = None,
) -> Principal:
    if not authorization or not authorization.startswith("Bearer "):
        raise ApiError(401, "authentication_required", "A bearer token is required.")
    token = authorization.removeprefix("Bearer ").strip()
    settings: Settings = request.app.state.settings
    if settings.allow_legacy_bearer_identity:
        try:
            return Principal(uuid.UUID(token), uuid.UUID(int=0), UserRole.USER)
        except ValueError:
            pass
    claims = _decode(token, settings.auth_signing_secret)
    if (claims.get("typ"), claims.get("iss"), claims.get("aud")) != (
        "access",
        settings.auth_issuer,
        settings.auth_audience,
    ):
        raise ApiError(401, "invalid_identity", "Authentication token is invalid.")
    try:
        user_id, session_id = uuid.UUID(claims["sub"]), uuid.UUID(claims["sid"])
        role = UserRole(claims["role"])
    except (KeyError, ValueError) as error:
        raise ApiError(
            401, "invalid_identity", "Authentication token is invalid."
        ) from error
    auth_session = await session.get(AuthSession, session_id)
    user = await session.get(UserAccount, user_id)
    now = datetime.now(UTC)
    if (
        not auth_session
        or auth_session.user_id != user_id
        or auth_session.revoked_at
        or auth_session.expires_at.replace(tzinfo=UTC) < now
    ):
        raise ApiError(401, "session_revoked", "This session is no longer active.")
    if not user or user.disabled_at or not user.email_verified or user.role != role:
        raise ApiError(
            403, "account_unavailable", "This account cannot access RepWise."
        )
    return Principal(user_id, session_id, role)


async def authenticated_user(
    principal: Annotated[Principal, Depends(authenticated_principal)],
) -> uuid.UUID:
    return principal.user_id


def require_roles(*roles: UserRole) -> Callable[..., Awaitable[Principal]]:
    async def authorized(
        principal: Annotated[Principal, Depends(authenticated_principal)],
    ) -> Principal:
        if principal.role not in roles:
            raise ApiError(
                status.HTTP_403_FORBIDDEN,
                "insufficient_role",
                "Your role cannot access this resource.",
            )
        return principal

    return authorized


async def session_by_refresh(session: AsyncSession, refresh: str) -> AuthSession | None:
    return cast(
        AuthSession | None,
        await session.scalar(
            select(AuthSession).where(
                AuthSession.refresh_token_hash == refresh_hash(refresh)
            ).with_for_update()
        ),
    )
