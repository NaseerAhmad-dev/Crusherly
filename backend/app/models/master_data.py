"""The four master-data entities that are pure `code`/`name`/`description`/`status` lookups with
no entity-specific fields at all — `CodedMasterDataMixin` covers their entire shape. See
`app/models/material.py`, `app/models/party.py`, and `app/models/fleet.py` for entities that
extend the same base with additional fields.
"""

from sqlalchemy import UniqueConstraint

from app.core.database import Base
from app.models.base import AuditedByMixin, CodedMasterDataMixin, TenantScopedMixin, TimestampMixin, UUIDPrimaryKeyMixin


class MaterialCategory(
    UUIDPrimaryKeyMixin, TenantScopedMixin, CodedMasterDataMixin, AuditedByMixin, TimestampMixin, Base
):
    __tablename__ = "material_categories"
    __table_args__ = (UniqueConstraint("tenant_id", "code", name="uq_material_category_code"),)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<MaterialCategory {self.code}>"


class ProductCategory(
    UUIDPrimaryKeyMixin, TenantScopedMixin, CodedMasterDataMixin, AuditedByMixin, TimestampMixin, Base
):
    __tablename__ = "product_categories"
    __table_args__ = (UniqueConstraint("tenant_id", "code", name="uq_product_category_code"),)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<ProductCategory {self.code}>"


class TaxCode(UUIDPrimaryKeyMixin, TenantScopedMixin, CodedMasterDataMixin, AuditedByMixin, TimestampMixin, Base):
    __tablename__ = "tax_codes"
    __table_args__ = (UniqueConstraint("tenant_id", "code", name="uq_tax_code_code"),)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<TaxCode {self.code}>"


class PaymentTerm(
    UUIDPrimaryKeyMixin, TenantScopedMixin, CodedMasterDataMixin, AuditedByMixin, TimestampMixin, Base
):
    __tablename__ = "payment_terms"
    __table_args__ = (UniqueConstraint("tenant_id", "code", name="uq_payment_term_code"),)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<PaymentTerm {self.code}>"
