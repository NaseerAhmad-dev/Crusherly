"""Production entries — Phase 3's business module (no Phase 2 was requested; see
docs/phases/phase-3-completion.md for why the numbering has a gap).

A `ProductionEntry` records one plant's one shift of crushing: the raw material consumed and the
graded outputs it produced (e.g. 50 tons of 40mm aggregate, 30 tons of 20mm, 10 tons of dust from
one shift's input). Outputs are a one-to-many child table, not a single quantity, because a real
crushing run always grades its output into more than one product.

Like `WeighbridgeTicket`, material and product descriptions are free text rather than foreign keys
to a Vehicle/Product master — those modules don't exist yet, and denormalizing now versus adding a
speculative master-data table nobody else references yet is the same trade-off Weighbridge already
made (see docs/weighbridge.md).
"""

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import (
    AuditedByMixin,
    TenantScopedMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)
from app.models.enums import ProductionEntryStatus, ProductionShift


class ProductionEntry(UUIDPrimaryKeyMixin, TenantScopedMixin, AuditedByMixin, TimestampMixin, Base):
    __tablename__ = "production_entries"

    organization_unit_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("organization_units.id", ondelete="SET NULL"), nullable=True, index=True
    )
    raw_material_unit_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("units.id", ondelete="RESTRICT"), nullable=False
    )

    entry_number: Mapped[str] = mapped_column(String(50), nullable=False)
    production_date: Mapped[date] = mapped_column(Date, nullable=False)
    shift: Mapped[ProductionShift] = mapped_column(
        SAEnum(ProductionShift, name="production_shift"), nullable=False
    )
    status: Mapped[ProductionEntryStatus] = mapped_column(
        SAEnum(ProductionEntryStatus, name="production_entry_status"),
        nullable=False,
        default=ProductionEntryStatus.DRAFT,
    )

    raw_material_description: Mapped[str] = mapped_column(String(200), nullable=False)
    raw_material_quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)

    remarks: Mapped[str | None] = mapped_column(Text, nullable=True)

    outputs: Mapped[list["ProductionOutput"]] = relationship(
        back_populates="entry", cascade="all, delete-orphan", order_by="ProductionOutput.created_at"
    )

    __table_args__ = (
        # Only unique within a tenant — see WeighbridgeTicket.ticket_number for why.
        UniqueConstraint("tenant_id", "entry_number", name="uq_production_entry_number"),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<ProductionEntry {self.entry_number} ({self.status.value})>"


class ProductionOutput(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "production_outputs"

    production_entry_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("production_entries.id", ondelete="CASCADE"), nullable=False, index=True
    )
    unit_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("units.id", ondelete="RESTRICT"), nullable=False
    )

    product_description: Mapped[str] = mapped_column(String(200), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)

    entry: Mapped["ProductionEntry"] = relationship(back_populates="outputs")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<ProductionOutput {self.product_description} qty={self.quantity}>"
