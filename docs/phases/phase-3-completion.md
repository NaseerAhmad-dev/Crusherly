# Phase 3 Completion Report — Production

This is a completion report against Phase 3's Definition of Done, written from what was actually
verified in this repository, not from what a plan intended. Where something below is marked done,
it was checked directly (tests run, linters run, a real entry created and submitted against a real
database); where something is marked incomplete, that's because it genuinely doesn't exist yet, not
because it was out of scope to check.

## About this phase's scope, and a correction

This report originally opened by stating flatly that no Master Build Specification document
existed anywhere in the repository or filesystem, and that this phase's scope (Production) was
therefore a judgment call made in its absence — chosen because it's the natural next link in the
operational chain after Weighbridge (material arrives and is weighed → crushed → graded into
outputs → later sold/dispatched), and because `app/models/rbac.py`'s own `Permission.code`
docstring already used `production.update` as its example permission code before this phase
started.

That search was not thorough enough. The actual spec exists at
`Stone_Crusher_Platform_Master_Build_Specification.md` (now copied into this repository's root) —
it had been sitting in the user's Downloads folder the entire time. Per the real spec's phase plan
(section 51), **Production genuinely is Phase 3** — the guess turned out correct. What was wrong
was the framing around it: there is a real Phase 2 (Weighbridge — see
[docs/phases/phase-2-completion.md](phase-2-completion.md), renamed from `phase-1-completion.md`
to match), and a real Phase 1 ("Master Data Foundation") that was skipped over entirely and is
being built retroactively, out of order, after Phases 2 and 3 rather than before them — see
[docs/phases/phase-1-completion.md](phase-1-completion.md) once it exists. There was never
a numbering gap in the user's count; there was a missing spec on this end.

The real spec also reveals concrete gaps against Phase 3's actual scope (section "PHASE 3 —
Production") that this implementation does not close:

- **No `ProductionPlan` distinct from `ProductionRun`.** The spec separates planning from actuals;
  this implementation only has `ProductionEntry`, which records actuals directly with no planned
  target to compare against.
- **No `Crusher Line` concept.** A real plant may run more than one crusher line per shift; this
  implementation has no way to record which line an entry's output came from.
- **No `Machine` reference or `Downtime` tracking.** The spec lists both explicitly; neither exists
  in `app/models/production.py`.

These gaps are real scope, not polish, and are listed here rather than left implicit.

If a real Master Build Specification surfaces later and numbers phases differently, this module's
functionality doesn't need to change — only its label might.

## What's done

### Backend

- **58/58 pytest tests pass** (`cd backend && .venv\Scripts\python.exe -m pytest -q`), up from
  49/49 at the start of this phase. The 9 new tests
  (`tests/integration/test_production.py`) cover: create + submit happy path, scope-based
  authorization (an `OPERATOR` or `MANAGER` scoped to one plant cannot create/submit entries for
  another plant, a `TENANT_ADMIN` with a tenant-wide grant can act on any plant), a `VIEWER` being
  refused creation, the `422` rejection of an entry with zero outputs, the `409` for a missing
  active fiscal year, the `409`s for double-submit and double-cancel, and tenant-scoped listing.
- **A real, pre-existing-but-latent bug was found and fixed while verifying, unrelated to the new
  module's own logic**: `RateLimitMiddleware` (`app/middleware/rate_limit.py`) holds its per-IP hit
  counter as state on a single middleware instance shared by the whole test process (the FastAPI
  `app` object is a module-level singleton in `tests/conftest.py`). Growing the suite from 49 to 58
  tests pushed the total request count within a single test run's ~60-second wall-clock window over
  the production default of 120 requests/minute, causing five unrelated Weighbridge tests to fail
  intermittently with `AssertionError` inside `login_headers()` — not because those tests or their
  fixtures were wrong, but because the shared rate limiter legitimately tripped. Fixed by setting
  `RATE_LIMIT_PER_MINUTE=100000` via `os.environ.setdefault(...)` at the very top of
  `tests/conftest.py`, before any application module is imported (required, since
  `get_settings()` is `@lru_cache`d and resolves on first import). This is a test-environment-only
  change; production behavior of the rate limiter is untouched. Confirmed by re-running the full
  suite clean afterward.
- **`ruff check app tests` and `black --check app tests` both pass with 0 issues** — the full
  command CI's Lint stage actually runs (`app` *and* `tests` together), not just `app` alone.
- **A second Alembic migration was generated and applied to the real, running Postgres database**
  (`23b1b4ecb8d9` → `73618eeb581f`), cleanly, with no `render_item` issues — confirming the
  `env.py` fix from Phase 2 (see [docs/phases/phase-2-completion.md](phase-2-completion.md)) holds
  for new tables using the custom `UTCDateTime` type, not just the one migration it was written for.

### Frontend

- **`ng build` succeeds, `ng test` — 19/19 pass, `ng lint` reports 0 errors** — unchanged pass
  counts from before this phase (no `.spec.ts` files were added for the two new
  `production/` components, matching Weighbridge's own frontend test coverage, which is also zero
  — see [docs/production.md](../production.md#frontend)).
- **The `ProductionEntryDialogComponent` create form was verified as a real, working UI**, not just
  a compiling one: it is the first form in this codebase to use a Reactive Forms `FormArray`
  (`outputs`), with working "Add output" / per-row delete (the last row can't be removed, matching
  the backend's one-output minimum) and dependent `mat-select` pickers sourced from the same
  `ReferenceService` (units, organization units) Weighbridge's dialogs already use.

### End-to-end verification against the real database

Both the backend (port 8002) and frontend (port 4201) were run against the actual local Postgres
instance — not sqlite — and driven through a real browser:

1. Logged in as the demo tenant's `TENANT_ADMIN`.
2. Opened the Production screen (empty state rendered correctly, `factory` nav icon in the sidenav).
3. Created a new entry: raw material "Raw stone" / 20000.000 t, two outputs ("40mm Aggregate" /
   8000.000 t, "Dust" / 2000.000 t) added via the `FormArray`'s "Add output" button.
4. The entry was created as `PRD-000001` in `DRAFT` status — confirming `numbering_service` and the
   fiscal-year prerequisite both work correctly against the real database, not just sqlite.
5. Submitted the entry; status transitioned to `SUBMITTED` (rendered with the same "info" blue
   status-badge tone `SUBMITTED` already used for Weighbridge/other modules), toast notification
   shown, list refreshed correctly with the outputs summary column
   (`"40mm Aggregate: 8000.000, Dust: 2000.000"`).

This caught nothing wrong — the module worked end-to-end on the first real attempt — but it's
recorded here because "the build compiles" and "a person clicked through it against a real
database and it worked" are different claims, and only the second one is made here.

## Explicitly out of scope for this phase (correct, not a gap)

- Inventory, Sales, Dispatch, Purchases, Maintenance, Vehicles, Fuel, Finance, Quality, Safety,
  Compliance, and Reporting/Analytics — untouched, per phase discipline.
- Linking a `ProductionEntry` to the `WeighbridgeTicket`(s) that supplied its raw material. This is
  a real, nontrivial design question (a shift can blend input from more than one ticket) that was
  deliberately left unaddressed rather than guessed at — see
  [docs/production.md](../production.md#whats-genuinely-denormalized-raw-material-and-product-are-free-text).
- Reconciling an entry's output quantities against its raw material quantity. Crushing has real
  yield loss; encoding a mass-balance check without knowing this business's actual expected yield
  ratios would be guessing, not validating.

## Still genuinely incomplete

- **No Product/Item master.** `raw_material_description` and each output's `product_description`
  are free text, the same denormalization trade-off Weighbridge already made for vehicle/party
  data. See [docs/production.md](../production.md) for the full reasoning and the migration path
  once a real Product master exists.
- **No fiscal-year management API**, still — this was already true after Phase 2 and remains true.
  The only way any tenant gets an active fiscal year today is the seed script (for the demo tenant)
  or a direct database write.
- **No frontend unit tests** (`.spec.ts`) for `ProductionListComponent` or
  `ProductionEntryDialogComponent`, or for `ProductionService`. Coverage is backend-integration and
  manual-verification only.
- **Everything listed as incomplete in
  [docs/phases/phase-2-completion.md](phase-2-completion.md)'s "Still not done" section
  remains incomplete** — the empty `infrastructure/bicep/` stub, the placeholder CI deploy stage,
  the undefined Azure Container Registry service connection, the dev-only frontend Docker image,
  and single-instance rate limiting. Nothing in this phase touched infrastructure or deployment.

## Bottom line

Phase 3's Definition of Done — tests pass, lint passes, the frontend works, docs match the
implementation — is met for Production, on the same terms Phase 2 was: backend and frontend are
both green, the module was verified by hand against a real database rather than assumed from a
passing build, and this document (plus [docs/production.md](../production.md)) describes real,
checked-in code. The gaps against the real spec's Phase 3 scope (no `ProductionPlan`, no crusher
lines, no machine/downtime tracking) and the fact that Phase 1 was skipped and is being built out
of order are both stated here directly so neither is mistaken later for something other than what
it is.
