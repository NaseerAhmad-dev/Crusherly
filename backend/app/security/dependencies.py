"""Reusable FastAPI authentication/authorization dependencies.

Every future module route must depend on these rather than reimplementing auth:

    require_authenticated_user()          -> SecurityContext
    require_permission("users.view")      -> dependency; raises 403 if not held at ANY scope
    authorize(session, ctx, code, org_id) -> awaitable; raises 403 unless scope covers org_id
"""

import uuid
from collections.abc import Callable

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.models.enums import UserStatus
from app.models.user import User
from app.security.security_context import SecurityContext
from app.security.tokens import TokenError, TokenType, decode_token
from app.services.security_context_service import build_security_context

_bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    session: AsyncSession = Depends(get_db),
) -> User:
    if credentials is None or not credentials.credentials:
        raise UnauthorizedError("Authentication credentials were not provided.")

    try:
        decoded = decode_token(credentials.credentials, expected_type=TokenType.ACCESS)
    except TokenError as exc:
        raise UnauthorizedError(str(exc)) from exc

    try:
        user_id = uuid.UUID(decoded.subject)
    except ValueError as exc:
        raise UnauthorizedError("Token subject is invalid.") from exc

    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise UnauthorizedError("User no longer exists.")
    if user.status != UserStatus.ACTIVE:
        raise UnauthorizedError("User account is not active.")

    request.state.user_id = str(user.id)
    request.state.tenant_id = str(user.tenant_id) if user.tenant_id else None
    return user


async def require_authenticated_user(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> SecurityContext:
    """The primary dependency: authenticates the user and resolves their full security context
    (roles, permissions, scope) fresh from the database on every request."""
    return await build_security_context(session, user)


def require_permission(permission_code: str) -> Callable:
    """Dependency factory: 403s unless the caller holds `permission_code` at ANY scope.

    Use this for route-level gating (e.g. "must be able to view users at all"). For checks
    against one specific resource's organization unit, call
    `app.services.authorization_service.authorize(...)` inside the route/service instead.
    """

    async def _dependency(
        context: SecurityContext = Depends(require_authenticated_user),
    ) -> SecurityContext:
        if not context.has_permission(permission_code):
            raise ForbiddenError("You do not have permission to perform this action.")
        return context

    return _dependency
