"""Append-only audit log.

Normal application code must only INSERT rows here (via app.services.audit_service). No API
route exposes update/delete for audit events — see app/api/v1/audit.py.
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import UTCDateTime, UUIDPrimaryKeyMixin, portable_json
from app.models.enums import AuditAction


class AuditEvent(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "audit_events"

    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), nullable=True, index=True
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    resource_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    resource_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    old_data: Mapped[dict[str, Any] | None] = mapped_column(portable_json(), nullable=True)
    new_data: Mapped[dict[str, Any] | None] = mapped_column(portable_json(), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(255), nullable=True)
    request_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    timestamp: Mapped[datetime] = mapped_column(
        UTCDateTime(), server_default=func.now(), nullable=False, index=True
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<AuditEvent {self.action} {self.resource_type}:{self.resource_id}>"


# AuditAction is re-exported here for convenient `from app.models.audit import AuditAction`
# call-sites in services; the canonical definition lives in app.models.enums.
__all__ = ["AuditEvent", "AuditAction"]
