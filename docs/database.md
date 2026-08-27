# Database

This document describes the data model implemented in `backend/app/models/` as of Phase 0
(Platform Foundation — see [README.md](../README.md)). It covers the shared model conventions,
the reasoning behind two non-obvious pieces of infrastructure (`UTCDateTime` and
`eager_defaults`), the Alembic migration setup, and a full model inventory.

The database is PostgreSQL 16 in every real environment. SQLite backs the fast unit-test suite
(`backend/tests/conftest.py`). Every convention described below exists to make the exact same
model definitions behave identically on both, so tests exercise real model behavior rather than
a SQLite-specific approximation of it.

## Conventions

### UUID primary keys + timestamps

Every model mixes in `UUIDPrimaryKeyMixin` (see `backend/app/models/base.py`):

```python
class UUIDPrimaryKeyMixin:
    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
```

`Uuid` is SQLAlchemy 2.0's dialect-agnostic UUID type — deliberately not
`sqlalchemy.dialects.postgresql.UUID` — so the identical column definition compiles to a native
`uuid` column on PostgreSQL and to `CHAR(32)` on SQLite. IDs are generated client-side
(`default=uuid.uuid4`) rather than server-side, so a newly-constructed ORM object has a usable
`.id` before the first flush (needed, for example, to build the `RefreshSession` row and the JWT
`jti` in `auth_service._issue_token_pair` in the same unit of work).

Most models also mix in `TimestampMixin`:

```python
class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime(), server_default=func.now(), onupdate=func.now(), nullable=False)
```

Both are server-computed (`func.now()`), not app-computed, so the timestamp reflects the
database's clock and is correct even for rows written by raw SQL or a future data-migration
script that bypasses the ORM. `AuditEvent` and `ApprovalAction` are the two exceptions: they are
immutable, single-write log rows, so they only carry a `created_at`/`timestamp` column and no
`updated_at`.

`AuditedByMixin` adds `created_by`/`updated_by` (both nullable `FK -> users.id`,
`ondelete="SET NULL"` so deleting a user doesn't cascade into deleting the records they touched).
It is opt-in per model — declared as `@declared_attr` methods rather than plain columns, which is
what lets a mixin contribute a `ForeignKey` without every consuming model needing to know the
target table up front. No Phase 0 model currently uses it directly; it exists as the shared
building block for business-module tables in later phases that need a "who touched this last"
column without hand-rolling the FK pair each time.

### Why `UTCDateTime` instead of `DateTime(timezone=True)`

```python
class UTCDateTime(TypeDecorator):
    impl = DateTime(timezone=True)
    cache_ok = True

    def process_result_value(self, value, dialect):
        if value is not None and value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return value
```

PostgreSQL's `TIMESTAMPTZ` round-trips tz-aware `datetime` objects natively. SQLite has no
tz-aware storage type at all: `DateTime(timezone=True)` silently returns a **naive** `datetime`
on read there, with no error. That divergence caused a real bug during Phase 0 development — a
refresh-token expiry check (`refresh_session.expires_at < datetime.now(UTC)` in
`auth_service.refresh`) worked fine against PostgreSQL but raised
`TypeError: can't compare offset-naive and offset-aware datetimes` under the SQLite-backed test
suite, because `expires_at` came back naive while `datetime.now(UTC)` is aware.

`UTCDateTime` wraps `DateTime(timezone=True)` and re-attaches `UTC` tzinfo on read whenever the
underlying driver handed back a naive value. Since every stored timestamp in this codebase is
already UTC by convention, re-attaching `UTC` is always correct, never a guess. Every timestamp
column in every model uses `UTCDateTime()` instead of `DateTime(timezone=True)` directly, so
PostgreSQL and SQLite behave identically and comparisons like the one above work the same way in
tests as they do in production.

### `portable_json()`

```python
def portable_json():
    return JSON().with_variant(JSONB(), "postgresql")
```

Compiles to `JSONB` on PostgreSQL (indexable, binary-stored) and plain `JSON` everywhere else
(SQLite has no `JSONB`). Used for genuinely schemaless columns: `AuditEvent.old_data`/`new_data`
(arbitrary before/after snapshots for any resource type) and `Setting.value` (a setting value can
be a scalar, object, or array — see `backend/app/models/setting.py`).

### Tenant scoping

`TenantScopedMixin` adds a **mandatory, indexed** `tenant_id`:

```python
class TenantScopedMixin:
    @declared_attr
    def tenant_id(cls) -> Mapped[uuid.UUID]:
        return mapped_column(Uuid(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
```

Its docstring is explicit about the security model: *"The backend security context — never the
client — determines which tenant_id is used for reads/writes"* (see
`app/security/dependencies.py` and the tenant-scoping middleware). A client cannot pass a
`tenant_id` in a request body and have it trusted; the service layer always derives it from the
authenticated user's `SecurityContext`.

