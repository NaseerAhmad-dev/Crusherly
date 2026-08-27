import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification


async def list_for_user(
    session: AsyncSession, user_id: uuid.UUID, offset: int, limit: int, unread_only: bool = False
) -> tuple[list[Notification], int]:
    filters = [Notification.user_id == user_id]
    if unread_only:
        filters.append(Notification.is_read.is_(False))

    count_result = await session.execute(
        select(func.count()).select_from(Notification).where(*filters)
    )
    total = count_result.scalar_one()

    result = await session.execute(
        select(Notification)
        .where(*filters)
        .order_by(Notification.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(result.scalars().all()), total


async def get_for_user(
    session: AsyncSession, notification_id: uuid.UUID, user_id: uuid.UUID
) -> Notification | None:
    result = await session.execute(
        select(Notification).where(
            Notification.id == notification_id, Notification.user_id == user_id
        )
    )
    return result.scalar_one_or_none()


def add(session: AsyncSession, notification: Notification) -> None:
    session.add(notification)


def mark_read(notification: Notification) -> None:
    notification.is_read = True
    notification.read_at = datetime.now(UTC)
