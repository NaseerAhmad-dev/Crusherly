# 2. Dialect-Portable Models (SQLite for Tests, PostgreSQL in Production)

## Status

Accepted

## Context

PostgreSQL 16 is the database in every real environment. The test suite needs to run fast,
anywhere, without a live database server — `backend/tests/conftest.py` builds a fresh in-memory
SQLite database per test run via `sqlite+aiosqlite://` with `StaticPool`. For that to be a
meaningful test of the real application, rather than a test of a SQLite-specific approximation of
it, the exact same SQLAlchemy model definitions have to run unmodified against both databases;
maintaining two parallel sets of model definitions (or two sets of migrations) was rejected from
the start as an ongoing maintenance and drift risk.

`app/models/base.py`'s module docstring states the resulting constraint directly: every column
must use SQLAlchemy 2.0's dialect-agnostic types (`Uuid`, `JSON`/`portable_json()`) "rather than
`sqlalchemy.dialects.postgresql.UUID`/`JSONB` directly ... so the exact same model definitions run
against PostgreSQL in production and SQLite in the fast unit-test suite."

This is not a purely theoretical concern. During Phase 0 development, two real, user-facing bugs
shipped specifically because a piece of dialect behavior diverged between SQLite and PostgreSQL in
a way that plain SQLAlchemy types don't paper over:

1. A `MissingGreenlet` crash in the tenant-suspend endpoint. SQLAlchemy's async ORM leaves
   server-computed columns (`onupdate=func.now()`) expired after an UPDATE by default; reading
   `tenant.updated_at` to serialize a response after `session.flush()` triggered an implicit
   lazy-load, which is fatal under asyncio because it happens outside the session's IO-bridging
   context.
2. A naive-vs-aware `datetime` comparison crash in refresh-token expiry checking. PostgreSQL's
   `TIMESTAMPTZ` round-trips timezone-aware datetimes; SQLite has no timezone-aware storage type
   at all, so plain `DateTime(timezone=True)` silently returns a **naive** datetime on read there.
   Comparing that naive value against `datetime.now(UTC)` (aware) raised
   `TypeError: can't compare offset-naive and offset-aware datetimes` — a comparison that works
   fine against real PostgreSQL.

Both were found and fixed in the same session (see [docs/testing.md](../testing.md)), and both
are the direct evidence for this ADR: SQLAlchemy's "dialect-agnostic" types (`Uuid`, `JSON`) do
not automatically make *behavior* identical across dialects — only *schema* portable. Behavior
parity for anything dialect-sensitive (timestamp handling, in this case) needed an explicit
abstraction of its own.

## Decision

Use SQLAlchemy 2.0's dialect-agnostic column types everywhere, plus two purpose-built helpers in
`app/models/base.py` for the two behaviors plain types don't make portable:

- `Uuid(as_uuid=True)` (not `postgresql.UUID`) for every primary/foreign key — compiles to native
  `uuid` on PostgreSQL, `CHAR(32)` elsewhere.
- `portable_json()` — `JSON().with_variant(JSONB(), "postgresql")` — for schemaless columns,
  instead of a raw `JSONB` import. Compiles to `JSONB` on PostgreSQL, plain `JSON` elsewhere.
- `UTCDateTime`, a `TypeDecorator` wrapping `DateTime(timezone=True)` that re-attaches `UTC`
  tzinfo in `process_result_value` whenever the underlying driver returns a naive value. Applied
  to every timestamp column in the codebase (`TimestampMixin.created_at`/`updated_at` and any
  other datetime column) instead of using `DateTime(timezone=True)` directly.
- `Base.__mapper_args__ = {"eager_defaults": True}` (in `app/core/database.py`) so
  server-generated defaults are fetched via `RETURNING` on both INSERT and UPDATE, eliminating the
  implicit-lazy-load path that caused bug #1, mapper-wide, rather than requiring a per-endpoint
  `session.refresh()` call.

## Consequences

**Positive:**

- The test suite runs in-memory, with no external database dependency, and still exercises the
  real model definitions and (via `Base.metadata.create_all`) the real schema shape — not a
  hand-maintained SQLite-only fixture schema.
- New models get dialect portability and timestamp-comparison correctness "for free" by using the
  existing mixins (`UUIDPrimaryKeyMixin`, `TimestampMixin`) rather than needing per-model
  reasoning about dialect differences.
- The `eager_defaults` fix is mapper-wide, so it protects every current and future model against
  the same class of `MissingGreenlet` bug, not just the tenant-suspend endpoint where it was
  found.

**Negative / accepted trade-offs:**

- Portability has to be actively maintained, not just declared once: any new timestamp column that
  uses `DateTime(timezone=True)` directly instead of `UTCDateTime()` silently reintroduces bug #2,
  and nothing currently enforces this at the type-checker or lint level — it relies on code review
  and the precedent set in `app/models/base.py`'s docstring.
- SQLite and PostgreSQL still diverge in ways these helpers don't cover (e.g. no real `JSONB`
  containment/indexing operators under SQLite, no genuine concurrent-write behavior), so the test
  suite cannot catch every PostgreSQL-specific bug — dialect portability narrows the gap for the
  specific behaviors (UUID storage, JSON storage, timestamp timezone-awareness) shown to matter,
  not all of them.
- The two bugs this ADR documents were only caught because the test suite happened to exercise the
  affected code paths (a response that reads `updated_at` right after an update; a refresh-token
  flow that compares `expires_at`). A future column or comparison added without equivalent test
  coverage could reintroduce a similar class of bug undetected until it reaches a SQLite-backed
  environment or, worse, a real dialect-behavior gap not covered by the fixes above.
