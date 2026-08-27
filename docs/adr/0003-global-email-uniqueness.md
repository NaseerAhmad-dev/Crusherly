# 3. Email Is Globally Unique Across the Platform, Not Per-Tenant

## Status

Accepted

## Context

`User.email` needs a uniqueness scope: either unique within a tenant (two different tenants could
each have a `user@example.com`) or unique across the entire platform (only one `user@example.com`
can ever exist, regardless of tenant).

The login flow was designed to take only email and password — `app/services/auth_service.py`'s
module docstring states directly: *"Email is unique across the whole platform, so login takes only
email+password, no tenant selector."* There is no tenant-selection step before or during login.
If email uniqueness were scoped per-tenant instead, looking up a user by email at login time would
be ambiguous whenever the same email existed under two different tenants, and resolving that
ambiguity would require either a tenant selector on the login form (adding a step that a global
login page has no context to skip) or an arbitrary tie-breaking rule.

This decision is referenced in code as `ADR-003` in three places:
`app/repositories/user_repository.py` (`get_by_email`'s docstring), `app/services/auth_service.py`
(module docstring), and `app/models/user.py` (the `email` column comment) — this document is the
write-up those references point to.

## Decision

`User.email` is unique across the entire platform, enforced with a single-column `unique=True`
constraint (plus an index) on `users.email` — not a composite `(tenant_id, email)` uniqueness
constraint. `user_repository.get_by_email()` looks up by email alone, with no `tenant_id` filter,
and is used for both login and uniqueness checks during user creation.

Case sensitivity is normalized to lowercase at write time by the service layer (comment in
`app/models/user.py`); the database constraint applies to the already-lowercased stored value, so
`User@Example.com` and `user@example.com` are treated as the same account.

`User.tenant_id` itself is nullable specifically to accommodate this: platform users
(`is_platform_user=True`, e.g. `SUPER_ADMIN`) have no tenant at all, and tenant users have exactly
one (enforced in the service layer — see [docs/database.md](../database.md)).

## Consequences

**Positive:**

- Login is a single email+password form with no tenant-selection step, and no ambiguity to
  resolve when looking up "the user with this email" — there is always at most one.
- Uniqueness is enforced at the database level (a `UNIQUE` constraint), not just application
  logic, so it holds even against a bug or a direct-SQL write that bypasses the service layer's
  lowercase normalization.

**Negative / accepted trade-offs:**

- A person cannot hold accounts in two different tenants under the same email address — a real
  limitation for, e.g., a consultant or auditor working across multiple client tenants, who would
  need a distinct email alias per tenant.
- Because normalization to lowercase happens in the service layer rather than being guaranteed by
  the database (SQLite and PostgreSQL don't share a portable case-insensitive `citext`-equivalent
  type usable here — see [ADR-0002](0002-dialect-portable-models.md)), any future write path that
  inserts a `User` row without going through the service layer risks bypassing normalization and
  either creating a duplicate account the unique constraint should have prevented, or failing the
  constraint unexpectedly on a case mismatch.
- Any future tenant self-service signup/onboarding flow must check global email uniqueness up
  front and design its error messaging around "this email is already registered" rather than
  "already registered under this organization," since the platform has no per-tenant email
  namespace to fall back on.
