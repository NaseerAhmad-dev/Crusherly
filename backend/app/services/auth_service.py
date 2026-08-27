"""Authentication: login, token refresh/rotation, logout, and password reset.

Design notes (see docs/authentication.md and ADR-003):
- Email is unique across the whole platform, so login takes only email+password, no tenant
  selector.
- Access tokens are short-lived, stateless JWTs. Refresh tokens are JWTs too, but each one is
  backed by a `RefreshSession` row keyed by `jti`; logout (or "revoke all sessions") flips
  `revoked=True` there, which refresh() checks on every use. Refresh tokens rotate on every use
  (the old jti is revoked, a new one issued) to limit the blast radius of a stolen refresh token.
"""

import logging
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from app.core.config import get_settings
from app.core.exceptions import UnauthorizedError
from app.models.audit import AuditAction
from app.models.enums import UserStatus
from app.models.password_reset import PasswordResetToken
from app.models.refresh_session import RefreshSession
from app.models.user import User
from app.repositories import password_reset_repository, refresh_session_repository, user_repository
from app.security.passwords import hash_password, verify_password
from app.security.tokens import (
    TokenError,
    TokenType,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.services import audit_service

settings = get_settings()

_MAX_FAILED_ATTEMPTS = 10


class TokenPair:
    def __init__(self, access_token: str, refresh_token: str, expires_in: int):
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.expires_in = expires_in


async def _issue_token_pair(
    session: AsyncSession, user: User, request: Request | None
) -> TokenPair:
    jti = uuid.uuid4()
    access_token = create_access_token(user_id=user.id, tenant_id=user.tenant_id)
    refresh_token = create_refresh_token(user_id=user.id, tenant_id=user.tenant_id, jti=jti)

    decoded_refresh = decode_token(refresh_token, expected_type=TokenType.REFRESH)
    refresh_session_repository.add(
        session,
        RefreshSession(
            user_id=user.id,
            jti=jti,
            expires_at=decoded_refresh.expires_at,
            ip_address=request.client.host if request and request.client else None,
            user_agent=request.headers.get("user-agent") if request else None,
        ),
    )
    return TokenPair(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.access_token_expire_minutes * 60,
    )


async def login(
    session: AsyncSession, *, email: str, password: str, request: Request | None = None
) -> tuple[User, TokenPair]:
    user = await user_repository.get_by_email(session, email)

    if user is None or not verify_password(password, user.password_hash):
        if user is not None:
            user.failed_login_attempts += 1
            if user.failed_login_attempts >= _MAX_FAILED_ATTEMPTS:
                user.status = UserStatus.LOCKED
        await audit_service.record(
            session,
            action=AuditAction.LOGIN_FAILED.value,
            resource_type="user",
            resource_id=str(user.id) if user else None,
            tenant_id=user.tenant_id if user else None,
            user_id=user.id if user else None,
            request=request,
        )
        await session.commit()
        raise UnauthorizedError("Invalid email or password.")

    if user.status != UserStatus.ACTIVE:
        await audit_service.record(
            session,
            action=AuditAction.LOGIN_FAILED.value,
            resource_type="user",
            resource_id=str(user.id),
            tenant_id=user.tenant_id,
            user_id=user.id,
            new_data={"reason": f"account status is {user.status.value}"},
            request=request,
        )
        await session.commit()
        raise UnauthorizedError("This account is not active.")

    user.failed_login_attempts = 0
    user.last_login_at = datetime.now(UTC)

    token_pair = await _issue_token_pair(session, user, request)

    await audit_service.record(
        session,
        action=AuditAction.LOGIN.value,
        resource_type="user",
        resource_id=str(user.id),
        tenant_id=user.tenant_id,
        user_id=user.id,
        request=request,
    )
    await session.commit()
    return user, token_pair


async def refresh(
    session: AsyncSession, *, refresh_token: str, request: Request | None = None
) -> TokenPair:
    try:
        decoded = decode_token(refresh_token, expected_type=TokenType.REFRESH)
    except TokenError as exc:
        raise UnauthorizedError(str(exc)) from exc

    refresh_session = await refresh_session_repository.get_by_jti(session, uuid.UUID(decoded.jti))
    if refresh_session is None or refresh_session.revoked:
        raise UnauthorizedError("Refresh token has been revoked or does not exist.")
    if refresh_session.expires_at < datetime.now(UTC):
        raise UnauthorizedError("Refresh token has expired.")

    user = await user_repository.get_by_id(session, uuid.UUID(decoded.subject))
    if user is None or user.status != UserStatus.ACTIVE:
        raise UnauthorizedError("User no longer active.")

    # Rotate: revoke the used refresh token, issue a brand new pair.
    refresh_session.revoked = True
    token_pair = await _issue_token_pair(session, user, request)
    await session.commit()
    return token_pair


async def logout(
    session: AsyncSession, *, refresh_token: str, user_id: uuid.UUID | None = None
) -> None:
    try:
        decoded = decode_token(refresh_token, expected_type=TokenType.REFRESH)
    except TokenError:
        return  # logout is idempotent; an already-invalid token is not an error
    refresh_session = await refresh_session_repository.get_by_jti(session, uuid.UUID(decoded.jti))
    if refresh_session is not None:
        refresh_session.revoked = True
        await audit_service.record(
            session,
            action=AuditAction.LOGOUT.value,
            resource_type="user",
            resource_id=str(refresh_session.user_id),
            user_id=user_id or refresh_session.user_id,
        )
        await session.commit()


async def request_password_reset(session: AsyncSession, *, email: str) -> None:
    """Always succeeds from the caller's point of view (no user enumeration)."""
    user = await user_repository.get_by_email(session, email)
    if user is None or user.status != UserStatus.ACTIVE:
        return

    raw_token = uuid.uuid4().hex + uuid.uuid4().hex
    token_hash = hash_password(raw_token)

    password_reset_repository.add(
        session,
        PasswordResetToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        ),
    )
    await session.commit()
    # NOTE: Phase 0 does not deliver email; the raw token would be dispatched via the
    # notification service's EMAIL channel extension point once implemented (see
    # app/services/notification_service.py). Logged at debug level only in non-production so
    # the reset flow is exercisable end-to-end in local development.
    if not settings.is_production:
        logging.getLogger("app.auth").debug("Password reset token for %s: %s", email, raw_token)


async def reset_password(session: AsyncSession, *, token: str, new_password: str) -> None:
    # Tokens are stored hashed; scanning is required since Argon2 hashes are salted (no direct
    # lookup by hash of the raw token). Acceptable at Phase 0 volumes; revisit if this table grows.
    result = await session.execute(
        select(PasswordResetToken).where(PasswordResetToken.used_at.is_(None))
    )
    candidates = result.scalars().all()

    matched: PasswordResetToken | None = None
    for candidate in candidates:
        if verify_password(token, candidate.token_hash):
            matched = candidate
            break

    if matched is None or matched.expires_at < datetime.now(UTC):
        raise UnauthorizedError("Password reset token is invalid or has expired.")

    user = await user_repository.get_by_id(session, matched.user_id)
    if user is None:
        raise UnauthorizedError("Password reset token is invalid or has expired.")

    user.password_hash = hash_password(new_password)
    matched.used_at = datetime.now(UTC)
    await session.commit()
