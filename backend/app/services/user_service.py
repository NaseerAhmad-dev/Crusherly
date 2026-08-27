"""User management, always scoped to the caller's own tenant.

Tenant isolation is enforced here at the choke point, not left to the router: every function
that reads or writes a `User` takes `tenant_id` from the caller's SecurityContext (never from a
path/query/body parameter) and every repository call filters by it. See docs/multi-tenancy.md.
"""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.models.audit import AuditAction
from app.models.enums import UserStatus
from app.models.rbac import UserRole
from app.models.user import User
from app.repositories import role_repository, user_repository
from app.schemas.user import UserCreateRequest, UserUpdateRequest
from app.security.passwords import hash_password
from app.security.security_context import SecurityContext
from app.services import audit_service


async def list_users(
    session: AsyncSession, context: SecurityContext, page: int, page_size: int, search: str | None
) -> tuple[list[User], int]:
    if context.tenant_id is None:
        raise ForbiddenError("Platform users must manage users through tenant administration.")
    return await user_repository.list_users_in_tenant(
        session, context.tenant_id, offset=(page - 1) * page_size, limit=page_size, search=search
    )


async def get_user(session: AsyncSession, context: SecurityContext, user_id: uuid.UUID) -> User:
    if context.tenant_id is None:
        raise ForbiddenError("Platform users must manage users through tenant administration.")
    user = await user_repository.get_by_id_in_tenant(session, user_id, context.tenant_id)
    if user is None:
        raise NotFoundError("User not found.")
    return user


async def create_user(
    session: AsyncSession,
    context: SecurityContext,
    payload: UserCreateRequest,
    request: Request | None,
) -> User:
    if context.tenant_id is None:
        raise ForbiddenError("Platform users must manage users through tenant administration.")

    existing = await user_repository.get_by_email(session, payload.email)
    if existing is not None:
        raise ConflictError("A user with this email already exists.")

    user = User(
        tenant_id=context.tenant_id,
        email=payload.email.lower(),
        password_hash=hash_password(payload.password),
        first_name=payload.first_name,
        last_name=payload.last_name,
        phone=payload.phone,
        status=UserStatus.ACTIVE,
        is_verified=False,
        is_platform_user=False,
    )
    user_repository.add(session, user)
    await session.flush()

    await audit_service.record(
        session,
        action=AuditAction.USER_CREATED.value,
        resource_type="user",
        resource_id=str(user.id),
        tenant_id=context.tenant_id,
        user_id=context.user.id,
        new_data={"email": user.email},
        request=request,
    )
    await session.commit()
    return user


async def update_user(
    session: AsyncSession,
    context: SecurityContext,
    user_id: uuid.UUID,
    payload: UserUpdateRequest,
    request: Request | None,
) -> User:
    user = await get_user(session, context, user_id)
    old_data = {
        "first_name": user.first_name,
        "last_name": user.last_name,
        "status": user.status.value,
    }

    if payload.first_name is not None:
        user.first_name = payload.first_name
    if payload.last_name is not None:
        user.last_name = payload.last_name
    if payload.phone is not None:
        user.phone = payload.phone
    if payload.status is not None:
        user.status = payload.status

    await session.flush()
    await audit_service.record(
        session,
        action=AuditAction.USER_UPDATED.value,
        resource_type="user",
        resource_id=str(user.id),
        tenant_id=context.tenant_id,
        user_id=context.user.id,
        old_data=old_data,
        new_data={
            "first_name": user.first_name,
            "last_name": user.last_name,
            "status": user.status.value,
        },
        request=request,
    )
    await session.commit()
    return user


async def deactivate_user(
    session: AsyncSession, context: SecurityContext, user_id: uuid.UUID, request: Request | None
) -> User:
    """Users are deactivated, never hard-deleted (Master Build Specification section 14)."""
    user = await get_user(session, context, user_id)
    user.status = UserStatus.INACTIVE
    await session.flush()

    await audit_service.record(
        session,
        action=AuditAction.USER_DISABLED.value,
        resource_type="user",
        resource_id=str(user.id),
        tenant_id=context.tenant_id,
        user_id=context.user.id,
        request=request,
    )
    await session.commit()
    return user


async def assign_role(
    session: AsyncSession,
    context: SecurityContext,
    user_id: uuid.UUID,
    role_id: uuid.UUID,
    organization_unit_id: uuid.UUID | None,
    request: Request | None,
) -> UserRole:
    user = await get_user(session, context, user_id)
    role = await role_repository.get_visible_to_tenant(session, role_id, context.tenant_id)
    if role is None:
        raise NotFoundError("Role not found.")

    user_role = UserRole(
        user_id=user.id, role_id=role.id, organization_unit_id=organization_unit_id
    )
    user_role.role = role  # already loaded above; avoids a lazy-load on the relationship later
    role_repository.add(session, user_role)
    await session.flush()

    await audit_service.record(
        session,
        action=AuditAction.PERMISSION_CHANGED.value,
        resource_type="user",
        resource_id=str(user.id),
        tenant_id=context.tenant_id,
        user_id=context.user.id,
        new_data={
            "assigned_role": role.code,
            "organization_unit_id": (str(organization_unit_id) if organization_unit_id else None),
        },
        request=request,
    )
    await session.commit()
    return user_role
