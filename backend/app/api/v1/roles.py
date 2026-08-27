import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.common import MessageResponse, SuccessResponse
from app.schemas.role import (
    RoleCreateRequest,
    RolePermissionsUpdateRequest,
    RoleResponse,
    RoleUpdateRequest,
)
from app.security.dependencies import require_permission
from app.security.security_context import SecurityContext
from app.services import role_service

router = APIRouter(prefix="/roles", tags=["roles"])


def _to_response(role) -> RoleResponse:
    return RoleResponse(
        id=role.id,
        tenant_id=role.tenant_id,
        code=role.code,
        name=role.name,
        description=role.description,
        is_system=role.is_system,
        permission_codes=sorted(rp.permission.code for rp in role.role_permissions),
    )


@router.get("", response_model=SuccessResponse[list[RoleResponse]])
async def list_roles(
    context: SecurityContext = Depends(require_permission("roles.view")),
    session: AsyncSession = Depends(get_db),
):
    roles = await role_service.list_roles(session, context)
    return SuccessResponse(data=[_to_response(r) for r in roles])


@router.post("", response_model=SuccessResponse[RoleResponse], status_code=201)
async def create_role(
    payload: RoleCreateRequest,
    request: Request,
    context: SecurityContext = Depends(require_permission("roles.create")),
    session: AsyncSession = Depends(get_db),
):
    role = await role_service.create_role(session, context, payload, request)
    return SuccessResponse(data=_to_response(role))


@router.get("/{role_id}", response_model=SuccessResponse[RoleResponse])
async def get_role(
    role_id: uuid.UUID,
    context: SecurityContext = Depends(require_permission("roles.view")),
    session: AsyncSession = Depends(get_db),
):
    role = await role_service.get_role(session, context, role_id)
    return SuccessResponse(data=_to_response(role))


@router.patch("/{role_id}", response_model=SuccessResponse[RoleResponse])
async def update_role(
    role_id: uuid.UUID,
    payload: RoleUpdateRequest,
    request: Request,
    context: SecurityContext = Depends(require_permission("roles.update")),
    session: AsyncSession = Depends(get_db),
):
    role = await role_service.update_role(session, context, role_id, payload, request)
    return SuccessResponse(data=_to_response(role))


@router.put("/{role_id}/permissions", response_model=SuccessResponse[RoleResponse])
async def update_role_permissions(
    role_id: uuid.UUID,
    payload: RolePermissionsUpdateRequest,
    request: Request,
    context: SecurityContext = Depends(require_permission("roles.update")),
    session: AsyncSession = Depends(get_db),
):
    role = await role_service.update_role_permissions(
        session, context, role_id, payload.permission_codes, request
    )
    return SuccessResponse(data=_to_response(role))


@router.delete("/{role_id}", response_model=MessageResponse)
async def delete_role(
    role_id: uuid.UUID,
    request: Request,
    context: SecurityContext = Depends(require_permission("roles.delete")),
    session: AsyncSession = Depends(get_db),
):
    await role_service.delete_role(session, context, role_id, request)
    return MessageResponse(message="Role deleted.")
