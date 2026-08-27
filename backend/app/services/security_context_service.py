"""Builds a SecurityContext for a user by resolving roles, permissions, and scope from the
database. This is the ONLY place that should query UserRole/RolePermission/ScopeAssignment for
authorization purposes — everything else consumes the resulting SecurityContext.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.enums import ScopeLevel
from app.models.organization import OrganizationUnit
from app.models.rbac import Role, RolePermission, UserRole
from app.models.scope import ScopeAssignment
from app.models.user import User
from app.security.security_context import PermissionGrant, SecurityContext


async def build_security_context(session: AsyncSession, user: User) -> SecurityContext:
    is_platform_user = user.tenant_id is None and user.is_platform_user

    result = await session.execute(
        select(UserRole)
        .where(UserRole.user_id == user.id)
        .options(
            selectinload(UserRole.role)
            .selectinload(Role.role_permissions)
            .selectinload(RolePermission.permission)
        )
    )
    user_roles: list[UserRole] = list(result.scalars().unique().all())

    if not user_roles:
        return SecurityContext(
            user=user, tenant_id=user.tenant_id, is_platform_user=is_platform_user
        )

    user_role_ids = [ur.id for ur in user_roles]
    scope_result = await session.execute(
        select(ScopeAssignment).where(ScopeAssignment.user_role_id.in_(user_role_ids))
    )
    explicit_scopes: dict[uuid.UUID, list[ScopeAssignment]] = {}
    for sa in scope_result.scalars().all():
        explicit_scopes.setdefault(sa.user_role_id, []).append(sa)

    # Batch-resolve unit_type for every org unit implicitly scoped via UserRole.organization_unit_id
    # (no explicit ScopeAssignment row) so grants report an accurate ScopeLevel.
    implicit_org_unit_ids = {
        ur.organization_unit_id
        for ur in user_roles
        if ur.organization_unit_id is not None and ur.id not in explicit_scopes
    }
    unit_type_by_id: dict[uuid.UUID, str] = {}
    if implicit_org_unit_ids:
        ou_result = await session.execute(
            select(OrganizationUnit.id, OrganizationUnit.unit_type).where(
                OrganizationUnit.id.in_(implicit_org_unit_ids)
            )
        )
        unit_type_by_id = {row[0]: row[1].value for row in ou_result.all()}

    role_codes: set[str] = set()
    grants: list[PermissionGrant] = []

    for user_role in user_roles:
        role = user_role.role
        role_codes.add(role.code)
        permission_codes = [rp.permission.code for rp in role.role_permissions]

        scopes_for_role = explicit_scopes.get(user_role.id)
        if scopes_for_role:
            resolved_scopes = [(s.scope_level, s.organization_unit_id) for s in scopes_for_role]
        elif user_role.organization_unit_id is not None:
            # Implicit single-node scope carried directly on UserRole: covers that unit and
            # everything beneath it (containment is checked via ancestor-chain walk at
            # authorize-time, see AuthorizationService).
            unit_type = unit_type_by_id.get(user_role.organization_unit_id)
            scope_level = ScopeLevel(unit_type) if unit_type else ScopeLevel.DEPARTMENT
            resolved_scopes = [(scope_level, user_role.organization_unit_id)]
        else:
            # No organization unit attached: covers the whole tenant (or the whole platform for
            # platform-level users with no tenant).
            default_level = ScopeLevel.PLATFORM if is_platform_user else ScopeLevel.TENANT
            resolved_scopes = [(default_level, None)]

        for permission_code in permission_codes:
            for scope_level, organization_unit_id in resolved_scopes:
                grants.append(
                    PermissionGrant(
                        permission_code=permission_code,
                        scope_level=scope_level,
                        organization_unit_id=organization_unit_id,
                    )
                )

    return SecurityContext(
        user=user,
        tenant_id=user.tenant_id,
        is_platform_user=is_platform_user,
        role_codes=role_codes,
        grants=grants,
    )
