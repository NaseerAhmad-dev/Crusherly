from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.common import SuccessResponse
from app.schemas.role import PermissionResponse
from app.security.dependencies import require_permission
from app.security.security_context import SecurityContext
from app.services import permission_service

router = APIRouter(prefix="/permissions", tags=["permissions"])


@router.get("", response_model=SuccessResponse[list[PermissionResponse]])
async def list_permissions(
    _context: SecurityContext = Depends(require_permission("permissions.view")),
    session: AsyncSession = Depends(get_db),
):
    permissions = await permission_service.list_permissions(session)
    return SuccessResponse(data=[PermissionResponse.model_validate(p) for p in permissions])
