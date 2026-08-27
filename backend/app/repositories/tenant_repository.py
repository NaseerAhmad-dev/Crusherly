import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant import Tenant


async def get_by_id(session: AsyncSession, tenant_id: uuid.UUID) -> Tenant | None:
    return await session.get(Tenant, tenant_id)


async def get_by_code_or_slug(session: AsyncSession, code: str, slug: str) -> Tenant | None:
    result = await session.execute(
        select(Tenant).where((Tenant.code == code) | (Tenant.slug == slug))
    )
    return result.scalar_one_or_none()


async def list_tenants(session: AsyncSession, offset: int, limit: int) -> tuple[list[Tenant], int]:
    count_result = await session.execute(select(func.count()).select_from(Tenant))
    total = count_result.scalar_one()

    result = await session.execute(
        select(Tenant).order_by(Tenant.created_at.desc()).offset(offset).limit(limit)
    )
    return list(result.scalars().all()), total


def add(session: AsyncSession, tenant: Tenant) -> None:
    session.add(tenant)
