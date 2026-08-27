import math
import uuid

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.enums import ProductionEntryStatus
from app.schemas.common import Page, PageMeta, SuccessResponse
from app.schemas.production import ProductionEntryCreateRequest, ProductionEntryResponse
from app.security.dependencies import require_permission
from app.security.security_context import SecurityContext
from app.services import production_service

router = APIRouter(prefix="/production/entries", tags=["production"])


@router.get("", response_model=Page[ProductionEntryResponse])
async def list_entries(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    status: ProductionEntryStatus | None = Query(default=None),
    context: SecurityContext = Depends(require_permission("production.view")),
    session: AsyncSession = Depends(get_db),
):
    entries, total = await production_service.list_entries(
        session, context, page, page_size, status
    )
    return Page(
        data=[ProductionEntryResponse.model_validate(e) for e in entries],
        meta=PageMeta(
            page=page,
            page_size=page_size,
            total_items=total,
            total_pages=max(1, math.ceil(total / page_size)),
        ),
    )


@router.post("", response_model=SuccessResponse[ProductionEntryResponse], status_code=201)
async def create_entry(
    payload: ProductionEntryCreateRequest,
    request: Request,
    context: SecurityContext = Depends(require_permission("production.create")),
    session: AsyncSession = Depends(get_db),
):
    entry = await production_service.create_entry(session, context, payload, request)
    return SuccessResponse(data=ProductionEntryResponse.model_validate(entry))


@router.get("/{entry_id}", response_model=SuccessResponse[ProductionEntryResponse])
async def get_entry(
    entry_id: uuid.UUID,
    context: SecurityContext = Depends(require_permission("production.view")),
    session: AsyncSession = Depends(get_db),
):
    entry = await production_service.get_entry(session, context, entry_id)
    return SuccessResponse(data=ProductionEntryResponse.model_validate(entry))


@router.post("/{entry_id}/submit", response_model=SuccessResponse[ProductionEntryResponse])
async def submit_entry(
    entry_id: uuid.UUID,
    request: Request,
    context: SecurityContext = Depends(require_permission("production.update")),
    session: AsyncSession = Depends(get_db),
):
    entry = await production_service.submit_entry(session, context, entry_id, request)
    return SuccessResponse(data=ProductionEntryResponse.model_validate(entry))


@router.post("/{entry_id}/cancel", response_model=SuccessResponse[ProductionEntryResponse])
async def cancel_entry(
    entry_id: uuid.UUID,
    request: Request,
    context: SecurityContext = Depends(require_permission("production.update")),
    session: AsyncSession = Depends(get_db),
):
    entry = await production_service.cancel_entry(session, context, entry_id, request)
    return SuccessResponse(data=ProductionEntryResponse.model_validate(entry))
