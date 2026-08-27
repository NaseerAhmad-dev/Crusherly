"""Foundation dashboard only (Master Build Specification section 36).

Business dashboards (production/sales/inventory/etc.) are explicitly out of scope until
Phase 11 — Reporting/Analytics.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import ForbiddenError
from app.models.enums import TenantStatus, UserStatus
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.common import SuccessResponse
from app.schemas.dashboard import PlatformDashboardResponse, TenantDashboardResponse
from app.security.dependencies import require_permission
from app.security.security_context import SecurityContext

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/platform", response_model=SuccessResponse[PlatformDashboardResponse])
async def platform_dashboard(
    context: SecurityContext = Depends(require_permission("dashboard.view")),
    session: AsyncSession = Depends(get_db),
):
    if not context.is_platform_user:
        raise ForbiddenError("The platform dashboard is only available to platform-level users.")

    total_tenants = (await session.execute(select(func.count()).select_from(Tenant))).scalar_one()
    active_tenants = (
        await session.execute(
            select(func.count()).select_from(Tenant).where(Tenant.status == TenantStatus.ACTIVE)
        )
    ).scalar_one()
    total_users = (await session.execute(select(func.count()).select_from(User))).scalar_one()

    return SuccessResponse(
        data=PlatformDashboardResponse(
            total_tenants=total_tenants,
            active_tenants=active_tenants,
            total_users=total_users,
            system_status="ok",
        )
    )


@router.get("/tenant", response_model=SuccessResponse[TenantDashboardResponse])
async def tenant_dashboard(
    context: SecurityContext = Depends(require_permission("dashboard.view")),
    session: AsyncSession = Depends(get_db),
):
    if context.tenant_id is None:
        raise ForbiddenError("The tenant dashboard requires a tenant context.")

    from app.models.enums import OrganizationUnitType
    from app.models.organization import OrganizationUnit

    total_plants = (
        await session.execute(
            select(func.count())
            .select_from(OrganizationUnit)
            .where(
                OrganizationUnit.tenant_id == context.tenant_id,
                OrganizationUnit.unit_type == OrganizationUnitType.PLANT,
            )
        )
    ).scalar_one()
    total_users = (
        await session.execute(
            select(func.count()).select_from(User).where(User.tenant_id == context.tenant_id)
        )
    ).scalar_one()
    active_users = (
        await session.execute(
            select(func.count())
            .select_from(User)
            .where(User.tenant_id == context.tenant_id, User.status == UserStatus.ACTIVE)
        )
    ).scalar_one()

    return SuccessResponse(
        data=TenantDashboardResponse(
            total_plants=total_plants, total_users=total_users, active_users=active_users
        )
    )
