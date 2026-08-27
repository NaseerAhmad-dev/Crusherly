# Multi-Tenancy

This document covers how tenant isolation is modeled and enforced in Phase 0. The implementation
lives in:

- `backend/app/models/tenant.py` — the `Tenant` model
- `backend/app/models/base.py` — `TenantScopedMixin`
- `backend/app/services/tenant_service.py` — tenant lifecycle (create/update/suspend)
- `backend/app/models/enums.py` — `TenantStatus`
- `backend/app/security/dependencies.py` — where the acting tenant is actually determined
- `backend/app/services/user_service.py` — the clearest real example of tenant isolation enforced
  in a service
- `backend/tests/integration/test_tenant_isolation.py` — the tests that pin this behavior down
- `docs/database.md` — the deeper technical writeup of `eager_defaults` and the three `tenant_id`
  patterns used across every model in the schema

See also [organization.md](organization.md) (every organization unit belongs to exactly one
tenant) and [authorization.md](authorization.md) (RBAC/scope run inside a tenant that's already
been resolved).

## `Tenant`: top of the hierarchy

```python
class Tenant(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    name: Mapped[str]
    code: Mapped[str]          # unique, indexed
    slug: Mapped[str]          # unique, indexed
    status: Mapped[TenantStatus]
    timezone: Mapped[str]      # default "Asia/Kolkata"
    currency: Mapped[str]      # default "INR"
```

A `Tenant` row is not itself an `OrganizationUnit` — it's the implicit root above the org-unit
hierarchy (see [organization.md](organization.md)). Everything tenant-owned — organization units,
users, roles' custom variants, settings, and every business-module table added in later phases —
hangs off a `tenant_id` somewhere.

## Never trust a client-supplied `tenant_id`

The rule, stated directly in `user_service.py`'s module docstring: *"Tenant isolation is enforced
here at the choke point, not left to the router: every function that reads or writes a `User`
takes `tenant_id` from the caller's `SecurityContext` (never from a path/query/body parameter) and
every repository call filters by it."*

Concretely, `SecurityContext.tenant_id` is just `user.tenant_id`, read directly off the freshly
re-fetched `User` row in `build_security_context()` (see [authorization.md](authorization.md)) —
never off anything the caller supplied on this request. Both the access and refresh JWTs do carry
a `tenant_id` claim (`app/security/tokens.py`, for convenience/telemetry), but `get_current_user`
(`app/security/dependencies.py`) never reads it — it decodes only the `sub` claim (the user id),
loads that `User` row from the database, and everything downstream derives tenant from that row.
A forged or stale `tenant_id` claim in a token is simply never consulted.

This shows up concretely in `app/schemas/user.py`:

```python
class UserCreateRequest(BaseModel):
    ...
    tenant_id: uuid.UUID | None = None  # only honored for platform users creating platform users
```

The field exists on the request schema, but `user_service.create_user()` never reads
`payload.tenant_id` at all — every created user unconditionally gets `context.tenant_id`. The
comment describes a platform-admin "create a user in tenant X" flow that doesn't exist yet in
Phase 0; today the field is inert, not a bypass. This is the pattern to expect throughout the
codebase: a client-supplied tenant identifier, if present in a schema at all, is either ignored or
reserved for a not-yet-built platform-level flow — it is never what a service function actually
uses to decide which tenant's data to touch.

### The repository-layer choke points

Every tenant-scoped repository function takes `tenant_id` as an explicit parameter and filters on
it in the query itself, so a mismatched id doesn't even reveal a row exists:

- `user_repository.get_by_id_in_tenant(session, user_id, tenant_id)` — `WHERE id = :id AND
  tenant_id = :tenant_id` in one query. `user_service.get_user()` calls this rather than
  `get_by_id()` for exactly this reason.
- `user_repository.list_users_in_tenant(session, tenant_id, ...)` — every listing filters by
  `tenant_id` first, before any search term.
