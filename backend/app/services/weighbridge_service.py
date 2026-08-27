"""Weighbridge ticket lifecycle.

Every state change is authorized through `authorization_service.authorize()` rather than just
the coarser `require_permission` route dependency, because a plant manager's grant should only
cover their own plant's weighbridge — the whole point of scope-based authorization
(see docs/authorization.md). `require_permission` still gates the route first as a cheap "can
this user do this at all" check; `authorize()` then checks it against the *specific* ticket's
`organization_unit_id`.
"""

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.models.audit import AuditAction
from app.models.enums import WeighbridgeTicketStatus
from app.models.weighbridge import WeighbridgeTicket
from app.repositories import fiscal_year_repository, weighbridge_repository
from app.schemas.weighbridge import (
    WeighbridgeTicketCompleteRequest,
    WeighbridgeTicketCreateRequest,
)
from app.security.security_context import SecurityContext
from app.services import audit_service, authorization_service, numbering_service

_DOCUMENT_TYPE = "WEIGHBRIDGE_TICKET"
_TICKET_PREFIX = "WBT"


async def list_tickets(
    session: AsyncSession,
    context: SecurityContext,
    page: int,
    page_size: int,
    status: WeighbridgeTicketStatus | None,
) -> tuple[list[WeighbridgeTicket], int]:
    if context.tenant_id is None:
        raise ForbiddenError("Platform users must access weighbridge data through a tenant.")
    return await weighbridge_repository.list_in_tenant(
        session, context.tenant_id, offset=(page - 1) * page_size, limit=page_size, status=status
    )


async def get_ticket(
    session: AsyncSession, context: SecurityContext, ticket_id: uuid.UUID
) -> WeighbridgeTicket:
    if context.tenant_id is None:
        raise ForbiddenError("Platform users must access weighbridge data through a tenant.")
    ticket = await weighbridge_repository.get_by_id_in_tenant(session, ticket_id, context.tenant_id)
    if ticket is None:
        raise NotFoundError("Weighbridge ticket not found.")
    return ticket


async def create_ticket(
    session: AsyncSession,
    context: SecurityContext,
    payload: WeighbridgeTicketCreateRequest,
    request: Request | None,
) -> WeighbridgeTicket:
    if context.tenant_id is None:
        raise ForbiddenError("Platform users must access weighbridge data through a tenant.")

    await authorization_service.authorize(
        session, context, "weighbridge.create", payload.organization_unit_id
    )

    fiscal_year = await fiscal_year_repository.get_active_for_tenant(session, context.tenant_id)
    if fiscal_year is None:
        raise ConflictError(
            "No active fiscal year is configured for this tenant. An administrator must set one "
            "up before recording weighbridge tickets."
        )

    ticket_number = await numbering_service.next_number(
        session,
        tenant_id=context.tenant_id,
        document_type=_DOCUMENT_TYPE,
        fiscal_year_code=fiscal_year.code,
        prefix=_TICKET_PREFIX,
        organization_unit_id=payload.organization_unit_id,
    )

    ticket = WeighbridgeTicket(
        tenant_id=context.tenant_id,
        organization_unit_id=payload.organization_unit_id,
        unit_id=payload.unit_id,
        ticket_number=ticket_number,
        ticket_type=payload.ticket_type,
        status=WeighbridgeTicketStatus.OPEN,
        vehicle_number=payload.vehicle_number.upper(),
        driver_name=payload.driver_name,
        party_name=payload.party_name,
        material_description=payload.material_description,
        first_weight=payload.first_weight,
        first_weighed_at=datetime.now(UTC),
        remarks=payload.remarks,
        created_by=context.user.id,
    )
    weighbridge_repository.add(session, ticket)
    await session.flush()

    await audit_service.record(
        session,
        action=AuditAction.WEIGHBRIDGE_TICKET_CREATED.value,
        resource_type="weighbridge_ticket",
        resource_id=str(ticket.id),
        tenant_id=context.tenant_id,
        user_id=context.user.id,
        new_data={"ticket_number": ticket.ticket_number, "ticket_type": ticket.ticket_type.value},
        request=request,
    )
    await session.commit()
    return ticket


async def complete_ticket(
    session: AsyncSession,
    context: SecurityContext,
    ticket_id: uuid.UUID,
    payload: WeighbridgeTicketCompleteRequest,
    request: Request | None,
) -> WeighbridgeTicket:
    ticket = await get_ticket(session, context, ticket_id)
    await authorization_service.authorize(
        session, context, "weighbridge.update", ticket.organization_unit_id
    )

    if ticket.status != WeighbridgeTicketStatus.OPEN:
        raise ConflictError(f"Ticket is {ticket.status.value.lower()}, not open.")

    net_weight: Decimal = abs(ticket.first_weight - payload.second_weight)

    ticket.second_weight = payload.second_weight
    ticket.second_weighed_at = datetime.now(UTC)
    ticket.net_weight = net_weight
    ticket.status = WeighbridgeTicketStatus.COMPLETED
    ticket.updated_by = context.user.id

    await session.flush()
    await audit_service.record(
        session,
        action=AuditAction.WEIGHBRIDGE_TICKET_COMPLETED.value,
        resource_type="weighbridge_ticket",
        resource_id=str(ticket.id),
        tenant_id=context.tenant_id,
        user_id=context.user.id,
        new_data={"net_weight": str(net_weight)},
        request=request,
    )
    await session.commit()
    return ticket


async def cancel_ticket(
    session: AsyncSession,
    context: SecurityContext,
    ticket_id: uuid.UUID,
    request: Request | None,
) -> WeighbridgeTicket:
    ticket = await get_ticket(session, context, ticket_id)
    await authorization_service.authorize(
        session, context, "weighbridge.update", ticket.organization_unit_id
    )

    if ticket.status == WeighbridgeTicketStatus.COMPLETED:
        raise ConflictError("A completed ticket cannot be cancelled.")

    ticket.status = WeighbridgeTicketStatus.CANCELLED
    ticket.updated_by = context.user.id
    await session.flush()

    await audit_service.record(
        session,
        action=AuditAction.WEIGHBRIDGE_TICKET_CANCELLED.value,
        resource_type="weighbridge_ticket",
        resource_id=str(ticket.id),
        tenant_id=context.tenant_id,
        user_id=context.user.id,
        request=request,
    )
    await session.commit()
    return ticket
