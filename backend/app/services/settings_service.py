"""Hierarchical settings resolution: Module+Plant > Module+Tenant > Plant > Tenant > Platform.

Business modules should call `resolve()` to read effective configuration rather than hard-coding
tenant-specific business rules (Master Build Specification section 23).
"""

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditAction
from app.models.setting import Setting
from app.repositories import setting_repository
from app.services import audit_service


def _specificity(setting: Setting) -> int:
    score = 0
    if setting.tenant_id is not None:
        score += 1
    if setting.organization_unit_id is not None:
        score += 2
    if setting.module is not None:
        score += 4
    return score


async def resolve(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID | None,
    key: str,
    organization_unit_id: uuid.UUID | None = None,
    module: str | None = None,
    default: Any = None,
) -> Any:
    candidates = await setting_repository.list_candidates(session, tenant_id=tenant_id, key=key)

    applicable = [
        s
        for s in candidates
        if (s.organization_unit_id is None or s.organization_unit_id == organization_unit_id)
        and (s.module is None or s.module == module)
    ]
    if not applicable:
        return default

    best = max(applicable, key=_specificity)
    return best.value


async def upsert(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID | None,
    key: str,
    value: Any,
    organization_unit_id: uuid.UUID | None,
    module: str | None,
    changed_by: uuid.UUID,
) -> Setting:
    existing = await setting_repository.find(
        session,
        tenant_id=tenant_id,
        organization_unit_id=organization_unit_id,
        module=module,
        key=key,
    )
    if existing is not None:
        old_value = existing.value
        existing.value = value
        setting = existing
    else:
        old_value = None
        setting = Setting(
            tenant_id=tenant_id,
            organization_unit_id=organization_unit_id,
            module=module,
            key=key,
            value=value,
        )
        setting_repository.add(session, setting)

    await session.flush()
    await audit_service.record(
        session,
        action=AuditAction.SETTINGS_CHANGED.value,
        resource_type="setting",
        resource_id=key,
        tenant_id=tenant_id,
        user_id=changed_by,
        old_data={"value": old_value},
        new_data={"value": value},
    )
    await session.commit()
    return setting
