"""Hierarchical settings: Platform -> Tenant -> Plant -> Module.

A lookup for key `K` at (tenant, plant, module) resolves by walking from most specific to least
specific (module+plant -> module+tenant -> plant -> tenant -> platform), implemented in
app/services/settings_service.py. This avoids hard-coding business rules that vary per tenant
(currency, timezone, date format, weight unit, tax configuration, numbering, approval limits,
notification preferences).
"""

import uuid
from typing import Any

from sqlalchemy import ForeignKey, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin, portable_json


class Setting(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "settings"

    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True, index=True
    )
    organization_unit_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organization_units.id", ondelete="CASCADE"), nullable=True
    )
    module: Mapped[str | None] = mapped_column(String(50), nullable=True)
    key: Mapped[str] = mapped_column(String(100), nullable=False)
    # Any JSON-serializable value (string/number/bool/object/array), not just objects — settings
    # like `weight_unit: "kg"` or `approval_limits: 50000` are scalars, not dicts.
    value: Mapped[Any] = mapped_column(portable_json(), nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "organization_unit_id", "module", "key", name="uq_setting_scope_key"
        ),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Setting {self.key}>"
