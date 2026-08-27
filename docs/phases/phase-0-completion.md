# Phase 0 Completion Report — Platform Foundation

This is a completion report against Phase 0's Definition of Done, written from what was actually
verified in this repository, not from what the plan intended. Where something below is marked
done, it was checked directly (tests run, linters run, screens loaded in a browser); where
something is marked incomplete, that's because it genuinely doesn't exist yet, not because it was
out of scope to check.

## What's done

### Backend

- **39/39 pytest tests pass** (`cd backend && pytest -v`). This is up from 37/39 at the start of
  this session — two real bugs were found and fixed along the way, not pre-existing green:
  1. A `MissingGreenlet` crash in the tenant-suspend endpoint, caused by a server-side
     `onupdate` timestamp column not being eagerly fetched after an UPDATE. Fixed by setting
     `Base.__mapper_args__ = {"eager_defaults": True}` in `app/core/database.py`.
  2. A naive-vs-aware `datetime` comparison crash in refresh-token expiry checking, caused by
     SQLite silently dropping tzinfo on `DateTime(timezone=True)` columns. Fixed by introducing a
     `UTCDateTime` `TypeDecorator` in `app/models/base.py`, applied to every timestamp column.

     Full technical detail on both bugs, and the design decision they informed, is in
     [docs/testing.md](../testing.md), [docs/database.md](../database.md), and
     [ADR-0002](../adr/0002-dialect-portable-models.md).
- **`ruff check app` reports 0 errors** (was 83 at session start). Fixed via a mix of `ruff`'s
  auto-fix, `StrEnum`/PEP-695-generics modernization, and manual line-wrapping for the remaining
  `E501`s.
- **`black --check app` passes.**

### Frontend

- **`ng build` succeeds.**
- **`ng test` — 19/19 tests pass** (Vitest via Angular's `@angular/build:unit-test` builder — see
  [docs/testing.md](../testing.md)).
- **`ng lint` reports 0 errors.**
- **A custom industrial Material 3 theme was applied consistently** across the login screen, the
  shell/sidenav, the dashboard, and all list screens (tenants, users, roles, audit, settings) —
  graphite/slate primary (`#37474F`), amber/safety-orange tertiary (`#E8871E`), Inter typography.
- **The theme was verified end to end, not just built.** This means actually logging in against a
  throwaway seeded SQLite-backed instance and screenshotting every screen — not just confirming
  the build compiles. That verification pass caught and fixed two real regressions that a build-only
  check would have missed:
  - An inconsistent `<h1>` size on the Settings and Audit Log pages, which weren't wrapped in the
    shared `.page-header` class the other screens use.
  - A broken, no-longer-centered card layout on the forgot-password/reset-password screens, caused
    by those screens sharing login's stylesheet after the login page was redesigned to a
    split-panel layout.

### Documentation

Every document the root [README.md](../../README.md)'s "Documentation" section names now exists
in `docs/`:

`architecture.md`, `database.md`, `authentication.md`, `authorization.md`, `multi-tenancy.md`,
`organization.md`, `audit.md`, `workflow.md`, `documents.md`, `notifications.md`, `security.md`,
`development.md`, `api-conventions.md`, `testing.md`, `azure.md`, plus three ADRs under
`docs/adr/` (`0001-modular-monolith.md`, `0002-dialect-portable-models.md`,
`0003-global-email-uniqueness.md`).

This list was confirmed by listing `docs/` directly, not from memory or from the plan — at the
start of this work, `docs/` contained nothing but two empty subdirectories (`adr/`, `phases/`).

## Explicitly out of scope for Phase 0 (correct, not a gap)

Per the README's "Phase Discipline" section, no business modules exist yet, and that is by
design, not an oversight:

- Weighbridge, Production, Inventory, Sales, Dispatch, Purchases, Maintenance, Vehicles, Fuel,
  Finance, Quality, Safety, Compliance, and Reporting/Analytics have no routers, services, models,
  or frontend features. `app/events/definitions.py`'s docstring sketches example future event
  types for some of these (`ProductionCompleted`, `StockReceived`, `InvoiceCreated`, ...), but
  none of the modules themselves are started.
- No production message broker or task queue: the event bus (`app/events/bus.py`) is in-process
  and synchronous, and the job abstraction (`app/jobs/base.py`) has a registry and decorator but
  nothing scheduling or queuing real work — there is no real recurring job yet that would need
  one.
- No email/SMS delivery: password reset generates and stores a token but only logs it at debug
  level outside production.

None of this blocks Phase 0's Definition of Done — these are correctly deferred to later phases.

## Still genuinely incomplete

- **`infrastructure/bicep/` is empty.** Confirmed by listing the directory directly: it contains
  no files at all. There is no Bicep (or any other IaC) for provisioning PostgreSQL, Container
  Apps/App Service, Azure Container Registry, Key Vault, Application Insights, a Storage Account,
  or networking. See [docs/azure.md](../azure.md) for the full "Not yet built" breakdown.
- **`infrastructure/README.md` does not exist**, despite being referenced by name in
  `azure-pipelines.yml`'s `DeployDevelopment` placeholder comment.
- **No real deployment stage.** `DeployDevelopment` in `azure-pipelines.yml` is a single `echo`
  step; `Testing`, `Staging`, and `Production` stages exist only as a trailing comment describing
  the intended promotion path, not as pipeline stages. Nothing in this pipeline has ever actually
  deployed the application anywhere.
- **The Azure Container Registry service connection is undefined in-repo** — `DockerBuildPush`
  references `$(azureContainerRegistryServiceConnection)`, which has to be created in Azure DevOps
  project settings before that stage could succeed.
- **Key Vault integration is a settings field, not working code.** `azure_key_vault_url` exists on
  `Settings` but nothing reads it — the actual mechanism (Key Vault-backed pipeline variable
  groups injecting environment variables) isn't defined anywhere in this repo either.
- **No production frontend Docker image.** `frontend/Dockerfile` only runs the Angular dev server;
  the Static Web Apps/Container App + nginx target mentioned in its own comment doesn't exist yet.
- **Rate limiting is single-instance only** (in-memory, per-process — documented directly in
  `app/middleware/rate_limit.py`), which is fine for Phase 0 but will under- or over-limit the
  moment the backend runs as more than one replica.

## Bottom line

Phase 0's Definition of Done — tests pass, lint passes, the frontend works, and docs match the
implementation — is met for everything inside the platform foundation's actual scope: backend and
frontend are both green, the visual/functional state of the UI was verified by hand rather than
assumed from a passing build, and every doc the README promises now exists and describes real,
checked-in code. What remains (Bicep infrastructure, a working deployment pipeline, a production
frontend image) is infrastructure and deployment work that was never claimed to be done, and it's
listed above precisely so it isn't mistaken for done later.
