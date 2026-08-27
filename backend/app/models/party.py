"""Customers and Suppliers — the two "party" master-data entities Weighbridge's `party_name`
free-text field should eventually reference (see docs/master-data.md)."""

from sqlalchemy import String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import AuditedByMixin, CodedMasterDataMixin, TenantScopedMixin, TimestampMixin, UUIDPrimaryKeyMixin


class Customer(
    UUIDPrimaryKeyMixin, TenantScopedMixin, CodedMasterDataMixin, AuditedByMixin, TimestampMixin, Base
):
    __tablename__ = "customers"

    contact_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    tax_id: Mapped[str | None] = mapped_column(String(50), nullable=True)

    __table_args__ = (UniqueConstraint("tenant_id", "code", name="uq_customer_code"),)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Customer {self.code}>"


class Supplier(
    UUIDPrimaryKeyMixin, TenantScopedMixin, CodedMasterDataMixin, AuditedByMixin, TimestampMixin, Base
):
    __tablename__ = "suppliers"

    contact_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    tax_id: Mapped[str | None] = mapped_column(String(50), nullable=True)

    __table_args__ = (UniqueConstraint("tenant_id", "code", name="uq_supplier_code"),)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Supplier {self.code}>"
