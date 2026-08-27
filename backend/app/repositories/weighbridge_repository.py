import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import WeighbridgeTicketStatus
from app.models.weighbridge import WeighbridgeTicket


def add(session: AsyncSession, ticket: WeighbridgeTicket) -> None:
    session.add(ticket)


async def get_by_id_in_tenant(
    session: AsyncSession, ticket_id: uuid.UUID, tenant_id: uuid.UUID
) -> WeighbridgeTicket | None:
    result = await session.execute(
        select(WeighbridgeTicket).where(
            WeighbridgeTicket.id == ticket_id, WeighbridgeTicket.tenant_id == tenant_id
        )
    )
    return result.scalar_one_or_none()


async def list_in_tenant(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    offset: int,
    limit: int,
    status: WeighbridgeTicketStatus | None = None,
) -> tuple[list[WeighbridgeTicket], int]:
    conditions = [WeighbridgeTicket.tenant_id == tenant_id]
    if status is not None:
        conditions.append(WeighbridgeTicket.status == status)

    count_result = await session.execute(
        select(func.count()).select_from(WeighbridgeTicket).where(*conditions)
    )
    total = count_result.scalar_one()

    result = await session.execute(
        select(WeighbridgeTicket)
        .where(*conditions)
        .order_by(WeighbridgeTicket.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(result.scalars().all()), total