Not every model uses the mixin, because not every table is tenant-owned. Three different
patterns show up across the schema:

1. **Mandatory `tenant_id`** (via `TenantScopedMixin`, or an equivalent explicit non-nullable
   column) — genuinely tenant-owned data: `OrganizationUnit`, `Location`, `CostCentre`,
   `ProfitCentre`, `FiscalYear`, `DocumentSequence`, `Attachment`, `WorkflowInstance`.
2. **Nullable `tenant_id`** — platform-level rows coexist with tenant-level rows in the same
   table. `User.tenant_id` is nullable because platform users (`is_platform_user=True`, e.g.
   `SUPER_ADMIN`) aren't bound to any tenant, while tenant users must always carry one (enforced
   in the service layer, not the database, since a `CHECK` on `is_platform_user` correlating two
   columns isn't portable across both dialects). `Role.tenant_id`, `WorkflowDefinition.tenant_id`,
   `Setting.tenant_id`, and `Notification.tenant_id` follow the same shape: null means
   platform-wide/shared, set means tenant-specific.
3. **No `tenant_id` at all** — either genuinely platform-global (`Tenant` itself, `Permission`,
   `UnitCategory`/`Unit`/`UnitConversion` — units of measurement are shared platform-wide
   reference data, not tenant-specific), or scoped indirectly through a parent FK rather than
   their own column (`RolePermission`, `UserRole`, `ScopeAssignment`, `WorkflowStepDefinition`,
   `ApprovalAction`, `PasswordResetToken`, `RefreshSession` all derive their tenant through
   `role_id`/`user_id`/`workflow_instance_id` rather than duplicating `tenant_id` redundantly).
   `AuditEvent.tenant_id` is a special case: it's nullable and *not* a foreign key, by design —
   audit rows must survive independently of anything else and must never be blocked or cascaded
   by referential integrity (see the module docstring in `app/models/audit.py`).

## `eager_defaults = True` — and the bug it fixes

`backend/app/core/database.py` sets a mapper-wide default:

```python
class Base(DeclarativeBase):
    __mapper_args__ = {"eager_defaults": True}
```

By default, SQLAlchemy's async ORM fetches server-generated column values (`server_default`,
`onupdate=func.now()`, etc.) via `RETURNING` on **INSERT**, but leaves them **expired** after an
**UPDATE** — reading them normally triggers a lazy refresh on next access. In a synchronous
session that refresh happens transparently. In an *async* session it can't: SQLAlchemy's asyncio
extension only bridges greenlets for calls it explicitly awaits, so an implicit attribute-access
refresh triggered deep inside Pydantic's `model_validate(orm_obj)` (e.g. reading `updated_at` to
build a `TenantResponse`) raises `sqlalchemy.exc.MissingGreenlet` instead of silently working.

This is exactly what happened in the tenant-suspend endpoint
(`suspend_tenant` in `backend/app/services/tenant_service.py`): it flips `tenant.status`,
`session.flush()`s, then the router immediately does
`TenantResponse.model_validate(tenant)` to build the response — which reads `updated_at`. Because
`updated_at` uses `onupdate=func.now()` (a server-side default that only fires on UPDATE, not a
value already sitting in memory), the ORM object's cached `updated_at` was stale/expired after the
flush, and serializing it into the response schema crashed with `MissingGreenlet`.

