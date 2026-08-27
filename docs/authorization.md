# Authorization

This document covers role-based access control (RBAC) and scope-based authorization as
implemented in Phase 0. The implementation lives in:

- `backend/app/security/security_context.py` — `SecurityContext`, `PermissionGrant`
- `backend/app/services/security_context_service.py` — `build_security_context()`, the only place
  that queries `UserRole`/`RolePermission`/`ScopeAssignment` for authorization purposes
- `backend/app/security/dependencies.py` — `require_authenticated_user`, `require_permission`
- `backend/app/services/authorization_service.py` — `is_authorized()` / `authorize()`
- `backend/app/models/rbac.py` — `Permission`, `Role`, `RolePermission`, `UserRole`
- `backend/app/models/scope.py` — `ScopeAssignment`
- `backend/app/models/enums.py` — `ScopeLevel`
- `backend/app/core/seed.py` — the fixed permission set and the seven system roles
- `backend/tests/unit/test_authorization_service.py` — unit tests exercising the scope-walk logic
  directly; the algorithm described below is read from `authorization_service.py` and confirmed
  against these tests, not guessed at

See also [multi-tenancy.md](multi-tenancy.md) (tenant isolation, which authorization sits on top
of) and [organization.md](organization.md) (the org-unit hierarchy that scope resolves against).

## Two layers: RBAC answers "what", scope answers "where"

Every authorization decision in this codebase is the composition of two independent questions:

1. **RBAC** — does the user hold permission `X` at all, in any capacity? (`SecurityContext.has_permission`)
2. **Scope** — if so, does one of the grants for `X` actually cover *this specific resource*?
   (`authorization_service.is_authorized` / `authorize`)

Route-level gating (`require_permission("users.view")` on `GET /users`) only needs question 1 —
it would be wasteful to resolve a specific resource's organization unit just to decide whether to
show a list endpoint at all. Anything that acts on one specific record (viewing/editing a specific
user, approving a specific document) needs question 2, because a MANAGER scoped to one plant must
not be authorized against another plant's records even though they hold `users.view` somewhere.

## `SecurityContext`: rebuilt from the database on every request

```python
@dataclass(frozen=True)
class PermissionGrant:
    permission_code: str
    scope_level: ScopeLevel
    organization_unit_id: uuid.UUID | None

@dataclass
class SecurityContext:
    user: User
    tenant_id: uuid.UUID | None
    is_platform_user: bool
    role_codes: set[str]
    grants: list[PermissionGrant]
```

`SecurityContext`'s own docstring is explicit about why this is rebuilt every time rather than
cached or carried in the JWT: *"a permission or role change takes effect on the very next
request."* Access tokens (see [authentication.md](authentication.md)) carry nothing but the user's
identity — no roles, no permissions, no scope — precisely so there is nothing stale to invalidate.
`require_authenticated_user` (`app/security/dependencies.py`) is the dependency that ties this
together: it authenticates the bearer token down to a `User` row, then calls
`build_security_context(session, user)` fresh, every request.

`has_permission(code)` is a flat "is this code in `permission_codes` at all" check — it ignores
scope entirely, which is exactly what route-level gating wants. `grants_for(code)` returns every
`PermissionGrant` matching that code, which is what the scope-walk (below) iterates over.

## How `build_security_context` resolves grants

`security_context_service.build_security_context(session, user)`:

1. `is_platform_user = user.tenant_id is None and user.is_platform_user` — both conditions are
   checked defensively even though in the current seed data they always travel together (only
   `seed_super_admin` sets both at once).
2. Load every `UserRole` row for the user in one query, eagerly joining
   `role -> role_permissions -> permission` via `selectinload`. If there are none, return an empty
   `SecurityContext` immediately (`grants == []`, `has_permission()` always `False`) — a user with
   no role assignments is authorized for nothing, not even `dashboard.view`.
3. Load every `ScopeAssignment` row for those `UserRole` ids in one query, bucketed by
   `user_role_id`.
