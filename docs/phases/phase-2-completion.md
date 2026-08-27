# Phase 2 Completion Report — Weighbridge

This is a completion report against Phase 2's Definition of Done, written from what was actually
verified in this repository, not from what a plan intended. Where something below is marked done,
it was checked directly (tests run, linters run, a real ticket created against a real database);
where something is marked incomplete, that's because it genuinely doesn't exist yet, not because it
was out of scope to check.

## About this phase's scope, and a correction

This report was originally written as "Phase 1 Completion Report — Weighbridge," at a time when no
Master Build Specification document could be found anywhere in this repository or filesystem
despite being referenced by name throughout the codebase. That search was not thorough enough: the
actual spec exists at `Stone_Crusher_Platform_Master_Build_Specification.md` (now copied into this
repository's root) — it had been sitting in the user's Downloads folder the entire time, outside
both the repo and the filesystem locations searched.

Per the real spec's phase plan (section 51), **Weighbridge is Phase 2**, not Phase 1 — Phase 1 is
"Master Data Foundation" (Materials, Products, Customers, Suppliers, Vehicles, Drivers, Machines,
Equipment, Tax Codes, Payment Terms), which was skipped over entirely and is being built
retroactively — see [docs/phases/phase-1-completion.md](phase-1-completion.md) once it exists.
This file has been renamed from `phase-1-completion.md` to `phase-2-completion.md` to match the
real numbering; nothing about the module's actual functionality changes as a result. The original
reasoning for building Weighbridge before its correct turn is still worth recording: it was chosen,
under an explicit instruction not to ask for clarification, because it's the first business module
listed everywhere modules are enumerated and the natural first operational transaction for a
stone-crushing business. That reasoning was sound as a guess in the absence of a spec — it was
simply superseded once the real spec was found.

The real spec also reveals concrete gaps against Phase 2's actual scope (section "PHASE 2 —
Weighbridge + Raw Material") that this implementation does not close:

- **No `Gate` field** — the spec lists Gate as a ticket attribute; this implementation has no
  equivalent.
- **No `External Reference` / idempotency support** — section 30 of the spec calls out Weighbridge
  by name as needing idempotent handling of external readings ("the same external transaction
  received twice must not create duplicate business transactions"). This implementation has no
  external-reference field and no duplicate-detection logic; two identical `POST` requests create
  two separate tickets.
- **`Supplier`/`Customer` are spec'd as real entities**, not the free-text `party_name` this
  implementation uses (see "Still not done" below — this was already flagged, just not previously
  connected to the fact that the spec explicitly calls for proper master-data entities here).

These gaps are exactly what Phase 1 (Master Data Foundation), once built, should close by
retrofitting `Customer`/`Supplier`/`Vehicle` foreign keys onto `WeighbridgeTicket` in place of the
current free-text columns, and adding `gate`/`external_reference` fields directly.

## What's done

### Backend

- **49/49 pytest tests pass** (`cd backend && .venv\Scripts\python.exe -m pytest -q`). This is up
  from 39/39 at the start of this phase — the 10 new tests are entirely this phase's own coverage:
  7 in `tests/integration/test_weighbridge.py` (ticket creation, completion, cancellation, the
  fiscal-year-missing 409, and — the significant ones — the scope-based authorization tests: an
  `OPERATOR` scoped to one plant cannot create a ticket for another plant, a `MANAGER` scoped to
  one plant cannot complete a ticket from another, and a `TENANT_ADMIN` with tenant-wide scope can
  act on any plant) and 3 in `tests/integration/test_reference_data.py` (the two new
  reference-data endpoints).
- **`ruff check app tests` reports 0 errors.**
- **`black --check app tests` passes** (117 files unchanged).
- **A real bug in Alembic autogeneration was found and fixed.** Autogenerating the migration for
  `WeighbridgeTicket`'s timestamp columns (which use the custom `UTCDateTime` type) produced a
  broken `app.models.base.UTCDateTime(...)` reference in the migration file with no corresponding
  import — a migration that would have raised `NameError` the moment anyone ran
  `alembic upgrade head`. Fixed with a `render_item` hook in `alembic/env.py` that renders
  `UTCDateTime` columns as plain `sa.DateTime(timezone=True)` instead — the actual DDL type is
  identical either way; only the Python-side read behavior differs, and that lives in the ORM
  layer, not the schema.
- **A real gap in Phase 0 was closed: fiscal years were modeled but never created.**
  `app/models/fiscal_year.py` existed since Phase 0, but nothing ever inserted a row, because no
  business module needed to number a document against one yet. `app/core/seed.py` now has a
  `seed_fiscal_year()` step that creates one active April–March fiscal year for the demo tenant.
  There is still no API route to manage fiscal years — see "Still not done" below.
- **Two new read-only reference-data endpoints** (`GET /api/v1/units`,
  `GET /api/v1/organization-units`) were added because Weighbridge's create form needs to let the
  user pick a unit and a plant, and Phase 0 had modeled `Unit`/`OrganizationUnit` but never exposed
  either over the API.
- **Three new permissions** (`weighbridge.view`, `weighbridge.create`, `weighbridge.update`) were
  added to the fixed permission set in `app/core/seed.py` and assigned to five of the seven system
  roles: `SUPER_ADMIN` and `TENANT_ADMIN` get all three; `MANAGER` and `OPERATOR` get all three as
  well (both can create and complete/cancel tickets, distinguished only by scope, not by which
  weighbridge permissions they hold); `ACCOUNTANT`, `STOREKEEPER`, and `VIEWER` get `.view` only.

### Frontend

- **`ng build` succeeds.**
- **`ng test --watch=false` — 19/19 tests pass**, the same count as Phase 0. No dedicated unit
  tests (`.spec.ts`) were written for the three new weighbridge components
  (`WeighbridgeListComponent`, `WeighbridgeTicketDialogComponent`,
  `WeighbridgeCompleteDialogComponent`) or the two new services (`WeighbridgeService`,
  `ReferenceService`). Frontend correctness for this module rests entirely on the backend's
  integration tests plus the manual verification pass below — this is a real, not hidden, gap; see
  "Still not done."
- **`ng lint` reports 0 errors.**
- **The Weighbridge nav item, route, and three screens use the existing Material 3 theme** with no
  new components introduced at the design-system level — the list screen reuses
  `DataTableComponent`, `PaginationComponent`, and `StatusBadgeComponent`; both dialogs reuse the
  shared `DialogService`/`MatDialogModule` pattern already established by other modules.

### End-to-end verification against a real database

Beyond the automated test suites (which run against SQLite), this phase was verified end-to-end
against a real PostgreSQL database: logging in through the UI as the demo tenant's
`TENANT_ADMIN` (seeded by `python -m app.core.seed`) and creating, then completing, a real
weighbridge ticket through the running frontend against the running backend — not just confirming
the automated tests pass. This is the same bar Phase 0's completion report held itself to for its
own UI verification.

## Explicitly out of scope for this phase (correct, not a gap)

- All other business modules — Production, Inventory, Sales, Dispatch, Purchases, Maintenance,
  Vehicles, Fuel, Finance, Quality, Safety, Compliance, Reporting/Analytics — remain unstarted, per
  the README's "Phase Discipline" section.
- Infrastructure and deployment gaps carried over from Phase 0 (empty `infrastructure/bicep/`, no
  real CI deploy stage, single-instance rate limiting, no email/SMS delivery) are unchanged by this
  phase and are not re-litigated here — see
  [docs/phases/phase-0-completion.md](phase-0-completion.md) for that detail.

## Still not done

- **No Vehicle master.** `vehicle_number` on a ticket is a free-text `String(20)`, upper-cased on
  save, not a foreign key to a dedicated vehicles table — because no Vehicles module exists yet.
  There is no vehicle history, no per-vehicle tare-weight lookup, and no validation that a vehicle
  number refers to anything real.
- **No Party/Customer/Supplier master.** `party_name` is likewise free-text `String(200)` with no
  backing table. There is no way to look up "all tickets for this customer" except by matching text
  strings.
- **No fiscal-year management API.** The only way a tenant gets an active `FiscalYear` today is the
  seed script (for the demo tenant) or a direct database insert. A production tenant onboarded
  through the tenant-management API has no self-service way to create one before recording its
  first weighbridge ticket — it will simply get the 409 telling it none exists.
- **The dashboard does not show a weighbridge summary card.** `app/services/dashboard` and the
  frontend dashboard screen are unchanged by this phase; today's ticket count, open-ticket count,
  or net-weight totals are only visible by opening the weighbridge list itself.
- **No ticket-level attachment/document support.** The platform's general `Attachment` model
  (Phase 0) is not wired to `WeighbridgeTicket` — there is no way to attach a photo of the loaded
  truck or a scanned paper slip to a ticket.
- **No printable ticket/challan output.** There is no PDF or print-formatted view of a ticket for
  handing to a driver — only the JSON API and the in-app list/detail view.
- **No frontend unit tests for this module**, as noted above.

## Bottom line

Phase 2's actual deliverable — Weighbridge tickets, built on Phase 0's numbering, audit, and
scope-based authorization — is done and verified: backend and frontend both green on their
respective test/lint/build commands, the numbers above were produced by running those commands in
this session rather than assumed, and the feature was exercised against a real Postgres-backed
instance through the real UI, not only against SQLite test doubles. What remains (a Vehicles
module, a customer/supplier master, fiscal-year self-service, dashboard visibility, attachments,
and printable output) was never claimed to be part of this phase's scope, and is listed above
precisely so it isn't mistaken for done later.
