# Testing

This document describes how the test suites in `backend/tests/` and
`frontend/src/app/**/*.spec.ts` are structured, why they're structured that way, and the commands
to run them. It complements [database.md](database.md) (the full `UTCDateTime`/`eager_defaults`
story) and [development.md](development.md).

## Backend

### Commands

```bash
cd backend
pytest -v                                              # full suite, verbose
pytest tests/unit                                      # unit tests only
pytest tests/integration                               # integration tests only
pytest tests/unit/test_authorization_service.py -v     # one file
```

CI (`azure-pipelines.yml`, `Test` stage) runs:

```bash
pytest --maxfail=1 --disable-warnings --cov=app
```

against a real PostgreSQL service container
(`DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/postgres`), not SQLite — see
[Why SQLite in tests, PostgreSQL in production](#why-sqlite-in-tests-postgresql-in-production)
below for why the local/CI split doesn't create a second, untested code path.

Current status: 39/39 tests pass.

### Why SQLite in tests, PostgreSQL in production

`backend/tests/conftest.py` builds every test database from scratch, in memory:

```python
test_engine = create_async_engine(
    "sqlite+aiosqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
async with test_engine.begin() as conn:
    await conn.run_sync(Base.metadata.create_all)
```

`StaticPool` isn't incidental: SQLite's `:memory:` database only exists for the lifetime of one
connection, so without `StaticPool` forcing every checkout to reuse the same underlying
connection, each new session in the same test would see an empty, freshly-created database
instead of the one a previous session set up.

This is safe — not just fast — because of `app/models/base.py`'s design (see
[ADR-0002](adr/0002-dialect-portable-models.md) and [database.md](database.md)): every model
column uses SQLAlchemy 2.0's dialect-agnostic types (`Uuid`, `portable_json()`, `UTCDateTime`)
instead of PostgreSQL-specific ones, so the exact same model definitions and the exact same
schema (via `Base.metadata.create_all`) run against SQLite in tests and PostgreSQL in production
and CI. There is no parallel "test model" to keep in sync.

That said, "the same code path" is not automatically "the same behavior" — two real bugs found
and fixed this session are the concrete evidence for why this needs active care, not a one-time
setup:

1. **`MissingGreenlet` on tenant suspend.** `TimestampMixin.updated_at` is a server-side
   `onupdate=func.now()` column. By default, SQLAlchemy's async ORM leaves such columns expired
   after an UPDATE rather than fetching them via `RETURNING`; reading `tenant.updated_at` to build
   a response (`TenantResponse.model_validate(tenant)`) triggered an implicit lazy-load, which
   raises `MissingGreenlet` under asyncio because the lazy-load happens outside the session's
   IO-bridging context. Fixed by setting `Base.__mapper_args__ = {"eager_defaults": True}` in
   `app/core/database.py`, so every server-generated default is fetched via `RETURNING` on both
   INSERT and UPDATE.
2. **Naive-vs-aware datetime comparison on refresh-token expiry.**
   `refresh_session.expires_at < datetime.now(UTC)` (in `auth_service.refresh`) works fine against
   PostgreSQL's `TIMESTAMPTZ`, but SQLite has no timezone-aware storage type — `DateTime(timezone=True)`
   silently returns a **naive** datetime on read there, and comparing it to an aware
   `datetime.now(UTC)` raises `TypeError: can't compare offset-naive and offset-aware datetimes`.
   Fixed by introducing `UTCDateTime`, a `TypeDecorator` in `app/models/base.py` that re-attaches
   `UTC` tzinfo on read whenever the driver hands back a naive value, applied to every timestamp
   column in every model.

Both bugs were caught by the test suite itself this session (37/39 -> 39/39 passing), which is the
actual argument for exercising SQLite at all: it isn't just a speed optimization, it's the exact
seam where dialect-portability assumptions get tested. It cuts both ways, though — a bug like
these two only surfaces if something in the suite actually reads the affected column/comparison
after a mutation. Portability has to be maintained deliberately (always `UTCDateTime`, `Uuid`,
`portable_json()` — never the bare or PostgreSQL-specific types directly); nothing currently stops
a new column from being added with `DateTime(timezone=True)` and quietly reintroducing bug #2 in a
path the suite doesn't happen to exercise.

### Fixtures (`tests/conftest.py`)

Fixtures build the standard fixture set from Master Build Specification section 39:

- `engine` / `session_factory` / `db_session` — the SQLite engine described above, and an
  `AsyncSession` bound to it.
- `seed_permissions` / `seed_roles` — every permission code used anywhere in the fixture set, and
  the system roles (`SUPER_ADMIN`, `TENANT_ADMIN`, `MANAGER`, `OPERATOR`, `VIEWER`) each wired up
  with the permission set a real deployment would seed.
- `tenant_a` / `tenant_b` — two separate tenants, specifically so tenant-isolation tests have two
  tenants to violate (see `tests/integration/test_tenant_isolation.py`).
- `super_admin`, `tenant_a_admin`, `tenant_b_admin`, `tenant_a_viewer` — one user per role, giving
  permission tests a realistic principal to authenticate as.
