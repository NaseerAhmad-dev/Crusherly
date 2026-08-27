"""Read-only audit trail. No route here ever updates or deletes an AuditEvent (append-only)."""

import math
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.repositories import audit_repository
from app.schemas.audit import AuditEventResponse
from app.schemas.common import Page, PageMeta
from app.security.dependencies import require_permission
from app.security.security_context import SecurityContext

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("", response_model=Page[AuditEventResponse])
async def list_audit_events(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    action: str | None = Query(default=None),
    resource_type: str | None = Query(default=None),
    user_id: uuid.UUID | None = Query(default=None),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    context: SecurityContext = Depends(require_permission("audit.view")),
    session: AsyncSession = Depends(get_db),
):
    # Tenant-scoped users only ever see their own tenant's audit trail; platform users (no
    # tenant_id) with audit.view see the platform-wide trail — this mirrors how tenants.view
    # naturally separates platform vs. tenant administration.
    events, total = await audit_repository.list_events(
        session,
        tenant_id=context.tenant_id,
        offset=(page - 1) * page_size,
        limit=page_size,
        action=action,
        resource_type=resource_type,
        user_id=user_id,
        date_from=date_from,
        date_to=date_to,
    )
    return Page(
        data=[AuditEventResponse.model_validate(e) for e in events],
        meta=PageMeta(
            page=page,
            page_size=page_size,
            total_items=total,
            total_pages=max(1, math.ceil(total / page_size)),
        ),
    )
