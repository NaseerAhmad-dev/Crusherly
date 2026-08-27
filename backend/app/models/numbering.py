"""Reusable, concurrency-safe document numbering.

One row per (tenant, organization unit, document type, fiscal year). `next_number()` in
app/services/numbering_service.py increments `last_sequence` via a single atomic
`UPDATE ... RETURNING` statement, so two concurrent requests can never receive the same number
(see Master Build Specification sections 17 and 29). Individual business modules must call this
service instead of implementing their own numbering.
"""

import uuid

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class DocumentSequence(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "document_sequences"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    organization_unit_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organization_units.id", ondelete="CASCADE"), nullable=True
    )
    document_type: Mapped[str] = mapped_column(String(50), nullable=False)
    fiscal_year_code: Mapped[str] = mapped_column(String(20), nullable=False)
    prefix: Mapped[str] = mapped_column(String(50), nullable=False)
    last_sequence: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    padding: Mapped[int] = mapped_column(Integer, nullable=False, default=6)

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "organization_unit_id",
            "document_type",
            "fiscal_year_code",
            name="uq_document_sequence_scope",
        ),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<DocumentSequence {self.prefix} last={self.last_sequence}>"
