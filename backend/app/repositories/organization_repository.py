"""Organization-unit hierarchy queries.

The hierarchy is shallow (Tenant -> Business Unit -> Plant -> Site -> Department, at most 4
levels deep), so ancestor resolution walks `parent_id` in a bounded loop rather than needing a
recursive CTE.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organization import OrganizationUnit

_MAX_DEPTH = 10  # safety bound against a corrupted/cyclic hierarchy


async def list_for_tenant(session: AsyncSession, tenant_id: uuid.UUID) -> list[OrganizationUnit]:
    result = await session.execute(
        select(OrganizationUnit)
        .where(OrganizationUnit.tenant_id == tenant_id)
        .order_by(OrganizationUnit.name)
    )
    return list(result.scalars().all())


async def get_self_and_ancestor_ids(
    session: AsyncSession, organization_unit_id: uuid.UUID | None
) -> set[uuid.UUID]:
    """Return {organization_unit_id} plus every ancestor's id, walking up to the root."""
    if organization_unit_id is None:
        return set()

    ids: set[uuid.UUID] = set()
    current_id: uuid.UUID | None = organization_unit_id
    depth = 0

    while current_id is not None and depth < _MAX_DEPTH:
        ids.add(current_id)
        result = await session.execute(
            select(OrganizationUnit.parent_id).where(OrganizationUnit.id == current_id)
        )
        row = result.first()
        if row is None:
            break
        current_id = row[0]
        depth += 1

    return ids
