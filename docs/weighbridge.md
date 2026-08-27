# Weighbridge

Weighbridge is Phase 2's business module (see
[docs/phases/phase-2-completion.md](phases/phase-2-completion.md) for why it isn't Phase 1): it
records the two weighments every truck goes through at a stone-crushing plant — one when it
arrives, one once its load has been handled — and derives the net weight from the difference.
Everything else in this document explains how that simple idea is actually wired into the Phase 0
platform foundation.

## The ticket lifecycle

A `WeighbridgeTicket` (`app/models/weighbridge.py`) moves through three states
(`WeighbridgeTicketStatus` in `app/models/enums.py`):

```
OPEN ──complete──> COMPLETED
OPEN ──cancel───> CANCELLED
```

- **`POST /api/v1/weighbridge/tickets`** creates a ticket in `OPEN` status. This records the
  *first* weighment — the vehicle's weight as it currently is (e.g. empty, arriving to load an
  outbound order, or loaded, arriving to deliver an inbound purchase). `first_weighed_at` is
  stamped server-side (`datetime.now(UTC)`) at creation time, not supplied by the client.
- **`POST /api/v1/weighbridge/tickets/{id}/complete`** records the *second* weighment and closes
  the ticket. This is only legal from `OPEN` — `weighbridge_service.complete_ticket()` raises a
  409 (`ConflictError`) with the message `"Ticket is {status}, not open."` if called against a
  ticket that's already `COMPLETED` or `CANCELLED`.
- **`POST /api/v1/weighbridge/tickets/{id}/cancel`** moves an `OPEN` ticket to `CANCELLED` (e.g.
  the vehicle left without loading). A ticket that has already reached `COMPLETED` cannot be
  cancelled — `cancel_ticket()` raises a 409 with `"A completed ticket cannot be cancelled."` A
  ticket that is already `CANCELLED` can be cancelled again; the service only special-cases
  `COMPLETED`.

There is no route to reopen a `COMPLETED` or `CANCELLED` ticket. Once a ticket leaves `OPEN`, it is
done.

## The two-weighment model and net weight

`WeighbridgeTicket` stores both readings directly on the ticket row, not as separate child
records:

| Field | Set when | Nullable |
|---|---|---|
| `first_weight` / `first_weighed_at` | ticket created | no |
| `second_weight` / `second_weighed_at` | ticket completed | yes (until completed) |
| `net_weight` | ticket completed | yes (until completed) |

Net weight is computed once, at completion, as `abs(first_weight - second_weight)` (see
`weighbridge_service.complete_ticket()`). Using `abs()` rather than a fixed subtraction order is
deliberate: for an `INBOUND` ticket a loaded truck typically arrives first and leaves empty
(`first > second`), while for an `OUTBOUND` ticket an empty truck arrives first and leaves loaded
(`first < second`) — one formula covers both `WeighbridgeTicketType` values without the caller
having to know which order to expect. `ticket_type` itself (`INBOUND` / `OUTBOUND`) is stored but
does not change how the net weight is calculated; it only records the direction of material
movement for reporting.