4. For any `UserRole` that carries an `organization_unit_id` but has **no** explicit
   `ScopeAssignment` row, batch-resolve `OrganizationUnit.unit_type` for those org units in one more
   query — needed so the resulting grant reports an accurate `ScopeLevel` (see step 5c).
5. For each `UserRole`, resolve its scope(s) — exactly one of three cases:
   - **(a) Explicit `ScopeAssignment` rows exist for this `UserRole`** — use each row's
     `(scope_level, organization_unit_id)` directly. This is the general form: a single role
     assignment can cover more than one, non-contiguous organization unit.
   - **(b) No explicit rows, but `UserRole.organization_unit_id` is set** — the implicit
     single-node shortcut: `scope_level = ScopeLevel(unit_type)` of that org unit (falling back to
     `DEPARTMENT` if the type lookup somehow came back empty), `organization_unit_id` = that unit.
     Per the code comment, this "covers that unit and everything beneath it" — containment isn't
     resolved here, it's resolved later at authorize-time by walking the *resource's* ancestor
     chain (see below).
   - **(c) Neither** — an unscoped assignment: `PLATFORM` if the user is a platform user, else
     `TENANT`, with `organization_unit_id = None`. This is how every demo tenant user in
     `seed.py` ends up (tenant-wide scoped, no organization unit attached).
6. For every permission code the role grants, cross it with every resolved scope tuple for that
   `UserRole` and append one `PermissionGrant`. A user holding two roles (or the same role at two
   different org units) accumulates grants from both — nothing is deduplicated or overwritten.

The result: `SecurityContext.grants` is a flat list of `(permission_code, scope_level,
organization_unit_id)` triples, one for every permission x scope combination the user actually
holds, ready for `authorization_service` to consult.

## `require_permission` vs `authorize()`

Two entry points, for two different questions:

- **`require_permission(permission_code)`** (`app/security/dependencies.py`) — a FastAPI dependency
  factory. Raises `ForbiddenError` (403) unless `context.has_permission(permission_code)` — i.e.
  unless the caller holds the permission at *any* scope at all. Used at the route level for coarse
  gating, e.g. `GET /api/v1/users` depends on `require_permission("users.view")`.
- **`authorize(session, context, permission_code, resource_organization_unit_id)`**
  (`app/services/authorization_service.py`) — an awaitable called from inside a route or service
  once a specific resource (and its organization unit) is known. Raises `ForbiddenError` unless a
  grant for that permission actually covers that resource's organization unit. `is_authorized()` is
  the boolean-returning function it wraps, and is what the unit tests call directly.

Both dependencies module and service module say this explicitly in their own docstrings: every
future business module must go through one of these two rather than reimplementing tenant/scope
logic itself.

## The scope-walk algorithm, as implemented

`ScopeLevel` (`app/models/enums.py`) is ordered broadest to narrowest:

```
PLATFORM > TENANT > BUSINESS_UNIT > PLANT > SITE > DEPARTMENT
```

`authorization_service.is_authorized(session, context, permission_code, resource_organization_unit_id)`:

1. `grants = context.grants_for(permission_code)`. No grants for this code at all → `False`
   immediately, regardless of scope (confirmed by
   `test_missing_permission_denied_regardless_of_scope`: a plant-scoped MANAGER holding
   `users.view` at their own plant is still denied `tenants.delete` there — RBAC is checked before
   scope, not instead of it).
2. For each grant, in order:
   - **`scope_level is PLATFORM`** → `True` immediately. A platform-wide grant covers everything
     (confirmed by `test_platform_super_admin_authorized_everywhere`).
   - **`scope_level is TENANT`** → `True` immediately, *without comparing organization units at
     all* (confirmed by `test_tenant_admin_authorized_for_every_plant`, which checks the same
     TENANT_ADMIN against two different plants and gets `True` both times). This is safe because
     tenant isolation is enforced earlier, at the point the resource was fetched — the resource is
     never even loaded across a tenant boundary (see [multi-tenancy.md](multi-tenancy.md)), so by
     the time `is_authorized` runs, "same tenant" is already guaranteed and a TENANT-level grant is
     sufficient on its own.
   - **`resource_organization_unit_id is None`** (and the grant is narrower than TENANT) → this
     grant cannot satisfy the check; skip to the next grant. A node-scoped grant cannot cover a
     resource that isn't tied to any organization unit (e.g. a tenant-wide setting).
   - **`grant.organization_unit_id == resource_organization_unit_id`** → `True` (exact node match).
   - **Otherwise, widen from the resource upward**: resolve
     `get_self_and_ancestor_ids(session, resource_organization_unit_id)`
     (`app/repositories/organization_repository.py` — walks `parent_id` up to the root, bounded at
     10 levels as a safety guard against a corrupted/cyclic hierarchy) once per call, and check
     whether `grant.organization_unit_id` is among the resource's own id + its ancestors. If so,
     `True`.
