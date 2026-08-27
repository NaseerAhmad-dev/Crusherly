# Organization

This document covers the organization-unit hierarchy: the internal structure a tenant uses to
model its business units, plants, sites, and departments, and how that structure is referenced for
scoped role assignment. The implementation lives in:

- `backend/app/models/organization.py` — the `OrganizationUnit` model
- `backend/app/models/enums.py` — `OrganizationUnitType`
- `backend/app/repositories/organization_repository.py` — ancestor-chain resolution
- `backend/app/services/user_service.py` — `assign_role()`, the real call site that attaches an
  `organization_unit_id` to a role assignment
- `backend/app/api/v1/users.py` / `backend/app/schemas/user.py` — the HTTP surface for role
  assignment (`POST /api/v1/users/{user_id}/role-assignments`)

See also [multi-tenancy.md](multi-tenancy.md) (every organization unit belongs to exactly one
tenant) and [authorization.md](authorization.md) (how a scoped role assignment turns into a
`PermissionGrant`, and the ancestor-walk that decides what it covers).

## The hierarchy model

`OrganizationUnit` is a single, self-referential table:

```python
class OrganizationUnit(UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin, Base):
    name: Mapped[str]
    code: Mapped[str]
    unit_type: Mapped[OrganizationUnitType]
    parent_id: Mapped[uuid.UUID | None]   # FK -> organization_units.id, ondelete="CASCADE"
    status: Mapped[str]                    # plain string, default "ACTIVE"
```

`OrganizationUnitType` (`app/models/enums.py`) has four members: `BUSINESS_UNIT`, `PLANT`, `SITE`,
`DEPARTMENT`. The conventional nesting is Tenant → Business Unit → Plant → Site → Department, but:

- **The `Tenant` row is the implicit root** — it is not itself an `OrganizationUnit` row. A
  tenant's top-level units simply have `parent_id = None`.
- **Not every level is required.** The model's own docstring says it directly: *"a small tenant may
  attach Plants directly under the Tenant with no Business Unit, by leaving `parent_id` null on a
  `PLANT`-type unit."* A tenant with one plant and no separate business-unit layer is a normal,
  supported shape, not a degenerate case.
- **The type ordering is a convention, not a database constraint.** There is no `CHECK` tying a
  unit's `unit_type` to its parent's `unit_type` — nothing in the schema stops constructing a
  `DEPARTMENT` with `parent_id = None`, or a `PLANT` whose parent is a `SITE`. Enforcing sane
  nesting today would be an application-level validation that doesn't currently exist; this is
  worth knowing before assuming the hierarchy is self-policing.
- **`code` has no uniqueness constraint** in the model (no `UniqueConstraint`, not even scoped to
  `tenant_id`). Two units in the same tenant can currently share a `code`.
- **`status`** is a plain `String(20)` defaulting to `"ACTIVE"`, not typed against the shared
  `MasterDataStatus` enum (`app/models/enums.py`) the way other master-data tables are — as
  implemented today, not a documented design choice.

`OrganizationUnit` mixes in `TenantScopedMixin` (see [multi-tenancy.md](multi-tenancy.md)), so
`tenant_id` is mandatory, indexed, and cascades on tenant deletion — an org unit can never exist
without belonging to exactly one tenant, and it's always the tenant that owns the role assignments
scoped to it.

## Ancestor resolution

`organization_repository.get_self_and_ancestor_ids(session, organization_unit_id)`:

```python
_MAX_DEPTH = 10  # safety bound against a corrupted/cyclic hierarchy

async def get_self_and_ancestor_ids(session, organization_unit_id):
    ids = set()
    current_id = organization_unit_id
    depth = 0
    while current_id is not None and depth < _MAX_DEPTH:
        ids.add(current_id)
        current_id = <parent_id of current_id>
        depth += 1
    return ids
```

