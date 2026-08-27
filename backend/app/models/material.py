"""Materials (raw input, e.g. "raw stone") and Products (graded output, e.g. "40mm aggregate") —
the two catalog entities Weighbridge's and Production's free-text `material_description` /
`product_description` fields should eventually reference (see docs/master-data.md for why that
retrofit isn't done in this same phase).
"""

import uuid

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import AuditedByMixin, CodedMasterDataMixin, TenantScopedMixin, TimestampMixin, UUIDPrimaryKeyMixin


class Material(
    UUIDPrimaryKeyMixin, TenantScopedMixin, CodedMasterDataMixin, AuditedByMixin, TimestampMixin, Base
):
    __tablename__ = "materials"

    category_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("material_categories.id", ondelete="SET NULL"), nullable=True
    )
    default_unit_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("units.id", ondelete="SET NULL"), nullable=True
    )

    __table_args__ = (UniqueConstraint("tenant_id", "code", name="uq_material_code"),)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Material {self.code}>"


class Product(
    UUIDPrimaryKeyMixin, TenantScopedMixin, CodedMasterDataMixin, AuditedByMixin, TimestampMixin, Base
):
    __tablename__ = "products"

    category_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("product_categories.id", ondelete="SET NULL"), nullable=True
    )
    default_unit_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("units.id", ondelete="SET NULL"), nullable=True
    )

    __table_args__ = (UniqueConstraint("tenant_id", "code", name="uq_product_code"),)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Product {self.code}>"
