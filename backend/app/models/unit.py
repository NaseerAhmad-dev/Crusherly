"""Units of measurement, grouped into categories, with explicit pairwise conversions.

Conversions are only ever mathematically valid within the same category (e.g. kg <-> ton, both
mass); a volume-to-weight conversion is NOT assumed to be universal since it depends on material
density, which is out of scope for the platform foundation (Master Build Specification section
24) and will be modelled per-material in a later phase.
"""

import uuid

from sqlalchemy import ForeignKey, Numeric, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class UnitCategory(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "unit_categories"

    code: Mapped[str] = mapped_column(String(30), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)


class Unit(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "units"

    category_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("unit_categories.id", ondelete="RESTRICT"), nullable=False
    )
    code: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    symbol: Mapped[str] = mapped_column(String(10), nullable=False)


class UnitConversion(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """`quantity_in_to_unit = quantity_in_from_unit * factor`."""

    __tablename__ = "unit_conversions"

    from_unit_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("units.id", ondelete="CASCADE"), nullable=False
    )
    to_unit_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("units.id", ondelete="CASCADE"), nullable=False
    )
    factor: Mapped[float] = mapped_column(Numeric(20, 10), nullable=False)

    __table_args__ = (
        UniqueConstraint("from_unit_id", "to_unit_id", name="uq_unit_conversion_pair"),
    )
