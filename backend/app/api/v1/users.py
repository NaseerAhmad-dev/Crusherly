import math
import uuid

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.common import MessageResponse, Page, PageMeta, SuccessResponse
from app.schemas.user import (
    RoleAssignmentRequest,
    UserCreateRequest,
    UserResponse,
    UserRoleResponse,
    UserUpdateRequest,
)
from app.security.dependencies import require_permission
from app.security.security_context import SecurityContext
from app.services import user_service

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=Page[UserResponse])
async def list_users(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    search: str | None = Query(default=None),
    context: SecurityContext = Depends(require_permission("users.view")),
    session: AsyncSession = Depends(get_db),
):
    users, total = await user_service.list_users(session, context, page, page_size, search)
    return Page(
        data=[UserResponse.model_validate(u) for u in users],
        meta=PageMeta(
            page=page,
            page_size=page_size,
            total_items=total,
            total_pages=max(1, math.ceil(total / page_size)),
        ),
    )


@router.post("", response_model=SuccessResponse[UserResponse], status_code=201)
async def create_user(
    payload: UserCreateRequest,
    request: Request,
    context: SecurityContext = Depends(require_permission("users.create")),
    session: AsyncSession = Depends(get_db),
):
    user = await user_service.create_user(session, context, payload, request)
    return SuccessResponse(data=UserResponse.model_validate(user))


@router.get("/{user_id}", response_model=SuccessResponse[UserResponse])
async def get_user(
    user_id: uuid.UUID,
    context: SecurityContext = Depends(require_permission("users.view")),
    session: AsyncSession = Depends(get_db),
):
    user = await user_service.get_user(session, context, user_id)
    return SuccessResponse(data=UserResponse.model_validate(user))


@router.patch("/{user_id}", response_model=SuccessResponse[UserResponse])
async def update_user(
    user_id: uuid.UUID,
    payload: UserUpdateRequest,
    request: Request,
    context: SecurityContext = Depends(require_permission("users.update")),
    session: AsyncSession = Depends(get_db),
):
    user = await user_service.update_user(session, context, user_id, payload, request)
    return SuccessResponse(data=UserResponse.model_validate(user))


@router.delete("/{user_id}", response_model=MessageResponse)
async def deactivate_user(
    user_id: uuid.UUID,
    request: Request,
    context: SecurityContext = Depends(require_permission("users.delete")),
    session: AsyncSession = Depends(get_db),
):
    await user_service.deactivate_user(session, context, user_id, request)
    return MessageResponse(message="User deactivated.")


@router.post(
    "/{user_id}/role-assignments",
    response_model=SuccessResponse[UserRoleResponse],
    status_code=201,
)
async def assign_role(
    user_id: uuid.UUID,
    payload: RoleAssignmentRequest,
    request: Request,
    context: SecurityContext = Depends(require_permission("users.update")),
    session: AsyncSession = Depends(get_db),
):
    user_role = await user_service.assign_role(
        session, context, user_id, payload.role_id, payload.organization_unit_id, request
    )
    return SuccessResponse(
        data=UserRoleResponse(
            id=user_role.id,
            role_id=user_role.role_id,
            role_code=user_role.role.code,
            organization_unit_id=user_role.organization_unit_id,
        )
    )