Setting `eager_defaults = True` mapper-wide makes SQLAlchemy fetch **all** server-generated
defaults via `RETURNING` on both INSERT and UPDATE, as part of the same flush statement — so
`tenant.updated_at` is already populated in memory by the time `session.flush()` returns, and no
implicit lazy-load is ever needed. This is a one-line, mapper-wide fix rather than a per-endpoint
`session.refresh(obj)` call, so every current and future model gets the same guarantee for free.

## Alembic migrations

`backend/alembic/env.py` imports `app.models` (which in turn imports every individual model
module — see its docstring) before setting `target_metadata = Base.metadata`, so
`Base.metadata` is fully populated and autogenerate can see every table. The engine is created
with `async_engine_from_config`/`async_engine_from_config` and migrations run via
`connection.run_sync(do_run_migrations)`, since Alembic's migration runner itself is synchronous
but the app's engine is async.

As of this writing there is exactly **one** migration:
`backend/alembic/versions/faf06f89c6a6_phase_0_platform_foundation.py`. It creates all 26 Phase 0
tables in one revision (`tenants`, `users`, `permissions`, `roles`, `role_permissions`,
`user_roles`, `scope_assignments`, `organization_units`, `audit_events`, `refresh_sessions`,
`password_reset_tokens`, `document_sequences`, `fiscal_years`, `workflow_definitions`,
`workflow_step_definitions`, `workflow_instances`, `approval_actions`, `attachments`,
`notifications`, `settings`, `unit_categories`, `units`, `unit_conversions`, `locations`,
`cost_centres`, `profit_centres`), with a matching `downgrade()` that drops them in
dependency-safe reverse order. There has been no need yet to hand-edit a generated migration
(no data backfills, no non-trivial column transforms) — Phase 0 only ever added tables.

Going forward, the workflow for every schema change is:

1. Change the model(s) in `backend/app/models/`.
2. Add the new module to `backend/app/models/__init__.py` if it's a new file (autogenerate can
   only see models that have actually been imported).
3. Run `alembic revision --autogenerate -m "<description>"` from `backend/`.
4. **Read the generated migration.** Autogenerate reliably detects new/dropped tables, columns,
   and indexes, but it does not detect renames (it will emit a drop+add), doesn't know about pure
   data migrations, and needs `compare_type=True` (already set in `env.py`) to notice column
   type changes at all.
5. Run `alembic upgrade head` locally (or let `backend/entrypoint.sh` do it automatically on
   container start — see the README) and confirm the app still boots against the migrated schema.

## Model inventory