- `role_repository.get_visible_to_tenant(session, role_id, tenant_id)` — a role is visible if it's
  a global system role (`tenant_id IS NULL`) or owned by the exact calling tenant; its own
  docstring calls this "the tenant-isolation choke point for roles." `user_service.assign_role`
  uses this, not `get_by_id`, so a tenant cannot assign a role belonging to a different tenant.

`tests/integration/test_tenant_isolation.py` pins the observable consequence: Tenant A attempting
to `GET`/`PATCH`/`DELETE` a Tenant B user by a guessed/enumerated id gets **404, not 403** — the
test comment is explicit that this is deliberate: *"tenant A must not even learn it exists."* A 403
would confirm the row exists under some other tenant; 404 doesn't.

Platform-level users (`context.tenant_id is None`) are explicitly *rejected* by these same
tenant-scoped user-management functions (`ForbiddenError("Platform users must manage users through
tenant administration.")`) — there is no cross-tenant user-management surface for platform admins
in Phase 0. The only platform-level surface that exists today is tenant lifecycle itself
(list/create/update/suspend tenants, below).

## `TenantScopedMixin`

```python
class TenantScopedMixin:
    @declared_attr
    def tenant_id(cls) -> Mapped[uuid.UUID]:
        return mapped_column(
            Uuid(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False, index=True,
        )
```

