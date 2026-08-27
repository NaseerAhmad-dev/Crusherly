from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.repositories import unit_repository
from app.schemas.common import SuccessResponse
from app.schemas.unit import UnitResponse
from app.security.dependencies import require_authenticated_user
from app.security.security_context import SecurityContext

router = APIRouter(prefix="/units", tags=["units"])


@router.get("", response_model=SuccessResponse[list[UnitResponse]])
async def list_units(
    _context: SecurityContext = Depends(require_authenticated_user),
    session: AsyncSession = Depends(get_db),
):
    """Global reference data (not tenant-scoped) — any authenticated user may look up the unit
    vocabulary to populate a picker, same as they would any other dropdown of allowed values."""
    units = await unit_repository.list_all(session)
    return SuccessResponse(data=[UnitResponse.model_validate(u) for u in units])