| Model | File | Purpose | Tenant-scoped |
|---|---|---|---|
| `Tenant` | `tenant.py` | A company/organization using the platform; top of the multi-tenancy hierarchy. | No — this *is* the tenant. |
| `User` | `user.py` | A platform or tenant-level user. Email is globally unique across the platform (no tenant selector at login). | Nullable — null for platform users (`is_platform_user=True`), mandatory for tenant users (service-layer enforced). |
| `Permission` | `rbac.py` | A stable, platform-wide permission code (e.g. `users.view`). Never referenced by ID in authorization logic, only by code. | No — global. |
| `Role` | `rbac.py` | A named collection of permissions. | Nullable — null for the seven platform-seeded system roles (SUPER_ADMIN, TENANT_ADMIN, MANAGER, OPERATOR, ACCOUNTANT, STOREKEEPER, VIEWER), set for tenant-specific custom roles. |
| `RolePermission` | `rbac.py` | Join table: which permissions a role grants. | Indirect via `role_id`. |
| `UserRole` | `rbac.py` | Assigns a role to a user, optionally scoped to one organization unit. | Indirect via `user_id`. |
| `ScopeAssignment` | `scope.py` | General-purpose "where" for a role assignment (platform/tenant/business-unit/plant/site/department), supporting multiple scopes per assignment beyond `UserRole`'s single-node shortcut. | Indirect via `user_role_id`. |
| `OrganizationUnit` | `organization.py` | One node in the Tenant → Business Unit → Plant → Site → Department hierarchy; self-referencing via `parent_id`. | Yes (`TenantScopedMixin`). |
| `AuditEvent` | `audit.py` | Append-only audit log entry. No API route ever updates or deletes a row. | Nullable, and deliberately **not** an FK (must never be blocked/cascaded). |
| `RefreshSession` | `refresh_session.py` | Tracks one issued refresh token (by `jti`) so it can be revoked; backs logout and future login history. Access tokens are stateless and untracked. | Indirect via `user_id`. |
| `PasswordResetToken` | `password_reset.py` | A single-use, short-lived, hashed password-reset token (the raw token is never stored). | Indirect via `user_id`. |
| `DocumentSequence` | `numbering.py` | One row per (tenant, organization unit, document type, fiscal year); `last_sequence` is incremented via an atomic `UPDATE ... RETURNING` for gap-free, concurrency-safe numbering. | Yes (explicit mandatory `tenant_id`). |
| `FiscalYear` | `fiscal_year.py` | A tenant's financial year (e.g. `"2026-27"`); no business logic anywhere may hard-code a year. | Yes (explicit mandatory `tenant_id`). |
| `WorkflowDefinition` | `workflow.py` | Names an approvable entity type and whether approval is currently active for it. | Nullable — null for platform-shared definitions, set for tenant-specific ones. |
| `WorkflowStepDefinition` | `workflow.py` | One ordered approval step within a `WorkflowDefinition`, optionally requiring a specific permission. | Indirect via `workflow_definition_id`. |
| `WorkflowInstance` | `workflow.py` | A live approval process attached to one business document (`entity_type` + `entity_id`), tracking current state/step. | Yes (explicit mandatory `tenant_id`). |
| `ApprovalAction` | `workflow.py` | Immutable record of one Submit/Approve/Reject/Return/Cancel action against a `WorkflowInstance`. | Indirect via `workflow_instance_id`. |
| `Attachment` | `attachment.py` | Metadata for one uploaded file (`entity_type`/`entity_id` + storage key); bytes live in blob storage, not the database. | Yes (explicit mandatory `tenant_id`). |
| `Notification` | `notification.py` | An in-app (or future email/SMS/push/WhatsApp) notification to one user. Only `IN_APP` is actually delivered in Phase 0. | Nullable. |
| `Setting` | `setting.py` | One key/value setting, resolved by walking Platform → Tenant → Plant → Module from most to least specific. | Nullable (both `tenant_id` and `organization_unit_id`). |
| `UnitCategory` | `unit.py` | Groups units of measurement (e.g. "mass", "volume") so conversions are only ever offered within a category. | No — global reference data. |
| `Unit` | `unit.py` | One unit of measurement (code/name/symbol) within a category. | No — global reference data. |
| `UnitConversion` | `unit.py` | An explicit pairwise conversion factor between two units. | No — global reference data. |
| `Location` | `location.py` | A reusable operational place (plant/warehouse/stock yard/workshop/office/storage area) for future inventory and maintenance modules to reference. | Yes (`TenantScopedMixin`). |
| `CostCentre` | `cost_centre.py` | A cost-tracking node, optionally attached to an `OrganizationUnit`. | Yes (`TenantScopedMixin`). |
| `ProfitCentre` | `cost_centre.py` | A profit-tracking node, optionally attached to an `OrganizationUnit`. | Yes (`TenantScopedMixin`). |

Business-module tables (Weighbridge, Production, Inventory, Sales, Dispatch, Purchases,
Maintenance, Vehicles, Fuel, Finance, Quality, Safety, Compliance, Reporting/Analytics) do not
exist yet — see the Phase Discipline section of the [README](../README.md).
