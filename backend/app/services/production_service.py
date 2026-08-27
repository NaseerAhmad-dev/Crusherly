"""Production entry lifecycle.

Same authorization pattern as weighbridge_service: `require_permission` gates the route, then
`authorization_service.authorize()` checks the *specific* entry's `organization_unit_id` — a
plant manager's grant should only cover their own plant's production, not the whole tenant's.
"""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.models.audit import AuditAction
from app.models.enums import ProductionEntryStatus
from app.models.production import ProductionEntry, ProductionOutput
from app.repositories import fiscal_year_repository, production_repository
from app.schemas.production import ProductionEntryCreateRequest
from app.security.security_context import SecurityContext
from app.services import audit_service, authorization_service, numbering_service

_DOCUMENT_TYPE = "PRODUCTION_ENTRY"
_ENTRY_PREFIX = "PRD"


async def list_entries(
    session: AsyncSession,
    context: SecurityContext,
    page: int,
    page_size: int,
    status: ProductionEntryStatus | None,
) -> tuple[list[ProductionEntry], int]:
    if context.tenant_id is None:
        raise ForbiddenError("Platform users must access production data through a tenant.")
    return await production_repository.list_in_tenant(
        session, context.tenant_id, offset=(page - 1) * page_size, limit=page_size, status=status
    )


async def get_entry(
    session: AsyncSession, context: SecurityContext, entry_id: uuid.UUID
) -> ProductionEntry:
    if context.tenant_id is None:
        raise ForbiddenError("Platform users must access production data through a tenant.")
    entry = await production_repository.get_by_id_in_tenant(session, entry_id, context.tenant_id)
    if entry is None:
        raise NotFoundError("Production entry not found.")
    return entry


async def create_entry(
    session: AsyncSession,
    context: SecurityContext,
    payload: ProductionEntryCreateRequest,
    request: Request | None,
) -> ProductionEntry:
    if context.tenant_id is None:
        raise ForbiddenError("Platform users must access production data through a tenant.")

    await authorization_service.authorize(
        session, context, "production.create", payload.organization_unit_id
    )

    fiscal_year = await fiscal_year_repository.get_active_for_tenant(session, context.tenant_id)
    if fiscal_year is None:
        raise ConflictError(
            "No active fiscal year is configured for this tenant. An administrator must set one "
            "up before recording production entries."
        )

    entry_number = await numbering_service.next_number(
        session,
        tenant_id=context.tenant_id,
        document_type=_DOCUMENT_TYPE,
        fiscal_year_code=fiscal_year.code,
        prefix=_ENTRY_PREFIX,
        organization_unit_id=payload.organization_unit_id,
    )

    entry = ProductionEntry(
        tenant_id=context.tenant_id,
        organization_unit_id=payload.organization_unit_id,
        raw_material_unit_id=payload.raw_material_unit_id,
        entry_number=entry_number,
        production_date=payload.production_date,
        shift=payload.shift,
        status=ProductionEntryStatus.DRAFT,
        raw_material_description=payload.raw_material_description,
        raw_material_quantity=payload.raw_material_quantity,
        remarks=payload.remarks,
        created_by=context.user.id,
        outputs=[
            ProductionOutput(
                product_description=output.product_description,
                quantity=output.quantity,
                unit_id=output.unit_id,
            )
            for output in payload.outputs
        ],
    )
    production_repository.add(session, entry)
    await session.flush()

    await audit_service.record(
        session,
        action=AuditAction.PRODUCTION_ENTRY_CREATED.value,
        resource_type="production_entry",
        resource_id=str(entry.id),
        tenant_id=context.tenant_id,
        user_id=context.user.id,
        new_data={"entry_number": entry.entry_number, "output_count": len(entry.outputs)},
        request=request,
    )
    await session.commit()
    return entry


async def submit_entry(
    session: AsyncSession,
    context: SecurityContext,
    entry_id: uuid.UUID,
    request: Request | None,
) -> ProductionEntry:
    entry = await get_entry(session, context, entry_id)
    await authorization_service.authorize(
        session, context, "production.update", entry.organization_unit_id
    )

    if entry.status != ProductionEntryStatus.DRAFT:
        raise ConflictError(f"Entry is {entry.status.value.lower()}, not draft.")

    entry.status = ProductionEntryStatus.SUBMITTED
    entry.updated_by = context.user.id
    await session.flush()

    await audit_service.record(
        session,
        action=AuditAction.PRODUCTION_ENTRY_SUBMITTED.value,
        resource_type="production_entry",
        resource_id=str(entry.id),
        tenant_id=context.tenant_id,
        user_id=context.user.id,
        request=request,
    )
    await session.commit()
    return entry


async def cancel_entry(
    session: AsyncSession,
    context: SecurityContext,
    entry_id: uuid.UUID,
    request: Request | None,
) -> ProductionEntry:
    entry = await get_entry(session, context, entry_id)
    await authorization_service.authorize(
        session, context, "production.update", entry.organization_unit_id
    )

    if entry.status == ProductionEntryStatus.CANCELLED:
        raise ConflictError("Entry is already cancelled.")

    entry.status = ProductionEntryStatus.CANCELLED
    entry.updated_by = context.user.id
    await session.flush()

    await audit_service.record(
        session,
        action=AuditAction.PRODUCTION_ENTRY_CANCELLED.value,
        resource_type="production_entry",
        resource_id=str(entry.id),
        tenant_id=context.tenant_id,
        user_id=context.user.id,
        request=request,
    )
    await session.commit()
    return entry
