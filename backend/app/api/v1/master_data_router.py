"""Builds a standard list/create/get/update/deactivate router for any master-data entity.

Every concrete master-data module (see `app/api/v1/materials.py`) calls `build_master_data_router()`
once with its own schemas, permission prefix, and `MasterDataService` instance, instead of hand
writing five near-identical route functions. This is the API-layer half of the same "don't
duplicate CRUD architecture" pattern `MasterDataRepository`/`MasterDataService` implement for the
repository/service layers.
"""

import math
import uuid
from typing import Any

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.common import Page, PageMeta, SuccessResponse
from app.security.dependencies import require_permission
from app.security.security_context import SecurityContext
from app.services.master_data_service import MasterDataService


def build_master_data_router(
    *,
    prefix: str,
    tags: list[str],
    permission_prefix: str,
    create_schema: type[BaseModel],
    update_schema: type[BaseModel],
    response_schema: type[BaseModel],
    service: MasterDataService[Any],
) -> APIRouter:
    router = APIRouter(prefix=prefix, tags=tags)
    view_permission = f"{permission_prefix}.view"
    create_permission = f"{permission_prefix}.create"
    update_permission = f"{permission_prefix}.update"

    @router.get("", response_model=Page[response_schema])
    async def list_items(
        page: int = Query(default=1, ge=1),
        page_size: int = Query(default=20, ge=1, le=200),
        search: str | None = Query(default=None),
        context: SecurityContext = Depends(require_permission(view_permission)),
        session: AsyncSession = Depends(get_db),
    ):
        items, total = await service.list(session, context, page, page_size, search)
        return Page(
            data=[response_schema.model_validate(item) for item in items],
            meta=PageMeta(
                page=page,
                page_size=page_size,
                total_items=total,
                total_pages=max(1, math.ceil(total / page_size)),
            ),
        )

    @router.post("", response_model=SuccessResponse[response_schema], status_code=201)
    async def create_item(
        payload: create_schema,
        request: Request,
        context: SecurityContext = Depends(require_permission(create_permission)),
        session: AsyncSession = Depends(get_db),
    ):
        item = await service.create(session, context, payload, request)
        return SuccessResponse(data=response_schema.model_validate(item))

    @router.get("/{item_id}", response_model=SuccessResponse[response_schema])
    async def get_item(
        item_id: uuid.UUID,
        context: SecurityContext = Depends(require_permission(view_permission)),
        session: AsyncSession = Depends(get_db),
    ):
        item = await service.get(session, context, item_id)
        return SuccessResponse(data=response_schema.model_validate(item))

    @router.patch("/{item_id}", response_model=SuccessResponse[response_schema])
    async def update_item(
        item_id: uuid.UUID,
        payload: update_schema,
        request: Request,
        context: SecurityContext = Depends(require_permission(update_permission)),
        session: AsyncSession = Depends(get_db),
    ):
        item = await service.update(session, context, item_id, payload, request)
        return SuccessResponse(data=response_schema.model_validate(item))

    @router.post("/{item_id}/deactivate", response_model=SuccessResponse[response_schema])
    async def deactivate_item(
        item_id: uuid.UUID,
        request: Request,
        context: SecurityContext = Depends(require_permission(update_permission)),
        session: AsyncSession = Depends(get_db),
    ):
        item = await service.deactivate(session, context, item_id, request)
        return SuccessResponse(data=response_schema.model_validate(item))

    return router
