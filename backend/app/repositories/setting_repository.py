import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.setting import Setting


async def find(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID | None,
    organization_unit_id: uuid.UUID | None,
    module: str | None,
    key: str,
) -> Setting | None:
    result = await session.execute(
        select(Setting).where(
            Setting.tenant_id == tenant_id,
            Setting.organization_unit_id == organization_unit_id,
            Setting.module == module,
            Setting.key == key,
        )
    )
    return result.scalar_one_or_none()


async def list_candidates(
    session: AsyncSession, *, tenant_id: uuid.UUID | None, key: str
) -> list[Setting]:
    """All settings rows for `key` that could apply to this tenant (platform + tenant-level),
    for the resolver in app/services/settings_service.py to pick the most specific one."""
    result = await session.execute(
        select(Setting).where(
            Setting.key == key,
            (Setting.tenant_id.is_(None)) | (Setting.tenant_id == tenant_id),
        )
    )
    return list(result.scalars().all())


def add(session: AsyncSession, setting: Setting) -> None:
    session.add(setting)
