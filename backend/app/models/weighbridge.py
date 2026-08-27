"""Weighbridge tickets — Phase 1's first business module.

A ticket records the two weighments every truck goes through at a stone-crushing plant: a first
reading when it arrives, and a second reading once its load has been handled. Net weight is the
difference between the two, computed once both exist (see `app/services/weighbridge_service.py`).

This module is built entirely on the Phase 0 foundation rather than inventing its own plumbing:
`numbering_service` issues the ticket number, `OrganizationUnit` records which plant it happened
at (and is what scope-based authorization checks against — see docs/authorization.md), `Unit`
supplies the weight unit, and every state change goes through `audit_service`.
"""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import (
    AuditedByMixin,
    TenantScopedMixin,
    TimestampMixin,
    UTCDateTime,
    UUIDPrimaryKeyMixin,
)
from app.models.enums import WeighbridgeTicketStatus, WeighbridgeTicketType


class WeighbridgeTicket(
    UUIDPrimaryKeyMixin, TenantScopedMixin, AuditedByMixin, TimestampMixin, Base
):
    __tablename__ = "weighbridge_tickets"

    organization_unit_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("organization_units.id", ondelete="SET NULL"), nullable=True, index=True
    )
    unit_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("units.id", ondelete="RESTRICT"), nullable=False
    )

    ticket_number: Mapped[str] = mapped_column(String(50), nullable=False)
    ticket_type: Mapped[WeighbridgeTicketType] = mapped_column(
        SAEnum(WeighbridgeTicketType, name="weighbridge_ticket_type"), nullable=False
    )
    status: Mapped[WeighbridgeTicketStatus] = mapped_column(
        SAEnum(WeighbridgeTicketStatus, name="weighbridge_ticket_status"),
        nullable=False,
        default=WeighbridgeTicketStatus.OPEN,
    )

    vehicle_number: Mapped[str] = mapped_column(String(20), nullable=False)
    driver_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    party_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    material_description: Mapped[str] = mapped_column(String(200), nullable=False)

    first_weight: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    first_weighed_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    second_weight: Mapped[Decimal | None] = mapped_column(Numeric(12, 3), nullable=True)
    second_weighed_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    net_weight: Mapped[Decimal | None] = mapped_column(Numeric(12, 3), nullable=True)

    remarks: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        # Ticket numbers are only unique within a tenant — numbering_service scopes sequences
        # per (tenant, organization unit, document type, fiscal year), so two tenants (or two
        # fiscal years) can legitimately produce the same number.
        UniqueConstraint("tenant_id", "ticket_number", name="uq_weighbridge_ticket_number"),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<WeighbridgeTicket {self.ticket_number} ({self.status.value})>"
