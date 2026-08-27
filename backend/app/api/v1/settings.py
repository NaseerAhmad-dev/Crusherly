import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.common import SuccessResponse
from app.schemas.setting import SettingResponse, SettingUpsertRequest
from app.security.dependencies import require_permission
from app.security.security_context import SecurityContext
from app.services import settings_service

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("/{key}", response_model=SuccessResponse[dict])
async def get_setting(
    key: str,
    organization_unit_id: uuid.UUID | None = Query(default=None),
    module: str | None = Query(default=None),
    context: SecurityContext = Depends(require_permission("settings.view")),
    session: AsyncSession = Depends(get_db),
):
    value = await settings_service.resolve(
        session,
        tenant_id=context.tenant_id,
        key=key,
        organization_unit_id=organization_unit_id,
        module=module,
    )
    return SuccessResponse(data={"key": key, "value": value})


@router.put("", response_model=SuccessResponse[SettingResponse])
async def upsert_setting(
    payload: SettingUpsertRequest,
    context: SecurityContext = Depends(require_permission("settings.update")),
    session: AsyncSession = Depends(get_db),
):
    setting = await settings_service.upsert(
        session,
        tenant_id=context.tenant_id,
        key=payload.key,
        value=payload.value,
        organization_unit_id=payload.organization_unit_id,
        module=payload.module,
        changed_by=context.user.id,
    )
    return SuccessResponse(data=SettingResponse.model_validate(setting))