All three weight columns are `Numeric(12, 3)` — three decimal places, matching the payload
validation (`Field(gt=0)` on `first_weight` and `second_weight` in `app/schemas/weighbridge.py`,
and the frontend's own `^\d+(\.\d{1,3})?$` input pattern in both ticket dialogs). Weights must be
strictly positive; there is no validation that `second_weight` differs from `first_weight` (a
net weight of zero is accepted — it is not the service's job to guess that this is unusual).

## How it builds on Phase 0 rather than inventing its own plumbing

`weighbridge_service.py`'s own module docstring states the point directly: every state change
goes through the platform foundation, not module-specific logic.

- **`numbering_service.next_number()`** issues `ticket_number` on creation, scoped to
  `(tenant, organization_unit, document_type="WEIGHBRIDGE_TICKET", fiscal_year_code)` with prefix
  `"WBT"` — so a ticket number looks like `WBT-000001`. Because the sequence is scoped per
  organization unit and fiscal year, two different plants (or the same plant in two different
  fiscal years) can both produce `WBT-000001` without colliding; the actual uniqueness constraint
  on the table (`uq_weighbridge_ticket_number`) is `(tenant_id, ticket_number)`, which numbering
  the sequence per-organization-unit-and-year happens to always satisfy in practice.
- **`audit_service.record()`** is called after every state change — creation, completion, and
  cancellation each write an `AuditEvent` in the same transaction as the ticket mutation, using
  three new `AuditAction` members added specifically for this module:
  `WEIGHBRIDGE_TICKET_CREATED`, `WEIGHBRIDGE_TICKET_COMPLETED`, `WEIGHBRIDGE_TICKET_CANCELLED`
  (`app/models/enums.py`). This is the pattern documented in [docs/audit.md](audit.md) — the audit
  trail states explicitly what happened rather than being inferred from HTTP traffic.
- **`OrganizationUnit`** (via `organization_unit_id`, nullable, `ON DELETE SET NULL`) records which
  plant the ticket happened at. This is also the field scope-based authorization checks against
  (see below) — it is not just informational.
- **`Unit`** (via `unit_id`, required, `ON DELETE RESTRICT`) supplies the weight's unit of measure
  (in practice, `ton` from the seeded unit set). `RESTRICT` rather than `SET NULL` here is
  deliberate: a ticket without a unit is meaningless, whereas a ticket without a plant is at least
  interpretable as tenant-wide.

## Scope-based authorization: the first real exercise of `authorize()`

Weighbridge is genuinely the first place in the codebase where
`authorization_service.authorize()` is checked against a real business resource rather than
described only in [docs/authorization.md](authorization.md) as a mechanism. Every mutating action
calls it explicitly, in addition to (not instead of) the coarser route-level `require_permission`
dependency:

```python
# app/api/v1/weighbridge.py
context: SecurityContext = Depends(require_permission("weighbridge.create"))

# app/services/weighbridge_service.py
await authorization_service.authorize(session, context, "weighbridge.create", payload.organization_unit_id)
```

`require_permission` answers "can this user create weighbridge tickets at all" — a coarse RBAC
check with no notion of which plant. `authorize()` then answers the sharper question: "does this
user's grant for `weighbridge.create` cover *this specific ticket's* organization unit." The
distinction matters in practice, and the test suite (`tests/integration/test_weighbridge.py`)
exercises it directly:

- An `OPERATOR` scoped to one plant (e.g. Pampore) can create and complete tickets for that plant,
  but gets a 403 attempting to create a ticket against a different plant in the same tenant (e.g.
  Pulwama) — even though the `OPERATOR` role itself holds `weighbridge.create`.
- A `MANAGER` scoped to one plant likewise gets a 403 completing a ticket that was created against
  a different plant.
- A `TENANT_ADMIN`, whose grant is tenant-wide (`ScopeLevel.TENANT`, no specific organization
  unit), can create and complete tickets for *any* plant in their tenant — tenant-level grants
  short-circuit `authorize()` to "yes" without ever inspecting the ticket's organization unit (see
  `authorization_service.is_authorized()`).
- A `VIEWER` (no `weighbridge.create` permission at all) gets a 403 from `require_permission`
  before `authorize()` is ever reached.

`complete_ticket()` and `cancel_ticket()` both authorize against the *ticket's own*
`organization_unit_id` (fetched via `get_ticket()`, not the caller's), using the
`weighbridge.update` permission for both actions — there is no separate `weighbridge.cancel`
permission.

## The fiscal-year prerequisite

Ticket numbering is scoped per fiscal year, so `create_ticket()` looks up the tenant's active
`FiscalYear` (`fiscal_year_repository.get_active_for_tenant()`) before doing anything else. If none
exists, it raises a 409 `ConflictError`:

> "No active fiscal year is configured for this tenant. An administrator must set one up before
> recording weighbridge tickets."

Phase 0 modeled `FiscalYear` (`app/models/fiscal_year.py`) but nothing ever created one — there was
no business module that needed to number a document against it yet. `app/core/seed.py` now has a
`seed_fiscal_year()` step (called from `seed_demo_tenant_and_users()`) that creates one active
April–March fiscal year for the demo tenant, matching the Indian financial-year convention implied
by `DEMO_TENANT`'s `timezone`/`currency`. There is still no API route to create or manage fiscal
years — for now, the only way a tenant gets one is the seed script (for the demo tenant) or a
direct database insert (for any other tenant). That gap is real: a production tenant onboarded
through the tenant-management API today has no self-service way to open a fiscal year before its
first weighbridge ticket, only this 409 telling them one is missing.

## Reference-data endpoints: `units` and `organization-units`

Weighbridge's create form needs to let the user pick a weight unit and, optionally, a plant.
Phase 0 built the `Unit` and `OrganizationUnit` models and their master-data tables, but never
built any API surface to read them — nothing needed to before now. Two small read-only endpoints
were added specifically to unblock this form:

- **`GET /api/v1/units`** (`app/api/v1/units.py`) — the full unit vocabulary (`kg`, `ton`, `litre`,
  ...), gated only by `require_authenticated_user`. Units are global reference data, not
  tenant-scoped (there's one `units` table shared platform-wide), so any authenticated user —
  platform or tenant — can read it, the same as they could any other fixed dropdown of allowed
  values.
- **`GET /api/v1/organization-units`** (`app/api/v1/organization_units.py`) — every organization
  unit in the caller's own tenant, also gated only by `require_authenticated_user`. Organization
  units *are* tenant-scoped, so this one raises a 403 (`ForbiddenError`) for a platform user with
  no `tenant_id` on their context, and otherwise scopes strictly to `context.tenant_id`
  (`organization_repository.list_for_tenant()`).

Neither endpoint takes a permission argument beyond "authenticated" — they exist purely to
populate pickers, not to gate access to sensitive data, and unlike the ticket endpoints they carry
no scope-based authorization check of their own (a `PLANT`-scoped operator can still list *all* of
their tenant's plants, they just can't act against one outside their own grant).

## What's genuinely denormalized: vehicle, driver, party are free text

`vehicle_number`, `driver_name`, and `party_name` are plain `String` columns on
`WeighbridgeTicket`, not foreign keys into a `Vehicle` or customer/supplier master table — because
those tables don't exist yet. There is no Vehicles module and no Party/Customer/Supplier master in
the codebase as of this phase. This is a deliberate "denormalize now, normalize when the real
module lands" choice, not an oversight: a stone-crushing plant needs to record weighbridge tickets
from day one, and making that wait on a Vehicles module and a customer/supplier master (both
larger, independent pieces of work) would block the first operational transaction on unrelated
scope. `vehicle_number` is upper-cased server-side on create (`payload.vehicle_number.upper()`) so
at least basic consistency exists without a real registry backing it; `driver_name` and
`party_name` have no normalization at all beyond a max length.

When a Vehicles module and a customer/supplier master do land, the expected migration path is to
add `vehicle_id` / `party_id` foreign keys alongside (or in place of) these free-text fields and
backfill by matching on the text — not designed yet, but the free-text columns don't foreclose it.

## Frontend

`frontend/src/app/weighbridge/` has three standalone components: `WeighbridgeListComponent` (the
paginated ticket list, with per-row "Complete" and "Cancel" actions gated on ticket status client-
side — the buttons are always rendered, the actions themselves still hit the real API which is
what actually enforces scope and state), `WeighbridgeTicketDialogComponent` (create — the first
weighment), and `WeighbridgeCompleteDialogComponent` (the second weighment). Both dialogs validate
weight input against the same `^\d+(\.\d{1,3})?$` pattern the backend's `Numeric(12, 3)` columns
imply. `WeighbridgeService` and `ReferenceService`
(`frontend/src/app/core/services/`) are thin HTTP wrappers with no business logic, matching every
other frontend service in the codebase. The nav item (`Weighbridge`, gated on `weighbridge.view`)
was added to `frontend/src/app/layout/shell.component.ts`, and the route to
`frontend/src/app/app.routes.ts`, gated by the same permission via `permissionGuard`.

There are no dedicated unit tests (`.spec.ts`) for the three weighbridge components or the two new
reference/weighbridge services — frontend test coverage for this module is currently zero;
correctness is exercised only through the backend's integration tests
(`tests/integration/test_weighbridge.py`, `tests/integration/test_reference_data.py`) and manual
verification. See [docs/phases/phase-2-completion.md](phases/phase-2-completion.md) for the exact
numbers.
