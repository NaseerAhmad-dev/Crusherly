from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rbac import Permission


async def list_all(session: AsyncSession) -> list[Permission]:
    result = await session.execute(select(Permission).order_by(Permission.code))
    return list(result.scalars().all())


async def get_by_code(session: AsyncSession, code: str) -> Permission | None:
    result = await session.execute(select(Permission).where(Permission.code == code))
    return result.scalar_one_or_none()