Every genuinely tenant-owned table (`OrganizationUnit`, `Location`, `CostCentre`, `ProfitCentre`,
and more per `docs/database.md`'s model inventory) mixes this in rather than declaring its own
`tenant_id` column, so the FK target, `ondelete` behavior, nullability, and index are identical
everywhere. It's a `@declared_attr`, not a plain column, specifically so a mixin can contribute a
`ForeignKey` without every consuming model needing to redeclare it.

The mixin's own docstring points to "the backend security context — never the client" and to `app/
middleware/tenant_context.py` for how the acting `tenant_id` gets determined. That specific file
does not exist in the current tree (there is no dedicated tenant-context middleware — the
`app/middleware/` package only has `request_context.py`, `rate_limit.py`, and
`security_headers.py`). The mechanism the docstring is pointing at is real, it's just implemented
in `app/security/dependencies.py` and `SecurityContext` rather than a middleware module: treat that
file path in the docstring as stale, and the actual enforcement as described above (repository
functions taking an explicit `tenant_id` sourced from `SecurityContext`) as the source of truth.

## The nullable `tenant_id` pattern

Not every `tenant_id` column is mandatory. Three shapes appear across the schema (see
`docs/database.md` for the full inventory); the one specific to this doc is the **nullable**
pattern used for platform/tenant coexistence in the same table:

- **`User.tenant_id`** is nullable: platform-level users (`is_platform_user=True`, e.g. the seeded
  `SUPER_ADMIN`) have `tenant_id = None`; every tenant-level user must carry one, but that's
  enforced in the service layer, not a database `CHECK` — correlating two columns (`tenant_id` and
  `is_platform_user`) with a portable constraint across both PostgreSQL and the SQLite test backend
  isn't practical, so `create_user`/`create_tenant` are the only places a `User` row is ever
  constructed and both hard-code the correct combination.
- **`Role.tenant_id`** follows the same shape: `NULL` = one of the seven platform-seeded system
  roles available to every tenant, set = a tenant-specific custom role (see
  [authorization.md](authorization.md)).
- `build_security_context()` treats `is_platform_user` as **both** `user.tenant_id is None` *and*
  `user.is_platform_user` being true — two independent signals checked together, even though in
  today's seed data (`seed_super_admin`) they're always set as a pair. The dual check is
  defensive, not evidence of a case where they currently diverge.

## Tenant lifecycle

`tenant_service.py`'s module docstring: *"Tenant lifecycle management. Platform-level operations
only (see permission `tenants.*`)."* — every function here is only reachable by a caller holding a
`tenants.*` permission, which per `seed.py` is only `SUPER_ADMIN`.

- **`create_tenant`** — checks `code`/`slug` uniqueness (`get_by_code_or_slug`) and that the
  admin's email isn't already registered (email is globally unique platform-wide, see
  [authentication.md](authentication.md)), inserts the `Tenant` row (`status=ACTIVE`), then in the
  *same* function creates that tenant's first user with the `TENANT_ADMIN` role
  (`tenant_id=None` lookup — raises `NotFoundError` if the platform seed hasn't been run, a
  deliberate hard dependency: there is no tenant without a `TENANT_ADMIN` role to hand it), audits
  `TENANT_CREATED`, and commits. A tenant is never created without an initial admin able to log
  into it.
- **`update_tenant`** — partial update of `name`/`timezone`/`currency` only; audits
  `TENANT_UPDATED` with an old/new snapshot.
- **`suspend_tenant`** — sets `status = SUSPENDED`, audits `TENANT_SUSPENDED`. There is no
  corresponding `reactivate_tenant`/`unsuspend` function in the current codebase.

### `TenantStatus`: ACTIVE / SUSPENDED / INACTIVE

```python
class TenantStatus(enum.StrEnum):
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    INACTIVE = "INACTIVE"
```

Only `ACTIVE` (the default, set at creation) and `SUSPENDED` (set by `suspend_tenant`) are
actually reachable through any service function today. `INACTIVE` exists in the enum but nothing
in the current codebase sets it — there is no deactivate/decommission flow yet. Treat it as
reserved for a later phase, not as evidence of a hidden decommission path.

More importantly: **as of Phase 0, no request path checks `Tenant.status` at all.**
`get_current_user` (`app/security/dependencies.py`) checks `User.status == ACTIVE` but never loads
or inspects that user's `Tenant` row; `auth_service.login()` likewise never looks at tenant status.
So `suspend_tenant` today only records the state change (plus an audit event) for administrative
visibility — it does not log out active sessions, block new logins, or reject API calls for that
tenant's users. Wiring that enforcement in (most naturally as an extra check in
`get_current_user`, alongside the existing `User.status` check) is a reasonable next step, but it
is not implemented, and this document isn't going to guess at behavior that doesn't exist.

## A bug fixed this session: `suspend_tenant`'s `MissingGreenlet`

`suspend_tenant` flips `tenant.status` and calls `session.flush()`; the router then serializes the
result into `TenantResponse`, which reads `tenant.updated_at`. `updated_at` is populated via
`onupdate=func.now()` (`TimestampMixin`, `app/models/base.py`) — a server-side default that only
fires on `UPDATE`. Async SQLAlchemy fetches server-generated columns via `RETURNING` on `INSERT`
automatically, but leaves them **expired** after an `UPDATE` unless told otherwise; reading an
expired attribute normally triggers a transparent lazy-refresh, but under `asyncio` that implicit
refresh happens outside the session's IO-bridging context and raises
`sqlalchemy.exc.MissingGreenlet` instead of quietly working. That's exactly what happened here:
`session.flush()` returned, `tenant.updated_at` was left expired, and the very next line reading it
(inside `TenantResponse.model_validate(tenant)`) crashed.

The fix is global, not a one-off patch to `suspend_tenant`:

```python
class Base(DeclarativeBase):
    __mapper_args__ = {"eager_defaults": True}
```

in `backend/app/core/database.py`. `eager_defaults` makes every mapped model fetch **all**
server-generated defaults via `RETURNING` on both `INSERT` and `UPDATE`, as part of the flush
itself — so `tenant.updated_at` is already populated in memory the moment `session.flush()`
returns, and no implicit lazy-load is ever needed, for `Tenant` or any other model. See
[database.md](database.md) for the fuller mechanics and why this is a mapper-wide option rather
than a per-endpoint `session.refresh(obj)` call.

## Cross-tenant data sharing: out of scope for Phase 0

There is no mechanism anywhere in the current codebase for one tenant to view or share data with
another — no cross-tenant read flag, no shared/global record type beyond genuinely
platform-global reference data (permissions, system roles, units of measurement — see
`docs/database.md`'s model inventory). A platform admin inspecting a specific tenant's data would
need a dedicated platform-admin surface that doesn't exist yet; this is explicitly future work, not
a feature to infer from what's here.
