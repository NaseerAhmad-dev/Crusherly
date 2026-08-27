"""Shared notification service.

Only the IN_APP channel is delivered in Phase 0. EMAIL/SMS/PUSH/WHATSAPP are modelled on
`Notification.channel` as extension points: a future channel provider registers itself here and
`send()` dispatches without callers needing to change (Master Build Specification section 22).
Future business modules should call `send()` rather than writing directly to the notifications
table.
"""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.enums import NotificationChannel
from app.models.notification import Notification
from app.repositories import notification_repository


async def send(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    title: str,
    body: str,
    tenant_id: uuid.UUID | None = None,
    channel: NotificationChannel = NotificationChannel.IN_APP,
    entity_type: str | None = None,
    entity_id: str | None = None,
) -> Notification:
    notification = Notification(
        tenant_id=tenant_id,
        user_id=user_id,
        channel=channel,
        title=title,
        body=body,
        entity_type=entity_type,
        entity_id=entity_id,
    )
    notification_repository.add(session, notification)
    await session.commit()
    return notification


async def list_for_user(
    session: AsyncSession, user_id: uuid.UUID, page: int, page_size: int, unread_only: bool
) -> tuple[list[Notification], int]:
    return await notification_repository.list_for_user(
        session, user_id, offset=(page - 1) * page_size, limit=page_size, unread_only=unread_only
    )


async def mark_read(
    session: AsyncSession, user_id: uuid.UUID, notification_id: uuid.UUID
) -> Notification:
    notification = await notification_repository.get_for_user(session, notification_id, user_id)
    if notification is None:
        raise NotFoundError("Notification not found.")
    notification_repository.mark_read(notification)
    await session.commit()
    return notification
