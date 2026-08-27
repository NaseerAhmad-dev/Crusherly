from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import ForbiddenError
from app.repositories import organization_repository
from app.schemas.common import SuccessResponse
from app.schemas.organization import OrganizationUnitResponse
from app.security.dependencies import require_authenticated_user
from app.security.security_context import SecurityContext

router = APIRouter(prefix="/organization-units", tags=["organization-units"])


@router.get("", response_model=SuccessResponse[list[OrganizationUnitResponse]])
async def list_organization_units(
    context: SecurityContext = Depends(require_authenticated_user),
    session: AsyncSession = Depends(get_db),
):
    """Every organization unit in the caller's own tenant — used to populate pickers (e.g. "which
    plant") on business-module create forms. Platform users have no tenant to scope this to."""
    if context.tenant_id is None:
        raise ForbiddenError("Platform users must access organization data through a tenant.")
    units = await organization_repository.list_for_tenant(session, context.tenant_id)
    return SuccessResponse(data=[OrganizationUnitResponse.model_validate(u) for u in units])
