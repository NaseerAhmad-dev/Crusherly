"""Role and role-permission management.

System roles (SUPER_ADMIN, TENANT_ADMIN, MANAGER, OPERATOR, ACCOUNTANT, STOREKEEPER, VIEWER) are
seeded platform-wide (`tenant_id IS NULL`, `is_system=True`) and cannot be edited or deleted
through the API; tenants may additionally define their own custom roles.
"""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.models.audit import AuditAction
from app.models.rbac import Role, RolePermission
from app.repositories import role_repository
from app.schemas.role import RoleCreateRequest, RoleUpdateRequest
from app.security.security_context import SecurityContext
from app.services import audit_service


async def list_roles(session: AsyncSession, context: SecurityContext) -> list[Role]:
    return await role_repository.list_visible_to_tenant(session, context.tenant_id)


async def get_role(session: AsyncSession, context: SecurityContext, role_id: uuid.UUID) -> Role:
    role = await role_repository.get_visible_to_tenant(session, role_id, context.tenant_id)
    if role is None:
        raise NotFoundError("Role not found.")
    return role


async def create_role(
    session: AsyncSession,
    context: SecurityContext,
    payload: RoleCreateRequest,
    request: Request | None,
) -> Role:
    if context.tenant_id is None:
        raise ForbiddenError("Platform-level custom roles are not supported in Phase 0.")

    existing = await role_repository.get_by_code(session, payload.code, context.tenant_id)
    if existing is not None:
        raise ConflictError("A role with this code already exists for this tenant.")

    role = Role(
        tenant_id=context.tenant_id,
        code=payload.code,
        name=payload.name,
        description=payload.description,
        is_system=False,
    )
    role_repository.add(session, role)
    await session.flush()

    if payload.permission_codes:
        permissions = await role_repository.get_permissions_by_codes(
            session, payload.permission_codes
        )
        for permission in permissions:
            role_repository.add(
                session, RolePermission(role_id=role.id, permission_id=permission.id)
            )
        await session.flush()

    await audit_service.record(
        session,
        action=AuditAction.ROLE_CREATED.value,
        resource_type="role",
        resource_id=str(role.id),
        tenant_id=context.tenant_id,
        user_id=context.user.id,
        new_data={"code": role.code, "permission_codes": payload.permission_codes},
        request=request,
    )
    await session.commit()
    return await get_role(session, context, role.id)


async def update_role(
    session: AsyncSession,
    context: SecurityContext,
    role_id: uuid.UUID,
    payload: RoleUpdateRequest,
    request: Request | None,
) -> Role:
    role = await get_role(session, context, role_id)
    if role.is_system:
        raise ForbiddenError("System roles cannot be modified.")

    old_data = {"name": role.name, "description": role.description}
    if payload.name is not None:
        role.name = payload.name
    if payload.description is not None:
        role.description = payload.description

    await session.flush()
    await audit_service.record(
        session,
        action=AuditAction.ROLE_UPDATED.value,
        resource_type="role",
        resource_id=str(role.id),
        tenant_id=context.tenant_id,
        user_id=context.user.id,
        old_data=old_data,
        new_data={"name": role.name, "description": role.description},
        request=request,
    )
    await session.commit()
    return role


async def update_role_permissions(
    session: AsyncSession,
    context: SecurityContext,
    role_id: uuid.UUID,
    permission_codes: list[str],
    request: Request | None,
) -> Role:
    role = await get_role(session, context, role_id)
    if role.is_system:
        raise ForbiddenError("System role permissions cannot be modified.")

    old_codes = sorted(rp.permission.code for rp in role.role_permissions)
    for rp in list(role.role_permissions):
        await session.delete(rp)
    await session.flush()

    permissions = await role_repository.get_permissions_by_codes(session, permission_codes)
    for permission in permissions:
        role_repository.add(session, RolePermission(role_id=role.id, permission_id=permission.id))
    await session.flush()

    await audit_service.record(
        session,
        action=AuditAction.PERMISSION_CHANGED.value,
        resource_type="role",
        resource_id=str(role.id),
        tenant_id=context.tenant_id,
        user_id=context.user.id,
        old_data={"permission_codes": old_codes},
        new_data={"permission_codes": sorted(p.code for p in permissions)},
        request=request,
    )
    await session.commit()
    return await get_role(session, context, role.id)


async def delete_role(
    session: AsyncSession, context: SecurityContext, role_id: uuid.UUID, request: Request | None
) -> None:
    role = await get_role(session, context, role_id)
    if role.is_system:
        raise ForbiddenError("System roles cannot be deleted.")

    await audit_service.record(
        session,
        action=AuditAction.ROLE_DELETED.value,
        resource_type="role",
        resource_id=str(role.id),
        tenant_id=context.tenant_id,
        user_id=context.user.id,
        old_data={"code": role.code},
        request=request,
    )
    await session.delete(role)
    await session.commit()
