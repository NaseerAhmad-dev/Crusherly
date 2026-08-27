from sqlalchemy import Enum as SAEnum
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import TenantStatus


class Tenant(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A company/organization using the platform. Top of the multi-tenancy hierarchy."""

    __tablename__ = "tenants"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)
    slug: Mapped[str] = mapped_column(String(80), nullable=False, unique=True, index=True)
    status: Mapped[TenantStatus] = mapped_column(
        SAEnum(TenantStatus, name="tenant_status"), nullable=False, default=TenantStatus.ACTIVE
    )
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="Asia/Kolkata")
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="INR")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Tenant {self.code} ({self.status.value})>"
