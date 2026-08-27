import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


async def get_by_id(session: AsyncSession, user_id: uuid.UUID) -> User | None:
    return await session.get(User, user_id)


async def get_by_id_in_tenant(
    session: AsyncSession, user_id: uuid.UUID, tenant_id: uuid.UUID
) -> User | None:
    """Fetch a user, scoped to a tenant, so a mismatched tenant_id never leaks another tenant's
    row — this is the tenant-isolation choke point for single-user lookups."""
    result = await session.execute(
        select(User).where(User.id == user_id, User.tenant_id == tenant_id)
    )
    return result.scalar_one_or_none()


async def get_by_email(session: AsyncSession, email: str) -> User | None:
    """Email is unique across the entire platform (see ADR-003), so login and uniqueness checks
    never need a tenant_id: a tenant-scoped lookup would be ambiguous if the same email could
    exist under two tenants, and a global login page has no tenant context to scope by anyway."""
    result = await session.execute(select(User).where(func.lower(User.email) == email.lower()))
    return result.scalar_one_or_none()


async def list_users_in_tenant(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    offset: int,
    limit: int,
    search: str | None = None,
) -> tuple[list[User], int]:
    filters = [User.tenant_id == tenant_id]
    if search:
        like = f"%{search.lower()}%"
        filters.append(
            or_(
                func.lower(User.email).like(like),
                func.lower(User.first_name).like(like),
                func.lower(User.last_name).like(like),
            )
        )

    count_result = await session.execute(select(func.count()).select_from(User).where(*filters))
    total = count_result.scalar_one()

    result = await session.execute(
        select(User).where(*filters).order_by(User.created_at.desc()).offset(offset).limit(limit)
    )
    return list(result.scalars().all()), total


def add(session: AsyncSession, user: User) -> None:
    session.add(user)
