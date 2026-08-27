from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.unit import Unit


async def list_all(session: AsyncSession) -> list[Unit]:
    result = await session.execute(select(Unit).order_by(Unit.name))
    return list(result.scalars().all())
