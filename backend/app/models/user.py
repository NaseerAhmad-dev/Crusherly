import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, String, Uuid
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UTCDateTime, UUIDPrimaryKeyMixin
from app.models.enums import UserStatus

if TYPE_CHECKING:
    from app.models.rbac import UserRole


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A platform or tenant-level user.

    `tenant_id` is nullable: platform-level users (e.g. SUPER_ADMIN) are not bound to a tenant.
    Tenant-level users must always carry a tenant_id, enforced in the service layer.
    """

    __tablename__ = "users"

    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True, index=True
    )
    # Globally unique across the whole platform, not just within a tenant (see ADR-003): a login
    # page has no tenant context to disambiguate by, so two tenants sharing an email would make
    # login ambiguous. Case sensitivity is normalized to lowercase at write time by the service
    # layer; the DB constraint is on the stored (already-lowercased) value.
    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    status: Mapped[UserStatus] = mapped_column(
        SAEnum(UserStatus, name="user_status"), nullable=False, default=UserStatus.ACTIVE
    )
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_platform_user: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    last_login_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    failed_login_attempts: Mapped[int] = mapped_column(default=0, nullable=False)

    user_roles: Mapped[list["UserRole"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<User {self.email}>"
