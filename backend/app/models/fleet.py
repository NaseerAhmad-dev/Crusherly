"""Vehicles and Drivers — the two entities Weighbridge's `vehicle_number`/`driver_name` free-text
fields should eventually reference (see docs/master-data.md). `code` on `Vehicle` is its
registration number."""

import uuid
from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import AuditedByMixin, CodedMasterDataMixin, TenantScopedMixin, TimestampMixin, UUIDPrimaryKeyMixin


class Vehicle(
    UUIDPrimaryKeyMixin, TenantScopedMixin, CodedMasterDataMixin, AuditedByMixin, TimestampMixin, Base
):
    """`code` is the vehicle's registration number (e.g. `JK01AB1234`), upper-cased on save —
    the same convention `weighbridge_service.create_ticket()` already applies to its free-text
    `vehicle_number` field."""

    __tablename__ = "vehicles"

    vehicle_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    capacity: Mapped[Decimal | None] = mapped_column(Numeric(12, 3), nullable=True)
    capacity_unit_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("units.id", ondelete="SET NULL"), nullable=True
    )

    __table_args__ = (UniqueConstraint("tenant_id", "code", name="uq_vehicle_code"),)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Vehicle {self.code}>"


class Driver(
    UUIDPrimaryKeyMixin, TenantScopedMixin, CodedMasterDataMixin, AuditedByMixin, TimestampMixin, Base
):
    """`code` is the driver's license number."""

    __tablename__ = "drivers"

    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)

    __table_args__ = (UniqueConstraint("tenant_id", "code", name="uq_driver_code"),)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Driver {self.code}>"
