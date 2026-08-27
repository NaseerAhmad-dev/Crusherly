# Production

Production is Phase 3's business module (there is no Phase 2 in this codebase — see
[docs/phases/phase-3-completion.md](phases/phase-3-completion.md) for why the numbering has a
gap). It records one plant's one shift of crushing: the raw material consumed and the graded
outputs it produced. Everything else in this document explains how that idea is wired into the
Phase 0 foundation, following the same pattern [Weighbridge](weighbridge.md) already established.

## The entry lifecycle

A `ProductionEntry` (`app/models/production.py`) moves through three states
(`ProductionEntryStatus` in `app/models/enums.py`):

```
DRAFT ──submit──> SUBMITTED
DRAFT ──cancel──> CANCELLED
SUBMITTED ──cancel──> CANCELLED
```

- **`POST /api/v1/production/entries`** creates an entry in `DRAFT` status, together with all of
  its output lines in the same request (see below) — there is no separate "add an output" endpoint.
- **`POST /api/v1/production/entries/{id}/submit`** finalizes the shift's numbers. This is only
  legal from `DRAFT` — `production_service.submit_entry()` raises a 409 (`ConflictError`) with
  `"Entry is {status}, not draft."` if called against an already-`SUBMITTED` or `CANCELLED` entry.
- **`POST /api/v1/production/entries/{id}/cancel`** moves either a `DRAFT` or a `SUBMITTED` entry to
  `CANCELLED` (e.g. a mis-recorded shift). Unlike Weighbridge's ticket cancellation, this is
  intentionally allowed from `SUBMITTED` too — a shift can be finalized and still need voiding
  later by an admin. Only an already-`CANCELLED` entry is rejected, with `"Entry is already
  cancelled."`

There is no route to reopen a `CANCELLED` entry, and no route to edit a `SUBMITTED` one — the only
thing you can do to a submitted entry is cancel it.

## Outputs are a child table, not a single quantity

A `ProductionEntry` has a one-to-many `outputs: list[ProductionOutput]` relationship
(`cascade="all, delete-orphan"`), because a real crushing run is graded into more than one product
in the same shift — 50 tons of 40mm aggregate, 30 tons of 20mm, 10 tons of dust from one input feed
is the normal case, not the exception. `ProductionEntryCreateRequest.outputs` requires at least one
line (`Field(min_length=1)`); the API rejects an entry with zero outputs at the schema-validation
layer (422), before the service is ever called.

