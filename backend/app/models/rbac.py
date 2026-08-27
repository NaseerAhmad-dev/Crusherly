"""RBAC: Role, Permission, UserRole, RolePermission.

Permission codes are stable strings (e.g. `users.view`), never database IDs — roles and
permissions can be reseeded/renumbered without breaking authorization checks elsewhere in the
codebase (Master Build Specification section 9).
"""

import uuid

from sqlalchemy import Boolean, ForeignKey, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin
from app.models.user import User  # noqa: F401  (referenced by relationship() below)


class Permission(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A stable, platform-wide permission code, e.g. `users.view`, `production.update`."""

    __tablename__ = "permissions"

    code: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    module: Mapped[str] = mapped_column(String(50), nullable=False, default="platform")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Permission {self.code}>"


class Role(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A named collection of permissions.

    `tenant_id` is null for platform-seeded roles (SUPER_ADMIN, TENANT_ADMIN, MANAGER, OPERATOR,
    ACCOUNTANT, STOREKEEPER, VIEWER) available to every tenant, and set for tenant-specific
    custom roles.
    """

    __tablename__ = "roles"

    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True, index=True
    )
    code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_system: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    role_permissions: Mapped[list["RolePermission"]] = relationship(
        back_populates="role", cascade="all, delete-orphan"
    )

    __table_args__ = (UniqueConstraint("tenant_id", "code", name="uq_role_tenant_code"),)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Role {self.code}>"


class RolePermission(TimestampMixin, Base):
    __tablename__ = "role_permissions"

    role_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True
    )
    permission_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True
    )

    role: Mapped["Role"] = relationship(back_populates="role_permissions")
    permission: Mapped["Permission"] = relationship()


class UserRole(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Assigns a Role to a User, optionally scoped to an organization unit (see ScopeAssignment
    for the general scope model — this FK covers the common single-scope-per-assignment case).

    `organization_unit_id` is nullable (an unscoped/tenant-wide assignment), so it cannot be part
    of a composite primary key; a surrogate UUID primary key is used instead with a supporting
    unique constraint.
    """

    __tablename__ = "user_roles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("roles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    organization_unit_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("organization_units.id", ondelete="CASCADE"),
        nullable=True,
    )

    user: Mapped["User"] = relationship(back_populates="user_roles")
    role: Mapped["Role"] = relationship()

    __table_args__ = (
        UniqueConstraint("user_id", "role_id", "organization_unit_id", name="uq_user_role_scope"),
    )
