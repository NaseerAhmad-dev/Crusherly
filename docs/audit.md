# Audit

The platform keeps a single, append-only audit trail: `AuditEvent`
(`app/models/audit.py`), written exclusively through `app.services.audit_service.record()`
(Master Build Specification section 15). Every service that changes something meaningful —
tenant lifecycle, authentication, RBAC, settings — calls `record()` in the same transaction as the
change it's describing. There is no generic "audit middleware" that infers events from HTTP
traffic; each call site states explicitly what happened.

## What's captured

Each `AuditEvent` row records:

- **actor** — `user_id` (nullable: a failed login against an email that doesn't exist has no
  user to attribute).
- **tenant** — `tenant_id` (nullable: platform-level actions such as creating a tenant, or a
  login attempt before tenant context is known, aren't scoped to one tenant).
- **action** — a free-text `String(100)`, in practice always one of the `AuditAction` enum values
  (see below), but the column itself isn't a DB enum — `audit_service.record()` takes `action: str`
  so call sites can pass either `AuditAction.TENANT_CREATED.value` or a literal string like
  `"DOCUMENT_UPLOADED"` for events that don't (yet) have a dedicated enum member.
- **resource_type / resource_id** — what was acted on (e.g. `"tenant"`, `"user"`, `"attachment"`)
  and its id, as a string.
- **old_data / new_data** — arbitrary JSON snapshots of before/after state, stored via
  `portable_json()` (see `app/models/base.py`). Both are optional and independent: a create only
  sets `new_data`, a delete only sets `old_data`, an update sets both, and simple actions like
  `LOGIN` or `LOGOUT` set neither.
- **ip_address / user_agent / request_id** — pulled from the inbound `Request` when one is
  available (`request.client.host`, the `user-agent` header, and `request.state.request_id`).
  Background/internal calls that don't have a `Request` (e.g. `logout()` in some call paths)
  simply leave these null — `record()` accepts `request: Request | None`.
- **timestamp** — server-side `func.now()`, not application clock time, so ordering is
  authoritative even across app instances with clock drift.

## Why insert-only

`AuditEvent` has no update or delete path anywhere in the codebase, by design:

- The model docstring states it plainly: "Normal application code must only INSERT rows here...
  No API route exposes update/delete for audit events."
- `audit_service.py` repeats the same constraint: "there is intentionally no repository function
  to do so" — `audit_repository.py` only exports `add()` and `list_events()`, nothing else.
- The read API, `app/api/v1/audit.py`, is explicitly documented as "Read-only audit trail. No
  route here ever updates or deletes an AuditEvent."

This is what makes the trail trustworthy as an audit log rather than just another mutable table:
if a row can be edited or removed after the fact, it can't be relied on as evidence of what
actually happened. The only way an audit event stops existing is a manual DBA-level deletion
outside the application, which is by definition outside the system's own trust boundary.

## How services call it

`audit_service.record()` is the single shared entry point (`app/services/audit_service.py`). Its
signature:

```python
async def record(
    session: AsyncSession,
    *,
    action: str,
    resource_type: str,
    resource_id: str | None = None,
    tenant_id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
    old_data: dict[str, Any] | None = None,
    new_data: dict[str, Any] | None = None,
    request: Request | None = None,
) -> AuditEvent
```

It builds the `AuditEvent`, adds it via `audit_repository.add()`, and flushes (not commits) —
the caller's own `session.commit()` covers both the business-data change and the audit row as one
atomic unit. This is the pattern seen at every call site:

- **`tenant_service.py`** — `create_tenant()`, `update_tenant()`, and `suspend_tenant()` each call
  `audit_service.record()` with `AuditAction.TENANT_CREATED` / `TENANT_UPDATED` / `TENANT_SUSPENDED`
  right after the tenant row is flushed, then commit once. `update_tenant()` is a good example of
  the old/new pattern: it snapshots `old_data` before mutating the tenant, then passes both
  `old_data` and the post-mutation `new_data`.
- **`auth_service.py`** — `login()` records `LOGIN_FAILED` on both a bad password and an inactive
  account (with a `new_data={"reason": ...}` explaining which), and `LOGIN` on success; `logout()`
  records `LOGOUT`. Notably, `LOGIN_FAILED` against an unknown email still records an event with
  `user_id=None` and `resource_id=None` — the attempt itself is worth capturing even with no user
  to attribute it to.
- **`attachment_service.py`** — records `"DOCUMENT_UPLOADED"` and `"DOCUMENT_DELETED"` as literal
  strings (not yet promoted to `AuditAction` members), showing that the action vocabulary is
  expected to grow as more services adopt auditing, without requiring an enum change to unblock a
  new call site.

## The `AuditAction` enum

`app/models/enums.py` currently defines:

```
LOGIN, LOGIN_FAILED, LOGOUT,
USER_CREATED, USER_UPDATED, USER_DISABLED,
ROLE_CREATED, ROLE_UPDATED, ROLE_DELETED, PERMISSION_CHANGED,
TENANT_CREATED, TENANT_UPDATED, TENANT_SUSPENDED,
SETTINGS_CHANGED
```

This is the vocabulary for identity/tenancy/RBAC events emitted by Phase 0's own services. It is
not meant to be exhaustive for all future business documents — `attachment_service.py` already
demonstrates that a service can record an action string outside this enum. Future business
modules are expected to either extend `AuditAction` or use their own descriptive action strings,
following the same `record()` contract.

`AuditAction` is defined once in `app/models/enums.py` and re-exported from
`app/models/audit.py` purely for call-site convenience (`from app.models.audit import
AuditAction`); the canonical definition lives in `enums.py`.

## Reading the trail

`GET /api/v1/audit` (`app/api/v1/audit.py`) is the only route on this data, gated by the
`audit.view` permission, and supports:

- `page` / `page_size` (max 200 per page)
- `action` — exact match on the action string
- `resource_type` — exact match
- `user_id` — exact match
- `date_from` / `date_to` — inclusive range on `timestamp`

Tenant scoping happens automatically, not via a query parameter: the route passes
`context.tenant_id` straight into `audit_repository.list_events()`, so a tenant-scoped caller only
ever sees their own tenant's events, while a platform user (no `tenant_id` on their context) sees
the platform-wide trail. This mirrors how `tenants.view` already separates platform vs. tenant
administration elsewhere in the API. Results are ordered newest-first
(`AuditEvent.timestamp.desc()`).

The frontend's audit list (`frontend/src/app/audit/audit-list.component.ts`) exposes `action` and
`resource_type` as its filter fields against this endpoint, and renders timestamp, action,
resource type, resource id, and user id as table columns — a direct, unadorned view over what the
API returns, with no client-side interpretation of the JSON payloads.
