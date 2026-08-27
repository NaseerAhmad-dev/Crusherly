"""Shared model mixins.

Per the database standards in the master spec: UUID primary keys for major entities,
timezone-aware `created_at`/`updated_at` on important entities, and `created_by`/`updated_by`
where appropriate.

Columns use SQLAlchemy 2.0's dialect-agnostic `Uuid`/`JSON` types (rather than
`sqlalchemy.dialects.postgresql.UUID`/`JSONB` directly) so the exact same model definitions run
against PostgreSQL in production and SQLite in the fast unit-test suite (see tests/conftest.py) —
`Uuid` compiles to native `uuid` on PostgreSQL and `CHAR(32)` elsewhere; `portable_json()` compiles
to `JSONB` on PostgreSQL (via `with_variant`) and plain `JSON` elsewhere.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, Enum as SAEnum, ForeignKey, String, Text, TypeDecorator, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, declared_attr, mapped_column

from app.models.enums import MasterDataStatus


def portable_json():
    return JSON().with_variant(JSONB(), "postgresql")


class UTCDateTime(TypeDecorator):
    """`DateTime(timezone=True)` that round-trips as tz-aware UTC on every backend.

    PostgreSQL's `TIMESTAMPTZ` preserves tzinfo natively. SQLite has no tz-aware storage —
    `DateTime(timezone=True)` silently returns naive datetimes on read there, which raises
    `TypeError: can't compare offset-naive and offset-aware datetimes` wherever a stored value
    is compared against `datetime.now(timezone.utc)`. Since SQLite backs the fast unit-test
    suite (see tests/conftest.py) while PostgreSQL runs in production, every timestamp column
    uses this type instead of `DateTime(timezone=True)` directly so both behave identically.
    """

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_result_value(self, value, dialect):
        if value is not None and value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return value


class UUIDPrimaryKeyMixin:
    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class AuditedByMixin:
    """Adds created_by / updated_by user references. Opt-in per model."""

    @declared_attr
    def created_by(cls) -> Mapped[uuid.UUID | None]:
        return mapped_column(
            Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
        )

    @declared_attr
    def updated_by(cls) -> Mapped[uuid.UUID | None]:
        return mapped_column(
            Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
        )


class TenantScopedMixin:
    """Adds a mandatory tenant_id FK. Every tenant-owned table must include this.

    The backend security context — never the client — determines which tenant_id is used
    for reads/writes (see app/security/dependencies.py and app/middleware/tenant_context.py).
    """

    @declared_attr
    def tenant_id(cls) -> Mapped[uuid.UUID]:
        return mapped_column(
            Uuid(as_uuid=True),
            ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )


class CodedMasterDataMixin:
    """The master-data field shape from the master spec section 25: `code`, `name`,
    `description`, `status` — the columns every master-data table shares regardless of what
    entity-specific fields it also has. See `app/repositories/master_data_repository.py` and
    `app/services/master_data_service.py` for the generic CRUD layer built against exactly this
    shape, so adding a new master-data entity means defining a model + schema, not rewriting
    CRUD plumbing (the master spec explicitly warns against duplicating CRUD architecture).

    `code` is unique per tenant (see each concrete model's `UniqueConstraint`), not globally —
    two tenants may both have a material coded `40MM`. Deactivation is preferred over deletion
    (`status -> INACTIVE`) since master data is normally referenced by transactional records.
    """

    code: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[MasterDataStatus] = mapped_column(
        # `create_type=False`: the Postgres enum type `master_data_status` already exists (first
        # created for `Location` in Phase 0's migration) — every model using this mixin shares
        # that one type rather than each emitting its own `CREATE TYPE`, which would fail with
        # "type already exists" the second time `alembic upgrade` runs a migration that touches
        # more than one `CodedMasterDataMixin` table. Irrelevant on SQLite, where `Enum` compiles
        # to a plain `VARCHAR` + `CHECK` constraint and `create_type` has no effect.
        SAEnum(MasterDataStatus, name="master_data_status", create_type=False),
        nullable=False,
        default=MasterDataStatus.ACTIVE,
    )
