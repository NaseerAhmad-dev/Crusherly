# Architecture

This document describes the system as it actually exists at the end of **Phase 0 — Platform
Foundation**. Nothing below is aspirational; where a piece of the design is a placeholder for a
later phase, it is called out explicitly in [What's NOT here yet](#whats-not-here-yet).

For the phase plan and what Phase 0 is scoped to deliver, see the root [README.md](../README.md).

## Shape of the system: modular monolith

The backend is one FastAPI application, one deployable process, one database — not a set of
services. Internally it is cut into modules (`auth`, `users`, `tenants`, `roles`, `permissions`,
`audit`, `settings`, `attachments`, `notifications`, `dashboard`, `weighbridge`, `production` today;
`inventory`, `sales`, `dispatch`, `purchases`, `maintenance`, `vehicles`, `fuel`,
`finance`, `quality`, `safety`, `compliance`, `reporting` in later phases) that only talk to each
other through well-defined layers, never by reaching into another module's database rows or
internal functions directly.

The reason for this shape, rather than starting with microservices:

- **A stone-crushing operator's write volume does not justify network-hop overhead.** The
  business modules share the same tenant/org/RBAC/audit foundation and mostly read and write the
  same handful of tables in a single request (e.g. recording a weighbridge ticket touches
  inventory, a document sequence, and an audit event) — that is one transaction, not a saga across
  services.
- **One deployable means one thing to build, test, and roll back.** There is no distributed
  tracing problem, no service-to-service auth problem, and no version-skew problem between
  modules, because they all ship together.
- **The internal boundaries are real, even though the process boundary isn't.** Every module is
  layered `api -> service -> repository -> model` (see [Request lifecycle](#request-lifecycle-through-the-application)
  below) and modules do not import each other's repositories. If a specific module ever needs to
  become its own service (e.g. Reporting/Analytics under heavy read load), the seam to extract it
  is already there: its service layer is the boundary, and the event bus (see
  [Event bus](#event-bus-an-in-process-extension-point)) is the mechanism other modules use to
  react to what it does, rather than calling into it synchronously.

This is a deliberate, named trade-off, not an accident of not having gotten around to
microservices yet — extract a module only when a concrete scaling or team-ownership need forces
it, not preemptively.

## Layering: API -> Service -> Repository -> Model

Every request follows the same shape, stated directly in the docstring of `app/main.py`:

```text
API -> Authentication -> Authorization -> Service -> Repository -> Database
```

- **`app/api/v1/*.py` (routers).** Parse and validate the request (via Pydantic schemas in
  `app/schemas/`), resolve the caller's identity/permissions through a FastAPI dependency, call
  exactly one service function, and shape the response. Routers contain no business logic and no
  direct SQLAlchemy queries — compare `app/api/v1/auth.py` and `app/api/v1/users.py`, both of which
  do nothing but wire a schema to a service call.
- **`app/services/*.py`.** Business logic and transaction boundaries live here (`session.commit()`
  is called from services, not routers or repositories). Services enforce invariants (e.g.
  `auth_service.login` counts failed attempts and locks the account, `authorization_service`
  resolves scope-based authorization), raise the domain exceptions in `app/core/exceptions.py`,
  and publish domain events after a commit.
- **`app/repositories/*.py`.** Thin, model-specific query functions (`get_by_email`,
  `get_by_code`, `add`, ...). No business logic — just how to find or persist a row. Services
  depend on repositories; repositories do not depend on services.
- **`app/models/*.py`.** SQLAlchemy 2.0 ORM models, mapped_column-typed, importable from a single
  `app/models/__init__.py` so `Base.metadata` is always fully populated for Alembic and so
  cross-module `relationship()` string references resolve.

Two supporting layers cut across all of them:

- **`app/security/`** — `SecurityContext` (who is calling, which tenant, which roles/permissions,
  at which scope), the `require_authenticated_user` / `require_permission` FastAPI dependencies,
  and `authorization_service.authorize()` for scope-specific checks. Built fresh from the database
  on every request (see `app/security/security_context.py`), deliberately not cached in the JWT,
  so a permission or role change takes effect on the very next request instead of waiting for a
  token to expire.
- **`app/schemas/`** — Pydantic request/response models. These are the only shapes that cross the
  HTTP boundary; ORM models are never returned directly.

## Request lifecycle through the application

`app/main.py`'s `create_app()` assembles the FastAPI app and registers middleware. Middleware
order matters in Starlette: the last one added is the **outermost** — it runs first on the way in
and last on the way out. In registration order:

1. `CORSMiddleware` (outermost) — origin allow-list from `settings.cors_origins_list`, credentials
   allowed, `X-Request-ID` exposed to browser JS.
2. `SecurityHeadersMiddleware` — sets `X-Content-Type-Options`, `X-Frame-Options`,
   `Referrer-Policy`, `Permissions-Policy` on every response, and `Strict-Transport-Security` only
   when `settings.is_production` is true (HSTS on a local HTTP dev server would be actively
   harmful).
3. `RateLimitMiddleware` — see below.
4. `RequestContextMiddleware` (innermost of the four) — see below.

So the actual runtime order for an inbound request is: CORS check -> security headers wrapper
established -> rate limit check -> request-ID assigned -> route handler -> (unwind back through
the same four, response headers added on the way out).

After middleware, `register_exception_handlers(app)` installs the handlers in
`app/core/error_handlers.py`, and `api_router` (from `app/api/v1/router.py`) is mounted at
`settings.api_v1_prefix` (`/api/v1`).

**`RequestContextMiddleware`** (`app/middleware/request_context.py`) gives every request a
correlation ID: it reads the inbound `X-Request-ID` header if the caller supplied one, otherwise
generates a UUID. The ID is stored on `request.state.request_id` (used by the error handlers and
audit service) and in a `ContextVar` (`request_id_var`) so `app/core/logging_config.py` can stamp
every log line with it without threading a `Request` object through every function signature. It
is echoed back to the client in the `X-Request-ID` response header.

**`RateLimitMiddleware`** (`app/middleware/rate_limit.py`) is an in-memory, fixed-window limiter
keyed by client IP, explicitly documented as a Phase 0 starting point rather than a distributed
rate limiter: state lives in process memory, so it resets on restart and does not share state
across multiple backend replicas. It skips `/health` and `/ready` so orchestrator liveness/
readiness probes are never rate-limited, and returns the platform's standard error envelope
(`RATE_LIMITED`, 429) when a client exceeds `settings.rate_limit_per_minute` (120/minute by
default) within a 60-second window. The module's own docstring calls out the upgrade path: swap in
a Redis-backed limiter later without changing call sites.

**`SecurityHeadersMiddleware`** (`app/middleware/security_headers.py`) is the baseline
hardening pass required by the Master Build Specification — content-type sniffing prevention,
clickjacking prevention, referrer trimming, and a locked-down permissions policy, applied
unconditionally, plus HSTS in production only.

**Errors** all come out through the same envelope, defined once in
`app/core/error_handlers.py`:

```json
{"success": false, "error": {"code": "FORBIDDEN", "message": "...", "request_id": "..."}}
```

Domain exceptions (`app/core/exceptions.py`: `UnauthorizedError`, `ForbiddenError`,
`NotFoundError`, `ConflictError`, `ValidationAppError`, all subclasses of `AppError`) map straight
to this envelope with their own status code. Starlette `HTTPException`s and FastAPI
`RequestValidationError`s are normalized into the same shape. Anything else (an actual bug) is
caught by a catch-all handler, logged with a full traceback server-side, and returned to the
client as a generic `INTERNAL_ERROR` with no stack trace — `settings.debug` controls whether the
real exception message leaks into the response, which should be false outside local development.

## Database layer

`app/core/database.py` builds a single async SQLAlchemy engine and `async_sessionmaker` from
`settings.database_url`. It branches only on dialect for connection pooling: SQLite (used for
tests) gets `check_same_thread=False` and no pool-size tuning; PostgreSQL (used everywhere else)
gets `pool_size`/`max_overflow` from settings plus `pool_pre_ping=True` so a dropped connection is
detected and replaced rather than surfacing as a query failure.

`Base`, the declarative base every model inherits from, sets one mapper-wide option:

```python
class Base(DeclarativeBase):
    __mapper_args__ = {"eager_defaults": True}
```

`eager_defaults` makes INSERT/UPDATE fetch server-computed columns (notably the
`onupdate=func.now()` timestamp on every `TimestampMixin` model) via `RETURNING` during the flush
itself, instead of leaving the attribute expired on the Python object. Without it, reading that
column right after a flush/commit — e.g. serializing the ORM object straight into a response
schema — triggers SQLAlchemy's implicit lazy-load, which raises `MissingGreenlet` under
`asyncio` because the lazy-load happens outside the session's IO-bridging context. This was a real
bug hit and fixed in this codebase, not a hypothetical.

`get_db()` is the FastAPI dependency every route/service ultimately runs under: it yields one
session per request and rolls back on any exception rather than leaving a half-committed
transaction open.

See [development.md](development.md) for how the same model definitions run against both
PostgreSQL (production) and SQLite (tests), and the `UTCDateTime` type that makes timestamp
comparisons behave identically on both.

## Event bus: an in-process extension point

`app/events/bus.py` implements a deliberately minimal in-process publish/subscribe bus — not
Kafka, not RabbitMQ, not even Redis pub/sub. `EventBus.publish()` just iterates the handlers
registered for that event's type and awaits each one in turn, synchronously, in the same process.
The module-level `event_bus` singleton is the one instance the whole app shares.

Two design decisions are worth calling out because they will matter to whoever adds the first real
subscriber:

- **Handlers run after the publishing transaction commits**, by convention (services call
  `session.commit()` first, then `publish()`) — a handler that reacts to `UserCreated` should
  never be able to observe a user row that the surrounding transaction later rolled back.
- **This is a seam, not a finished feature.** `app/events/definitions.py` currently defines
  `UserCreated`, `TenantCreated`, `RoleChanged`, `DocumentUploaded`, and `ApprovalCompleted` as
  frozen dataclasses, following the pattern future business modules should extend (its own
  docstring gives the example: `ProductionCompleted`, `StockReceived`, `InvoiceCreated`,
  `PaymentReceived`, `MaintenanceCompleted`). If a genuine need for durable or cross-process
  events shows up in a later phase, `publish`/`subscribe`'s signatures are the boundary a real
  broker gets swapped in behind — call sites in services do not change.

## Background jobs: an abstraction, not a queue

`app/jobs/base.py` defines a `@job("name")` decorator that registers an async function in an
in-memory registry, plus `run_job(name, *args, **kwargs)` to invoke one by name with logging around
success/failure. That is the entire Phase 0 deliverable for this area — there is intentionally no
task queue wired up (no Celery, no APScheduler, no cron) because there is no real recurring job
yet. The module's docstring lists what Phase 0 explicitly does not implement: document expiry
reminders, notification fan-out, report generation, scheduled maintenance generation, daily KPI
calculations, data synchronization — all deferred as FUTURE jobs in the spec.

The intended path when the first real job is needed: register it with `@job(...)`, then either
drive it with FastAPI's `BackgroundTasks` for fire-and-forget work, or wire APScheduler/Celery
behind the same `Job` interface for anything that needs to be recurring or durable — call sites do
not change either way.

## Security model (summary)

Full detail belongs in `docs/authentication.md` / `docs/authorization.md` (see the README's
documentation list); the pieces relevant to the architecture:

- **Authentication** (`app/services/auth_service.py`): email+password login (email is unique
  platform-wide, so there is no tenant selector at login), short-lived stateless JWT access
  tokens, and refresh tokens that are JWTs *backed by* a `RefreshSession` database row keyed by
  `jti` — this is what makes "logout" and "revoke all sessions" possible for a token type that
  would otherwise be stateless. Refresh tokens rotate on every use (old `jti` revoked, new one
  issued) to bound the blast radius of a stolen refresh token.
- **RBAC** (`app/models/rbac.py`, `SecurityContext.has_permission`): "can this user do X at all."
- **Scope-based authorization** (`app/services/authorization_service.py`): "does this user's grant
  for permission X cover *this specific resource's* organization unit" — walks the organization
  hierarchy's ancestors so a grant at a parent node covers its descendants. PLATFORM- and
  TENANT-level grants short-circuit to "yes" without needing the resource's org unit at all.
- **Tenant isolation**: enforced at the repository/service layer (a cross-tenant resource is never
  fetched in the first place, not filtered out after the fact) plus the mandatory `tenant_id`
  column that `TenantScopedMixin` adds to every tenant-owned table (`app/models/base.py`).
- **`SecurityContext` is rebuilt from the database on every request** (never trusted from JWT
  claims beyond the user ID), so role/permission changes apply immediately rather than waiting for
  token expiry.

## How the frontend fits in

`frontend/` is a separate Angular application (Angular 22, Angular Material 3, strict TypeScript)
served independently in development (`ng serve` on port 4200) and built as static assets for
deployment. It is not server-rendered by the backend and the backend does not template any HTML —
the two communicate purely over the `/api/v1` JSON API, using the same request/response envelope
described above.

The frontend's `src/app/core/` module mirrors the backend's cross-cutting layers on the client
side: an `auth/` service holding the token pair and current user, an `http/` `auth.interceptor`
that attaches the bearer token and an `error.interceptor` that unwraps the standard error envelope,
and `guards/` (`auth.guard`, `permission.guard`) that gate routes the same way
`require_authenticated_user`/`require_permission` gate API routes — so the permission model is
enforced on both sides, not just trusted from the UI. Feature modules (`auth`, `users`, `roles`,
`tenants`, `settings`, `audit`, `dashboard`, ...) correspond one-to-one with the backend's Phase 0
API routers; there is no frontend feature yet for a business module that does not exist on the
backend.

In Docker Compose (`docker-compose.yml`), `backend` and `frontend` are separate containers behind
the same origin only via CORS (`CORS_ALLOWED_ORIGINS`), not a shared reverse proxy — appropriate
for local development; production topology (e.g. a shared Azure Front Door/App Gateway origin) is
part of the infrastructure work still to be done (see below).

## What's NOT here yet

Phase 0 is the platform foundation; Phase 2 (Weighbridge) and Phase 3 (Production) added business
modules on top of it, ahead of Phase 1 ("Master Data Foundation"), which was skipped and is being
built out of order — see [docs/phases/phase-3-completion.md](phases/phase-3-completion.md) for why.
As of this writing:

- **Weighbridge and Production are the two shipped business modules.** Weighbridge exists in
  `app/api/v1/weighbridge.py`, `app/services/weighbridge_service.py`, and
  `app/models/weighbridge.py`; Production in `app/api/v1/production.py`,
  `app/services/production_service.py`, and `app/models/production.py`. Both are built entirely on
  the Phase 0 foundation described in this document (numbering, audit, scope-based authorization).
  See [docs/weighbridge.md](weighbridge.md) and [docs/production.md](production.md) for the full
  detail on each.
- **No other business modules.** Inventory, Sales, Dispatch, Purchases, Maintenance, Vehicles,
  Fuel, Finance, Quality, Safety, Compliance, and Reporting/Analytics do not exist in
  `app/api/v1/`, `app/services/`, or `app/models/` — only their eventual event types are sketched
  as examples in `app/events/definitions.py`'s docstring. Per the README's "Phase Discipline"
  section, these are not to be started until the current phase's Definition of Done is met and the
  next phase is reached.
- **No production message broker or task queue.** The event bus is in-process and synchronous;
  the job abstraction has a registry and a decorator but nothing scheduling or queuing work today.
- **Bicep infrastructure is an empty stub.** `infrastructure/bicep/` exists as a directory with no
  templates in it yet. There is no Azure resource definition (App Service/Container Apps,
  PostgreSQL, Key Vault, Application Insights, Front Door) checked in.
- **No CI-verified deployment.** `azure-pipelines.yml` defines Install -> Lint -> Test ->
  SecurityChecks -> Build -> DockerBuildPush -> DeployDevelopment stages, but the deploy stage is a
  literal placeholder (`echo "Deploy ... (placeholder — see infrastructure/README.md)"`), gated on
  infrastructure that does not exist yet. The Docker build/push stages depend on an Azure Container
  Registry service connection that has not been wired up either. Nothing in this pipeline has
  actually deployed the application anywhere.
- **Rate limiting is single-instance.** It will silently under- or over-limit if the backend is
  ever scaled to more than one replica, since state is per-process memory (documented directly in
  `app/middleware/rate_limit.py`).
- **No email/SMS delivery.** `auth_service.request_password_reset` generates and stores a reset
  token but only logs it at debug level outside production; there is no notification channel wired
  up to actually send it (see `app/services/notification_service.py`'s extension point).
