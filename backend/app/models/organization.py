import uuid

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TenantScopedMixin, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import OrganizationUnitType


class OrganizationUnit(UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin, Base):
    """A node in the Tenant -> Business Unit -> Plant -> Site -> Department hierarchy.

    Not every tenant must use every level (see Master Build Specification section 6): a small
    tenant may attach Plants directly under the Tenant with no Business Unit, by leaving
    parent_id null on a PLANT-type unit. Business modules reference `organization_unit_id` for
    scope rather than reimplementing hierarchy.
    """

    __tablename__ = "organization_units"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    unit_type: Mapped[OrganizationUnitType] = mapped_column(
        SAEnum(OrganizationUnitType, name="organization_unit_type"), nullable=False
    )
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organization_units.id", ondelete="CASCADE"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="ACTIVE")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<OrganizationUnit {self.code} ({self.unit_type.value})>"
