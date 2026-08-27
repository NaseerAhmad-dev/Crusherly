"""JWT access/refresh token issuance and verification.

Access tokens are short-lived and carry only identity claims (user id, tenant id); permissions
and roles are re-resolved from the database on every request by the security context (see
`app/security/dependencies.py`) so a permission/role change takes effect immediately rather than
waiting for token expiry. Refresh tokens are opaque-by-reference: the JWT carries a `jti` that
must match a live, non-revoked `RefreshSession` row, which is how logout/"revoke all sessions"
is implemented.
"""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any

import jwt

from app.core.config import get_settings

settings = get_settings()


class TokenType(StrEnum):
    ACCESS = "access"
    REFRESH = "refresh"


class TokenError(Exception):
    """Raised for any invalid, expired, or malformed token."""


@dataclass(frozen=True)
class DecodedToken:
    subject: str  # user id (str(UUID))
    tenant_id: str | None
    token_type: TokenType
    jti: str
    issued_at: datetime
    expires_at: datetime


def _encode(claims: dict[str, Any]) -> str:
    return jwt.encode(claims, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_access_token(*, user_id: uuid.UUID, tenant_id: uuid.UUID | None) -> str:
    now = datetime.now(UTC)
    expires = now + timedelta(minutes=settings.access_token_expire_minutes)
    claims = {
        "sub": str(user_id),
        "tenant_id": str(tenant_id) if tenant_id else None,
        "type": TokenType.ACCESS.value,
        "jti": str(uuid.uuid4()),
        "iat": now,
        "exp": expires,
    }
    return _encode(claims)


def create_refresh_token(*, user_id: uuid.UUID, tenant_id: uuid.UUID | None, jti: uuid.UUID) -> str:
    now = datetime.now(UTC)
    expires = now + timedelta(days=settings.refresh_token_expire_days)
    claims = {
        "sub": str(user_id),
        "tenant_id": str(tenant_id) if tenant_id else None,
        "type": TokenType.REFRESH.value,
        "jti": str(jti),
        "iat": now,
        "exp": expires,
    }
    return _encode(claims)


def decode_token(token: str, *, expected_type: TokenType | None = None) -> DecodedToken:
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except jwt.ExpiredSignatureError as exc:
        raise TokenError("Token has expired.") from exc
    except jwt.InvalidTokenError as exc:
        raise TokenError("Token is invalid.") from exc

    token_type_raw = payload.get("type")
    try:
        token_type = TokenType(token_type_raw)
    except ValueError as exc:
        raise TokenError("Token has an invalid type.") from exc

    if expected_type is not None and token_type is not expected_type:
        raise TokenError(f"Expected a {expected_type.value} token, got {token_type.value}.")

    subject = payload.get("sub")
    jti = payload.get("jti")
    if not subject or not jti:
        raise TokenError("Token is missing required claims.")

    return DecodedToken(
        subject=subject,
        tenant_id=payload.get("tenant_id"),
        token_type=token_type,
        jti=jti,
        issued_at=datetime.fromtimestamp(payload["iat"], tz=UTC),
        expires_at=datetime.fromtimestamp(payload["exp"], tz=UTC),
    )
