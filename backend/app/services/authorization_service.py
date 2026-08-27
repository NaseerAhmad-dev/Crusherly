"""Scope-aware authorization.

RBAC (`SecurityContext.has_permission`) answers "what can the user do". This service answers
"where" — whether the user's grants for a permission cover a specific resource's organization
unit, per Master Build Specification section 10. Every future business module must call
`authorize()` (or the `authorize_dependency` factory in app/security/dependencies.py) instead of
writing its own scope logic.
"""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenError
from app.models.enums import ScopeLevel
from app.repositories.organization_repository import get_self_and_ancestor_ids
from app.security.security_context import SecurityContext


async def is_authorized(
    session: AsyncSession,
    context: SecurityContext,
    permission_code: str,
    resource_organization_unit_id: uuid.UUID | None = None,
) -> bool:
    """True if `context` holds `permission_code` at a scope covering the given resource.

    `resource_organization_unit_id=None` means the resource is not tied to a specific
    organization unit (e.g. a tenant-wide setting); only PLATFORM/TENANT-level grants satisfy it.
    """
    grants = context.grants_for(permission_code)
    if not grants:
        return False

    resource_ancestor_ids: set[uuid.UUID] | None = None

    for grant in grants:
        if grant.scope_level is ScopeLevel.PLATFORM:
            return True
        if grant.scope_level is ScopeLevel.TENANT:
            # Tenant-wide grants cover any resource within the same tenant, regardless of
            # organization unit. Cross-tenant isolation is enforced separately at the
            # repository/service layer (the resource is never even fetched cross-tenant).
            return True

        if resource_organization_unit_id is None:
            continue  # a node-scoped grant cannot cover a resource with no organization unit

        if grant.organization_unit_id == resource_organization_unit_id:
            return True

        if resource_ancestor_ids is None:
            resource_ancestor_ids = await get_self_and_ancestor_ids(
                session, resource_organization_unit_id
            )
        if grant.organization_unit_id in resource_ancestor_ids:
            return True

    return False


async def authorize(
    session: AsyncSession,
    context: SecurityContext,
    permission_code: str,
    resource_organization_unit_id: uuid.UUID | None = None,
) -> None:
    """Raises ForbiddenError if `context` is not authorized; otherwise returns None."""
    if not await is_authorized(session, context, permission_code, resource_organization_unit_id):
        raise ForbiddenError("You do not have permission to perform this action.")
