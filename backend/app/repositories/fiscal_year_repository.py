import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.fiscal_year import FiscalYear


async def get_active_for_tenant(session: AsyncSession, tenant_id: uuid.UUID) -> FiscalYear | None:
    result = await session.execute(
        select(FiscalYear).where(FiscalYear.tenant_id == tenant_id, FiscalYear.is_active.is_(True))
    )
    return result.scalar_one_or_none()


def add(session: AsyncSession, fiscal_year: FiscalYear) -> None:
    session.add(fiscal_year)