Each `ProductionOutput` has its own `product_description` (free text — see below),
`quantity` (`Numeric(12, 3)`), and `unit_id`. The parent entry's `raw_material_quantity` and the
sum of its outputs' quantities are not reconciled against each other anywhere — nothing enforces
that outputs add up to (or don't exceed) the raw material consumed. That's a deliberate absence,
not a gap: crushing has real yield loss and by-products that make a strict mass-balance check
either wrong or premature to encode without knowing the actual expected yield ratios for this
business.

Reading `entry.outputs` back out is where the child-table relationship needed care: fetching an
existing `ProductionEntry` and serializing `outputs` into the response schema happens outside any
`await` on the session, so an un-eager-loaded relationship would trigger the exact `MissingGreenlet`
failure mode documented in [docs/database.md](database.md) — the same class of bug fixed earlier
this session for `Base.__mapper_args__`. `production_repository.get_by_id_in_tenant()` and
`list_in_tenant()` both explicitly `.options(selectinload(ProductionEntry.outputs))`, matching the
existing convention in `security_context_service.py` and `seed.py` (explicit `selectinload()` at
the query call site, not a mapper-level `lazy="selectin"` default) rather than introducing a new
pattern. Objects created and appended to `entry.outputs` in the same transaction as the parent (the
`create_entry()` path) don't need this — SQLAlchemy already has them in memory from being added,
no round trip required — but anything fetched fresh from the database does.

## How it builds on Phase 0 and Phase 1 rather than inventing its own plumbing

- **`numbering_service.next_number()`** issues `entry_number` on creation, scoped to
  `(tenant, organization_unit, document_type="PRODUCTION_ENTRY", fiscal_year_code)` with prefix
  `"PRD"` — an entry number looks like `PRD-000001`. Same mechanism, same fiscal-year prerequisite,
  as Weighbridge's `WBT-` numbers.
- **`audit_service.record()`** is called after every state change, using three new `AuditAction`
  members: `PRODUCTION_ENTRY_CREATED`, `PRODUCTION_ENTRY_SUBMITTED`, `PRODUCTION_ENTRY_CANCELLED`.
- **`OrganizationUnit`** (via `organization_unit_id`, nullable, `ON DELETE SET NULL`) records which
  plant the shift happened at, and is what scope-based authorization checks against.
- **`Unit`** supplies the unit of measure for both the raw material quantity and each output line
  independently — a single entry can record its raw material in tons and one output in kilograms if
  that's genuinely how it was measured; nothing forces every quantity on an entry to share one unit.
- **The fiscal-year prerequisite is identical to Weighbridge's.** `create_entry()` looks up the
  tenant's active `FiscalYear` before numbering anything and raises the same 409 message if none
  exists. No new fiscal-year infrastructure was added for this phase; it reuses
  `fiscal_year_repository.get_active_for_tenant()` exactly as-is.

## Scope-based authorization

Every mutating action calls `authorization_service.authorize()` against the *entry's*
`organization_unit_id`, in addition to the coarser route-level `require_permission` dependency —
the same two-layer pattern documented in [docs/weighbridge.md](weighbridge.md#scope-based-authorization-the-first-real-exercise-of-authorize).
`tests/integration/test_production.py` exercises the identical scenarios Weighbridge's suite does,
reusing the same `tenant_a_plants`/`tenant_a_operator`/`tenant_a_plant_manager` fixtures from
`tests/conftest.py` rather than duplicating them:

- An `OPERATOR` scoped to one plant can create and submit entries for that plant, but gets a 403
  creating an entry against a different plant in the same tenant.
- A `MANAGER` scoped to one plant gets a 403 submitting an entry that was created against a
  different plant.
- A `TENANT_ADMIN` (tenant-wide grant) can act on entries for any plant in their tenant.
- A `VIEWER` (no `production.create`) gets a 403 from `require_permission` before `authorize()` is
  ever reached.

`submit_entry()` and `cancel_entry()` both authorize against the permission `production.update` —
there is no separate `production.submit` or `production.cancel` permission, mirroring Weighbridge's
single `weighbridge.update` covering both of its state-changing actions.

## What's genuinely denormalized: raw material and product are free text

`raw_material_description` on the entry and `product_description` on each output are plain
`String` columns, not foreign keys into a Product/Item master — because no such master exists yet.
This is the same "denormalize now, normalize when the real module lands" trade-off Weighbridge
already made for `vehicle_number`/`driver_name`/`party_name` (see
[docs/weighbridge.md](weighbridge.md#whats-genuinely-denormalized-vehicle-driver-party-are-free-text)),
applied consistently rather than reinvented for this module.

This phase also does **not** link a `ProductionEntry` to the `WeighbridgeTicket`(s) that supplied
its raw material, even though conceptually a shift's input often *is* one or more inbound
weighbridge tickets. Modeling that relationship (which tickets fed which entry, and in what
proportion when a shift blends more than one) is a real design question — not a small addition —
and was deliberately left out rather than guessed at.

## Frontend

`frontend/src/app/production/` has two standalone components: `ProductionListComponent` (the
paginated entry list — the "Outputs" column renders a plain joined summary string, e.g.
`"40mm Aggregate: 8000.000, Dust: 2000.000"`, not a nested table) and
`ProductionEntryDialogComponent` (create). The create dialog is the first place in the frontend
that uses a Reactive Forms `FormArray` — `outputs` — with "Add output" / per-row delete controls
(the last remaining row can't be removed, matching the backend's `min_length=1` requirement).
`ProductionService` (`frontend/src/app/core/services/production.service.ts`) is a thin HTTP
wrapper reusing the same `ReferenceService` (units, organization units) Weighbridge's dialogs
already depend on. The nav item (`Production`, gated on `production.view`) was added to
`shell.component.ts`, and the route to `app.routes.ts`, gated by `permissionGuard('production.view')`.

As with Weighbridge, there are no `.spec.ts` unit tests for these components — frontend coverage
for this module is zero; correctness is exercised through the backend's integration tests
(`tests/integration/test_production.py`) and manual end-to-end verification against the real
database (see [docs/phases/phase-3-completion.md](phases/phase-3-completion.md)).