- `tenant_a_plants` / `tenant_a_plant_manager` — two `OrganizationUnit` plants under tenant A and a
  `MANAGER` scoped to only one of them, used by the scope-authorization tests
  (`tests/unit/test_authorization_service.py`) to prove a grant at one org unit doesn't leak to a
  sibling.
- `client` — an `httpx.AsyncClient` wired to the FastAPI app via `ASGITransport`, with `get_db`
  overridden to hand out sessions from the same `session_factory` — integration tests exercise the
  real routing/middleware/dependency stack without a real socket or a real Postgres server.
- `login_headers(client, email)` — logs in with the fixture's known password
  (`RAW_PASSWORD = "TestPassword!123"`) and returns a ready-to-use `Authorization` header, used
  throughout the integration suite instead of hand-building JWTs.

### Test layout: `unit/` vs `integration/`

- **`tests/unit/`** (currently `test_authorization_service.py`) calls service functions directly
  against `db_session` — no HTTP, no router, no middleware. Good for exercising business logic
  (e.g. the scope-walk in `is_authorized`) one layer at a time.
- **`tests/integration/`** (`test_attachments.py`, `test_audit.py`, `test_auth.py`,
  `test_rbac.py`, `test_tenants.py`, `test_tenant_isolation.py`) drives the app through the
  `client` fixture end to end: real HTTP verbs against real routes, real JWT issuance/validation,
  real middleware. `test_tenant_isolation.py` is the most security-critical file in the suite —
  every case asserts a cross-tenant resource access returns `404`, not `403`, so tenant A can't
  even learn that tenant B's user IDs exist.

## Frontend

### Commands

```bash
cd frontend
npm test                                          # runs `ng test` -> Vitest, once, headless
```

CI (`azure-pipelines.yml`, `FrontendTests` job) runs:

```bash
npm test -- --watch=false --browsers=ChromeHeadless
```

Current status: 19/19 tests pass. `npm run lint` (ESLint via `angular-eslint`) reports 0 errors.

### Vitest via Angular's new test builder

`angular.json`'s `test` architect uses `@angular/build:unit-test` (Angular 22's built-in
Vitest-based builder), not the older Karma/Jasmine setup:

```json
"test": {
  "builder": "@angular/build:unit-test",
  "options": { "setupFiles": ["src/test-setup.ts"] }
}
```

`vitest` is a devDependency in `package.json`; there is no `karma.conf.js` anywhere in this repo.

### `src/test-setup.ts`: stubbing `localStorage`

Recent Node.js versions ship an experimental native `localStorage` that's disabled unless
`--localstorage-file` is passed but still takes precedence over jsdom's implementation, so
`globalThis.localStorage` can end up `undefined` under test regardless of the Node version
running the suite. Since `AuthService` (`core/auth/auth.service.ts`) reads/writes tokens via
`localStorage` directly, `test-setup.ts` installs a small `MemoryStorage` class (a `Map`-backed
`Storage` implementation) onto `globalThis.localStorage` whenever a working one isn't already
present. It's wired in through the `setupFiles` option shown above, so it runs once before any
spec file.

### Component/service specs: `TestBed` + `HttpTestingController`

Specs use Angular's `TestBed` to build a real component/service instance with fake collaborators,
not shallow snapshot tests:

- **HTTP is faked at the transport layer, not mocked function-by-function.** Specs that need real
  service logic exercised (`auth.service.spec.ts`, `error.interceptor.spec.ts`) provide
  `provideHttpClient()` + `provideHttpClientTesting()` and assert against
  `HttpTestingController.expectOne(...).flush(...)`, so the actual `HttpClient` pipeline
  (including interceptors, in the interceptor specs) runs — only the network call itself is
  faked.
- **Collaborators outside the unit under test are stubbed via `useValue`.** `login.component.spec.ts`
  stubs `AuthService` entirely (a plain object whose `login` method returns `of(FAKE_USER)` or
  `throwError(...)`), so the component spec exercises the component's own form-validation and
  error-display logic, not `AuthService`'s HTTP behavior — that's `auth.service.spec.ts`'s job.
  `auth.guard.spec.ts` similarly stubs `AuthService` down to just `isAuthenticated(): boolean` and
  drives the guard function directly via `TestBed.runInInjectionContext(...)`, without ever
  creating a component or touching the DOM.
- **`ActivatedRoute`/`Router` are provided via `provideRouter([...])`** with minimal stub routes
  (a blank `BlankTestComponent`) rather than a real route tree — just enough for
  navigation-related assertions (`authGuard`'s redirect-with-`returnUrl`, `LoginComponent`'s
  post-login navigation) to resolve.

The net effect: specs test one layer's actual logic against fake collaborators one level down,
mirroring the backend's `unit/` vs `integration/` split without a literal directory split on the
frontend.

## Where this runs

Both suites run in `azure-pipelines.yml`'s `Test` stage (see [azure.md](azure.md)), gated behind
the `Lint` stage passing first — a build never reaches the test stage with a lint failure already
present.
