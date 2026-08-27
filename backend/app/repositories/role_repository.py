import uuid

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.rbac import Permission, Role, RolePermission, UserRole


async def get_by_id(session: AsyncSession, role_id: uuid.UUID) -> Role | None:
    result = await session.execute(
        select(Role)
        .where(Role.id == role_id)
        .options(selectinload(Role.role_permissions).selectinload(RolePermission.permission))
    )
    return result.scalar_one_or_none()


async def get_visible_to_tenant(
    session: AsyncSession, role_id: uuid.UUID, tenant_id: uuid.UUID | None
) -> Role | None:
    """A role is visible to a tenant if it is a global (tenant_id IS NULL) system role, or a
    custom role owned by that exact tenant. This is the tenant-isolation choke point for roles.
    """
    result = await session.execute(
        select(Role)
        .where(Role.id == role_id, or_(Role.tenant_id.is_(None), Role.tenant_id == tenant_id))
        .options(selectinload(Role.role_permissions).selectinload(RolePermission.permission))
    )
    return result.scalar_one_or_none()


async def list_visible_to_tenant(session: AsyncSession, tenant_id: uuid.UUID | None) -> list[Role]:
    result = await session.execute(
        select(Role)
        .where(or_(Role.tenant_id.is_(None), Role.tenant_id == tenant_id))
        .options(selectinload(Role.role_permissions).selectinload(RolePermission.permission))
        .order_by(Role.is_system.desc(), Role.name)
    )
    return list(result.scalars().unique().all())


async def get_by_code(session: AsyncSession, code: str, tenant_id: uuid.UUID | None) -> Role | None:
    result = await session.execute(
        select(Role).where(Role.code == code, Role.tenant_id == tenant_id)
    )
    return result.scalar_one_or_none()


async def get_permissions_by_codes(session: AsyncSession, codes: list[str]) -> list[Permission]:
    if not codes:
        return []
    result = await session.execute(select(Permission).where(Permission.code.in_(codes)))
    return list(result.scalars().all())


async def get_user_role(session: AsyncSession, user_role_id: uuid.UUID) -> UserRole | None:
    return await session.get(UserRole, user_role_id)


def add(session: AsyncSession, obj) -> None:
    session.add(obj)
