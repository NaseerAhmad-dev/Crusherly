"""Reusable operational locations (Master Build Specification section 26).

Future inventory and maintenance modules reference `Location.id` rather than modelling their own
place concept.
"""

import enum
import uuid

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TenantScopedMixin, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import MasterDataStatus


class LocationType(enum.StrEnum):
    PLANT = "PLANT"
    WAREHOUSE = "WAREHOUSE"
    STOCK_YARD = "STOCK_YARD"
    WORKSHOP = "WORKSHOP"
    OFFICE = "OFFICE"
    STORAGE_AREA = "STORAGE_AREA"


class Location(UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin, Base):
    __tablename__ = "locations"

    organization_unit_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organization_units.id", ondelete="SET NULL"), nullable=True
    )
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    location_type: Mapped[LocationType] = mapped_column(
        SAEnum(LocationType, name="location_type"), nullable=False
    )
    status: Mapped[MasterDataStatus] = mapped_column(
        SAEnum(MasterDataStatus, name="master_data_status"),
        nullable=False,
        default=MasterDataStatus.ACTIVE,
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Location {self.code} ({self.location_type.value})>"
