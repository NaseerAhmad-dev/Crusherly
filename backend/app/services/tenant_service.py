"""Tenant lifecycle management. Platform-level operations only (see permission `tenants.*`)."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from app.core.exceptions import ConflictError, NotFoundError
from app.models.audit import AuditAction
from app.models.enums import TenantStatus, UserStatus
from app.models.rbac import UserRole
from app.models.tenant import Tenant
from app.models.user import User
from app.repositories import role_repository, tenant_repository, user_repository
from app.schemas.tenant import TenantCreateRequest, TenantUpdateRequest
from app.security.passwords import hash_password
from app.security.security_context import SecurityContext
from app.services import audit_service


async def list_tenants(
    session: AsyncSession, page: int, page_size: int
) -> tuple[list[Tenant], int]:
    return await tenant_repository.list_tenants(
        session, offset=(page - 1) * page_size, limit=page_size
    )


async def get_tenant(session: AsyncSession, tenant_id: uuid.UUID) -> Tenant:
    tenant = await tenant_repository.get_by_id(session, tenant_id)
    if tenant is None:
        raise NotFoundError("Tenant not found.")
    return tenant


async def create_tenant(
    session: AsyncSession,
    context: SecurityContext,
    payload: TenantCreateRequest,
    request: Request | None,
) -> Tenant:
    existing = await tenant_repository.get_by_code_or_slug(session, payload.code, payload.slug)
    if existing is not None:
        raise ConflictError("A tenant with this code or slug already exists.")

    existing_user = await user_repository.get_by_email(session, payload.admin_email)
    if existing_user is not None:
        raise ConflictError("A user with this admin email already exists.")

    tenant = Tenant(
        name=payload.name,
        code=payload.code,
        slug=payload.slug,
        status=TenantStatus.ACTIVE,
        timezone=payload.timezone,
        currency=payload.currency,
    )
    tenant_repository.add(session, tenant)
    await session.flush()

    tenant_admin_role = await role_repository.get_by_code(session, "TENANT_ADMIN", tenant_id=None)
    if tenant_admin_role is None:
        raise NotFoundError("TENANT_ADMIN role is not seeded. Run the platform seed script first.")

    admin_user = User(
        tenant_id=tenant.id,
        email=payload.admin_email.lower(),
        password_hash=hash_password(payload.admin_password),
        first_name=payload.admin_first_name,
        last_name=payload.admin_last_name,
        status=UserStatus.ACTIVE,
        is_verified=False,
        is_platform_user=False,
    )
    user_repository.add(session, admin_user)
    await session.flush()

    role_repository.add(session, UserRole(user_id=admin_user.id, role_id=tenant_admin_role.id))
    await session.flush()

    await audit_service.record(
        session,
        action=AuditAction.TENANT_CREATED.value,
        resource_type="tenant",
        resource_id=str(tenant.id),
        tenant_id=tenant.id,
        user_id=context.user.id,
        new_data={"code": tenant.code, "name": tenant.name, "admin_email": admin_user.email},
        request=request,
    )
    await session.commit()
    return tenant


async def update_tenant(
    session: AsyncSession,
    context: SecurityContext,
    tenant_id: uuid.UUID,
    payload: TenantUpdateRequest,
    request: Request | None,
) -> Tenant:
    tenant = await get_tenant(session, tenant_id)
    old_data = {"name": tenant.name, "timezone": tenant.timezone, "currency": tenant.currency}

    if payload.name is not None:
        tenant.name = payload.name
    if payload.timezone is not None:
        tenant.timezone = payload.timezone
    if payload.currency is not None:
        tenant.currency = payload.currency

    await session.flush()
    await audit_service.record(
        session,
        action=AuditAction.TENANT_UPDATED.value,
        resource_type="tenant",
        resource_id=str(tenant.id),
        tenant_id=tenant.id,
        user_id=context.user.id,
        old_data=old_data,
        new_data={"name": tenant.name, "timezone": tenant.timezone, "currency": tenant.currency},
        request=request,
    )
    await session.commit()
    return tenant


async def suspend_tenant(
    session: AsyncSession, context: SecurityContext, tenant_id: uuid.UUID, request: Request | None
) -> Tenant:
    tenant = await get_tenant(session, tenant_id)
    tenant.status = TenantStatus.SUSPENDED
    await session.flush()

    await audit_service.record(
        session,
        action=AuditAction.TENANT_SUSPENDED.value,
        resource_type="tenant",
        resource_id=str(tenant.id),
        tenant_id=tenant.id,
        user_id=context.user.id,
        request=request,
    )
    await session.commit()
    return tenant
