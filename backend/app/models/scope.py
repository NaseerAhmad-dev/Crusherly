"""Scope-based authorization.

RBAC answers "what can the user do"; ScopeAssignment answers "where". A user can hold a role
platform-wide, tenant-wide, or restricted to one or more organization units (business unit,
plant, site, department). This table is the general-purpose form; `UserRole.organization_unit_id`
covers the common single-node case inline for convenience for callers that don't need multiple
scopes per role assignment.
"""

import uuid

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import ScopeLevel


class ScopeAssignment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "scope_assignments"

    user_role_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("user_roles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    scope_level: Mapped[ScopeLevel] = mapped_column(
        SAEnum(ScopeLevel, name="scope_level"), nullable=False
    )
    organization_unit_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organization_units.id", ondelete="CASCADE"), nullable=True
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<ScopeAssignment {self.scope_level.value}>"
