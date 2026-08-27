import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.refresh_session import RefreshSession


async def get_by_jti(session: AsyncSession, jti: uuid.UUID) -> RefreshSession | None:
    result = await session.execute(select(RefreshSession).where(RefreshSession.jti == jti))
    return result.scalar_one_or_none()


def add(session: AsyncSession, refresh_session: RefreshSession) -> None:
    session.add(refresh_session)
