import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.attachment import Attachment


async def get_by_id_in_tenant(
    session: AsyncSession, attachment_id: uuid.UUID, tenant_id: uuid.UUID
) -> Attachment | None:
    result = await session.execute(
        select(Attachment).where(Attachment.id == attachment_id, Attachment.tenant_id == tenant_id)
    )
    return result.scalar_one_or_none()


async def list_for_entity(
    session: AsyncSession, tenant_id: uuid.UUID, entity_type: str, entity_id: str
) -> list[Attachment]:
    result = await session.execute(
        select(Attachment).where(
            Attachment.tenant_id == tenant_id,
            Attachment.entity_type == entity_type,
            Attachment.entity_id == entity_id,
        )
    )
    return list(result.scalars().all())


def add(session: AsyncSession, attachment: Attachment) -> None:
    session.add(attachment)


async def delete(session: AsyncSession, attachment: Attachment) -> None:
    await session.delete(attachment)