3. If no grant matched by the end, `False`.

The walk direction matters: it climbs from the **resource** up toward the root, checking whether
any held grant matches something on that path. It never walks *down* from a grant to see whether a
resource is nested somewhere beneath it. The practical effect is that a grant at a broader
(ancestor) node authorizes every resource nested beneath it, but a grant at a narrower
(descendant) node never authorizes a resource above it — a DEPARTMENT-scoped grant does not cover
its parent PLANT.

This is exercised directly by `tests/unit/test_authorization_service.py`, using a fixture tenant
with two sibling `PLANT` units ("Pampore" and "Pulwama") and a MANAGER scoped only to Pampore:

| Test | Confirms |
|---|---|
| `test_plant_scoped_manager_authorized_for_own_plant` | A grant scoped to a plant covers a resource at that exact plant. |
| `test_plant_scoped_manager_denied_for_other_plant` | The same grant does **not** cover a sibling plant — scope doesn't leak sideways. |
| `test_tenant_admin_authorized_for_every_plant` | A TENANT-level grant covers every plant in the tenant without an ancestor walk. |
| `test_platform_super_admin_authorized_everywhere` | A PLATFORM-level grant short-circuits before any org-unit comparison. |
| `test_missing_permission_denied_regardless_of_scope` | RBAC gates first — no grant for the code at all means denial regardless of how broad any *other* grant's scope is. |
| `test_user_with_no_roles_has_no_grants` | A user with zero `UserRole` rows gets `grants == []` and fails every `has_permission` check, including baseline ones like `dashboard.view`. |

## Permission codes are stable strings, not database IDs

`Permission.code` (e.g. `"users.view"`, `"production.update"`) is what every authorization check
compares against — never `Permission.id`. `rbac.py`'s module docstring states the reason directly:
*"roles and permissions can be reseeded/renumbered without breaking authorization checks elsewhere
in the codebase."* `seed.py` is idempotent specifically so it can run repeatedly against the same
environment (it looks up every row by natural key — `code` for permissions and roles — before
inserting), and nothing in the codebase holds onto a `Permission.id`/`Role.id` value across a
reseed. This also means a permission code is effectively part of the codebase's contract with
itself: introducing `production.update` in a later phase is additive and safe, but renaming an
existing code silently breaks every `require_permission("old.code")` call site.

## Models

- **`Permission`** — a global, platform-wide `(code, description, module)` row. No `tenant_id`;
  the same permission set applies everywhere.
- **`Role`** — a named bundle of permissions via `RolePermission`. `tenant_id` is nullable: `NULL`
  means one of the seven platform-seeded system roles (available to every tenant), a real value
  means a tenant-specific custom role. `is_system=True` marks the seeded roles. Unique constraint
  is `(tenant_id, code)` — a tenant's custom role code only needs to be unique within that tenant,
  not against every other tenant's custom roles or the system role codes.
- **`RolePermission`** — pure join table, `(role_id, permission_id)` composite primary key,
  cascades on either side.
- **`UserRole`** — assigns one `Role` to one `User`, with an optional
  `organization_unit_id` for the common single-node scoping case. Unique constraint is `(user_id,
  role_id, organization_unit_id)`, so the same user can hold the same role multiple times as long
  as each assignment is scoped to a different organization unit (or one unscoped + several scoped).