Given one org unit, this returns that unit's own id plus every ancestor's id, walking `parent_id`
one row at a time up to the root. The module docstring explains why this is a bounded loop instead
of a recursive CTE: *"the hierarchy is shallow (Tenant -> Business Unit -> Plant -> Site ->
Department, at most 4 levels deep)"* — 10 is a defensive ceiling against a corrupted or
accidentally cyclic `parent_id` chain, not a statement that 10 levels are expected in practice.

This function has exactly one caller: `authorization_service.is_authorized()`, which uses it to
widen a scope check from a specific resource's organization unit outward to every ancestor, so a
grant held at a broader (ancestor) node authorizes resources nested anywhere beneath it. See
[authorization.md](authorization.md#the-scope-walk-algorithm-as-implemented) for the full
algorithm and the unit tests that confirm its exact behavior.

## `organization_unit_id` as the scope anchor

Two different places in the schema carry an `organization_unit_id` for authorization purposes —
see [authorization.md](authorization.md) for how each becomes a `PermissionGrant`:

1. **`UserRole.organization_unit_id`** (nullable FK) — the common single-node case. Per
   `security_context_service`'s own comment, setting this on a role assignment means *"this role
   applies to this org unit and everything beneath it"* — containment is resolved later, at
   authorize-time, via the ancestor walk above, not stored redundantly here. **This is the only
   path Phase 0 actually uses** for scoped role assignment.
2. **`ScopeAssignment.organization_unit_id`** (`app/models/scope.py`) — the general multi-node
   form: a single role assignment can hold several independent `ScopeAssignment` rows, each
   covering a different, non-contiguous org unit. `build_security_context()` reads these rows if
   present, but as of Phase 0 **nothing in `app/services` or `app/api` ever constructs one** — no
   grep hit for `ScopeAssignment(` anywhere outside its own model definition. Multi-node scoping is
   modeled and read, but there is no endpoint to create it yet.

### Real example: `user_service.assign_role`

```python
async def assign_role(
    session, context, user_id, role_id, organization_unit_id, request,
) -> UserRole:
    user = await get_user(session, context, user_id)                       # tenant-scoped fetch
    role = await role_repository.get_visible_to_tenant(session, role_id, context.tenant_id)
    if role is None:
        raise NotFoundError("Role not found.")

    user_role = UserRole(user_id=user.id, role_id=role.id, organization_unit_id=organization_unit_id)
    ...
```

Reached via `POST /api/v1/users/{user_id}/role-assignments`
(`app/api/v1/users.py`, gated by `require_permission("users.update")`), with
`organization_unit_id` coming straight from the request body
(`RoleAssignmentRequest.organization_unit_id: uuid.UUID | None`, `app/schemas/user.py`):

- Passing `organization_unit_id = null` assigns the role **tenant-wide** (unscoped) — this is what
  every demo user in `seed.py` gets.
- Passing a specific org-unit id scopes the assignment to that node and everything beneath it, per
  the ancestor-walk semantics above. This is exactly what the `tenant_a_plant_manager` test fixture
  (`tests/conftest.py`) does: a `MANAGER` role assigned with `organization_unit_id` set to the
  "Pampore" plant, and nothing set for the sibling "Pulwama" plant.
- `role` is looked up via `get_visible_to_tenant`, not a bare `get_by_id` — the same tenant-
  isolation choke point described in [multi-tenancy.md](multi-tenancy.md), so a caller cannot
  assign a role belonging to a different tenant's custom role set.
- **`assign_role` does not verify that `organization_unit_id` actually belongs to `context.tenant_id`**
  (or to the target user's tenant). There is no such check in the function or anywhere in the
  request path. Passing another tenant's org-unit id is not currently rejected. This is a real gap
  in what's implemented, not a documented or intentional behavior — worth knowing rather than
  assuming it's guarded somewhere it isn't.

The resulting `UserRole` row is what `build_security_context()` later reads to produce a
`PermissionGrant` at the org unit's own `ScopeLevel` (`ScopeLevel(unit_type)` — e.g. a `PLANT`-type
org unit yields a `PLANT`-level grant). See
[authorization.md](authorization.md#how-build_security_context-resolves-grants) for that
resolution in full.
