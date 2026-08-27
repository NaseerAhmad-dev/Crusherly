import math
import uuid

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.enums import WeighbridgeTicketStatus
from app.schemas.common import Page, PageMeta, SuccessResponse
from app.schemas.weighbridge import (
    WeighbridgeTicketCompleteRequest,
    WeighbridgeTicketCreateRequest,
    WeighbridgeTicketResponse,
)
from app.security.dependencies import require_permission
from app.security.security_context import SecurityContext
from app.services import weighbridge_service

router = APIRouter(prefix="/weighbridge/tickets", tags=["weighbridge"])


@router.get("", response_model=Page[WeighbridgeTicketResponse])
async def list_tickets(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    status: WeighbridgeTicketStatus | None = Query(default=None),
    context: SecurityContext = Depends(require_permission("weighbridge.view")),
    session: AsyncSession = Depends(get_db),
):
    tickets, total = await weighbridge_service.list_tickets(
        session, context, page, page_size, status
    )
    return Page(
        data=[WeighbridgeTicketResponse.model_validate(t) for t in tickets],
        meta=PageMeta(
            page=page,
            page_size=page_size,
            total_items=total,
            total_pages=max(1, math.ceil(total / page_size)),
        ),
    )


@router.post("", response_model=SuccessResponse[WeighbridgeTicketResponse], status_code=201)
async def create_ticket(
    payload: WeighbridgeTicketCreateRequest,
    request: Request,
    context: SecurityContext = Depends(require_permission("weighbridge.create")),
    session: AsyncSession = Depends(get_db),
):
    ticket = await weighbridge_service.create_ticket(session, context, payload, request)
    return SuccessResponse(data=WeighbridgeTicketResponse.model_validate(ticket))


@router.get("/{ticket_id}", response_model=SuccessResponse[WeighbridgeTicketResponse])
async def get_ticket(
    ticket_id: uuid.UUID,
    context: SecurityContext = Depends(require_permission("weighbridge.view")),
    session: AsyncSession = Depends(get_db),
):
    ticket = await weighbridge_service.get_ticket(session, context, ticket_id)
    return SuccessResponse(data=WeighbridgeTicketResponse.model_validate(ticket))


@router.post("/{ticket_id}/complete", response_model=SuccessResponse[WeighbridgeTicketResponse])
async def complete_ticket(
    ticket_id: uuid.UUID,
    payload: WeighbridgeTicketCompleteRequest,
    request: Request,
    context: SecurityContext = Depends(require_permission("weighbridge.update")),
    session: AsyncSession = Depends(get_db),
):
    ticket = await weighbridge_service.complete_ticket(
        session, context, ticket_id, payload, request
    )
    return SuccessResponse(data=WeighbridgeTicketResponse.model_validate(ticket))


@router.post("/{ticket_id}/cancel", response_model=SuccessResponse[WeighbridgeTicketResponse])
async def cancel_ticket(
    ticket_id: uuid.UUID,
    request: Request,
    context: SecurityContext = Depends(require_permission("weighbridge.update")),
    session: AsyncSession = Depends(get_db),
):
    ticket = await weighbridge_service.cancel_ticket(session, context, ticket_id, request)
    return SuccessResponse(data=WeighbridgeTicketResponse.model_validate(ticket))
