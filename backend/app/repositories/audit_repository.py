import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditEvent


def add(session: AsyncSession, event: AuditEvent) -> None:
    session.add(event)


async def list_events(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID | None,
    offset: int,
    limit: int,
    action: str | None = None,
    resource_type: str | None = None,
    user_id: uuid.UUID | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> tuple[list[AuditEvent], int]:
    filters = []
    if tenant_id is not None:
        filters.append(AuditEvent.tenant_id == tenant_id)
    if action:
        filters.append(AuditEvent.action == action)
    if resource_type:
        filters.append(AuditEvent.resource_type == resource_type)
    if user_id:
        filters.append(AuditEvent.user_id == user_id)
    if date_from:
        filters.append(AuditEvent.timestamp >= date_from)
    if date_to:
        filters.append(AuditEvent.timestamp <= date_to)

    count_result = await session.execute(
        select(func.count()).select_from(AuditEvent).where(*filters)
    )
    total = count_result.scalar_one()

    result = await session.execute(
        select(AuditEvent)
        .where(*filters)
        .order_by(AuditEvent.timestamp.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(result.scalars().all()), total
