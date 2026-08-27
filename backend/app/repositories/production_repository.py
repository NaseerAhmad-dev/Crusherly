import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.enums import ProductionEntryStatus
from app.models.production import ProductionEntry


def add(session: AsyncSession, entry: ProductionEntry) -> None:
    session.add(entry)


async def get_by_id_in_tenant(
    session: AsyncSession, entry_id: uuid.UUID, tenant_id: uuid.UUID
) -> ProductionEntry | None:
    result = await session.execute(
        select(ProductionEntry)
        .where(ProductionEntry.id == entry_id, ProductionEntry.tenant_id == tenant_id)
        .options(selectinload(ProductionEntry.outputs))
    )
    return result.scalar_one_or_none()


async def list_in_tenant(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    offset: int,
    limit: int,
    status: ProductionEntryStatus | None = None,
) -> tuple[list[ProductionEntry], int]:
    conditions = [ProductionEntry.tenant_id == tenant_id]
    if status is not None:
        conditions.append(ProductionEntry.status == status)

    count_result = await session.execute(
        select(func.count()).select_from(ProductionEntry).where(*conditions)
    )
    total = count_result.scalar_one()

    result = await session.execute(
        select(ProductionEntry)
        .where(*conditions)
        .options(selectinload(ProductionEntry.outputs))
        .order_by(ProductionEntry.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(result.scalars().all()), total