- **`ScopeAssignment`** (`app/models/scope.py`) — the general-purpose form: one `UserRole` can have
  *multiple* `ScopeAssignment` rows, each an independent `(scope_level, organization_unit_id)`
  pair, for when a single role assignment needs to cover more than one non-contiguous node.
  `build_security_context` reads these rows (step 5a above), but as of Phase 0 **nothing in
  `app/services` or `app/api` ever constructs one** — role assignment always goes through
  `UserRole.organization_unit_id`'s single-node shortcut instead (see
  [organization.md](organization.md) for the real call site). `ScopeAssignment` is modeled and
  wired into the read path ahead of having a write path; treat multi-node scoping as designed-for
  but not yet reachable through any endpoint.

## Seed data: the seven system roles

`seed.py` defines a fixed set of 20 permissions across five modules (`platform`, `identity`,
`authz`, `tenancy`, `documents`) and wires each of the seven system roles to an explicit subset.
This is the actual table, read from `SYSTEM_ROLES` in `backend/app/core/seed.py` — not inferred
from role names:

| Permission | SUPER_ADMIN | TENANT_ADMIN | MANAGER | OPERATOR | ACCOUNTANT | STOREKEEPER | VIEWER |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| `dashboard.view` | X | X | X | X | X | X | X |
| `users.view` | X | X | X | | | | |
| `users.create` | X | X | | | | | |
| `users.update` | X | X | | | | | |
| `users.delete` | X | X | | | | | |
| `roles.view` | X | X | | | | | |
| `roles.create` | X | X | | | | | |
| `roles.update` | X | X | | | | | |
| `roles.delete` | X | X | | | | | |
| `permissions.view` | X | X | | | | | |
| `tenants.view` | X | | | | | | |
| `tenants.create` | X | | | | | | |
| `tenants.update` | X | | | | | | |
| `tenants.delete` | X | | | | | | |
| `settings.view` | X | X | X | | | | |
| `settings.update` | X | X | | | | | |
| `audit.view` | X | X | X | | | | |
| `documents.view` | X | X | X | X | X | X | X |
| `documents.upload` | X | X | X | X | X | X | |
| `documents.delete` | X | X | | | | | |

Notes on what this actually encodes:

- **SUPER_ADMIN** gets all 20 permissions, unconditionally — the only role wired to `tenants.*`,
  since tenant lifecycle is a platform-level concern (`Role.tenant_id IS NULL`, and in practice
  only ever assigned to the platform user seeded by `seed_super_admin`).
- **TENANT_ADMIN** gets everything except `tenants.*` (16 of 20) — full control within a tenant
  (users, roles, permissions viewing, settings, audit, documents) but cannot create/update/suspend
  tenants themselves.
- **MANAGER** gets 6: `dashboard.view`, `users.view`, `settings.view`, `audit.view`,
  `documents.view`, `documents.upload` — can see users and settings and read the audit trail
  within their assigned scope, but not create/edit users or roles.
- **OPERATOR**, **ACCOUNTANT**, and **STOREKEEPER** are currently **identical**: `dashboard.view`,
  `documents.view`, `documents.upload` (3 permissions each). Nothing in the current permission set
  is finance- or inventory-specific yet — those distinctions arrive with the Finance and Inventory
  business modules in later phases (per the README's phase plan). Today these three roles exist as
  distinct, seeded identities mainly so the demo tenant can demonstrate that role assignment works
  per-user, not because their grants currently differ.
- **VIEWER** gets 2: `dashboard.view`, `documents.view` — read-only, and not even
  `documents.upload`.

Every non-platform system role is granted **tenant-wide by default** in the demo data
(`seed_demo_tenant_and_users` assigns each with no `organization_unit_id`), which resolves to a
`TENANT`-level grant per case 5c above — deliberately chosen so role differences are visible
immediately without first setting up a plant/site hierarchy. Plant/site-scoped assignment (case 5b)
is what the `tenant_a_plant_manager` test fixture exercises instead — see
[organization.md](organization.md) for how `organization_unit_id` is actually attached to a role
assignment through `user_service.assign_role`.
