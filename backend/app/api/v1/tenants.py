import math
import uuid

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.common import Page, PageMeta, SuccessResponse
from app.schemas.tenant import TenantCreateRequest, TenantResponse, TenantUpdateRequest
from app.security.dependencies import require_permission
from app.security.security_context import SecurityContext
from app.services import tenant_service

router = APIRouter(prefix="/tenants", tags=["tenants"])


@router.get("", response_model=Page[TenantResponse])
async def list_tenants(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    _context: SecurityContext = Depends(require_permission("tenants.view")),
    session: AsyncSession = Depends(get_db),
):
    tenants, total = await tenant_service.list_tenants(session, page, page_size)
    return Page(
        data=[TenantResponse.model_validate(t) for t in tenants],
        meta=PageMeta(
            page=page,
            page_size=page_size,
            total_items=total,
            total_pages=max(1, math.ceil(total / page_size)),
        ),
    )


@router.post("", response_model=SuccessResponse[TenantResponse], status_code=201)
async def create_tenant(
    payload: TenantCreateRequest,
    request: Request,
    context: SecurityContext = Depends(require_permission("tenants.create")),
    session: AsyncSession = Depends(get_db),
):
    tenant = await tenant_service.create_tenant(session, context, payload, request)
    return SuccessResponse(data=TenantResponse.model_validate(tenant))


@router.get("/{tenant_id}", response_model=SuccessResponse[TenantResponse])
async def get_tenant(
    tenant_id: uuid.UUID,
    _context: SecurityContext = Depends(require_permission("tenants.view")),
    session: AsyncSession = Depends(get_db),
):
    tenant = await tenant_service.get_tenant(session, tenant_id)
    return SuccessResponse(data=TenantResponse.model_validate(tenant))


@router.patch("/{tenant_id}", response_model=SuccessResponse[TenantResponse])
async def update_tenant(
    tenant_id: uuid.UUID,
    payload: TenantUpdateRequest,
    request: Request,
    context: SecurityContext = Depends(require_permission("tenants.update")),
    session: AsyncSession = Depends(get_db),
):
    tenant = await tenant_service.update_tenant(session, context, tenant_id, payload, request)
    return SuccessResponse(data=TenantResponse.model_validate(tenant))


@router.post("/{tenant_id}/suspend", response_model=SuccessResponse[TenantResponse])
async def suspend_tenant(
    tenant_id: uuid.UUID,
    request: Request,
    context: SecurityContext = Depends(require_permission("tenants.update")),
    session: AsyncSession = Depends(get_db),
):
    tenant = await tenant_service.suspend_tenant(session, context, tenant_id, request)
    return SuccessResponse(data=TenantResponse.model_validate(tenant))
