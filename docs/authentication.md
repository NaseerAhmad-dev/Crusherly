# Authentication

This document covers how identity, login, token issuance/rotation, logout, and password reset work
in Phase 0. The implementation lives primarily in:

- `backend/app/services/auth_service.py` — login, refresh, logout, password-reset orchestration
- `backend/app/security/tokens.py` — JWT access/refresh token issuance and decoding
- `backend/app/security/passwords.py` — Argon2id password hashing (see `docs/security.md`)
- `backend/app/security/dependencies.py` — request-time authentication dependency
- `backend/app/models/refresh_session.py`, `backend/app/models/password_reset.py` — persisted
  auth state
- `backend/app/repositories/user_repository.py`, `refresh_session_repository.py`,
  `password_reset_repository.py`
- `backend/app/api/v1/auth.py` — the `/auth/*` HTTP surface

## Design premise: one global identity, no tenant selector

Login takes only `email` + `password` — there is no tenant picker on the login screen. This is
possible because `email` is **globally unique across the entire platform**, not just within a
tenant. That decision is recorded in **ADR-003** (`docs/adr/0003-global-email-uniqueness.md`) and
is enforced in two places:

- `users.email` carries a plain `unique=True` database constraint (`backend/app/models/user.py`),
  not a composite `(tenant_id, email)` constraint.
- `user_repository.get_by_email()` looks up by `func.lower(email)` with **no** `tenant_id` filter,
  and its docstring spells out why: a global login page has no tenant context to scope by, and if
  the same email were allowed under two tenants, a tenant-less lookup would be ambiguous about
  which row to return.

Case sensitivity is normalized at write time (email is lowercased before storage); the uniqueness
constraint sits on the already-lowercased value, and lookups also lowercase the input, so
`Foo@Bar.com` and `foo@bar.com` collide as the same identity.

One consequence worth calling out: a platform-level user (`is_platform_user=True`, `tenant_id`
nullable/`None`) and every tenant-level user share the same email namespace. There is exactly one
account per email address on the whole platform.

## Access vs. refresh tokens

Both are JWTs (`backend/app/security/tokens.py`, HS256, signed with `settings.jwt_secret_key`),
but they play very different roles:

| | Access token | Refresh token |
|---|---|---|
| Lifetime | `access_token_expire_minutes` (default 15 min) | `refresh_token_expire_days` (default 7 days) |
| Server-side state | None — pure stateless JWT | Backed by a `RefreshSession` row keyed by `jti` |
| Claims | `sub` (user id), `tenant_id`, `type=access`, `jti`, `iat`, `exp` | `sub`, `tenant_id`, `type=refresh`, `jti`, `iat`, `exp` |
| Revocable before expiry? | No | Yes — flip `revoked=True` on its `RefreshSession` row |
| Carries roles/permissions? | No | No |

`TokenType` (`backend/app/security/tokens.py`) is a `class TokenType(StrEnum)` with two members,
`ACCESS` and `REFRESH`; `decode_token()` takes an `expected_type` and rejects a refresh token
presented where an access token is expected and vice versa. (This session `TokenType` was moved
from `class TokenType(str, Enum)` to `StrEnum` — a Python 3.12 modernization with identical
runtime behavior: `.value`, string comparison, and JSON/claim serialization all work exactly as
before. No consumer needed to change.)

### Why access tokens are stateless and short-lived

The access token intentionally carries **only identity** (`sub`, `tenant_id`) — no roles, no
permissions, no cached scope. Every authenticated request re-resolves the caller's full security
context (roles, permissions, org-unit scope) from the database via
`build_security_context()` (see `backend/app/security/dependencies.py`,
`require_authenticated_user`). The tradeoff this buys: a role change, a permission grant, or a
`deactivate_user` takes effect on the *next request*, not after the access token happens to
expire. The cost is a DB round trip on every request to resolve RBAC state — acceptable at Phase 0
scale, and isolated behind a single function if it ever needs caching.

Because access tokens are never persisted, there is no way to revoke one before it expires. That's
why they're kept short (15 minutes by default): the blast radius of a stolen access token is
capped by its own expiry, not by any revocation mechanism.

### Why refresh tokens are stateful ("opaque-by-reference")

A refresh token's JWT is verifiable on its own (signature + `exp`), but `auth_service.refresh()`
additionally requires a live, non-revoked `RefreshSession` row matching its `jti`
(`backend/app/models/refresh_session.py`). This is what makes logout and "revoke all sessions"
possible at all — something a purely stateless refresh token could never support, since a valid
signature alone can't be un-signed. The `RefreshSession` row also carries `ip_address` and
`user_agent` captured at issuance time, laying the groundwork for a login-history / active-sessions
view (Master Build Specification section 7) without needing a schema change later.

Access tokens are *not* tracked row-by-row — only refresh tokens are, because only refresh tokens
are long-lived enough that revocability matters.

## Login flow (`POST /api/v1/auth/login`)

`auth_service.login()`:

1. Look up the user by email (`user_repository.get_by_email`, tenant-agnostic — see above).
2. If no user matches, or the password fails `verify_password()` (Argon2id, see
   `docs/security.md`): increment `failed_login_attempts` on the user (only if a user row actually
   exists — an unknown email doesn't create counter state anywhere), lock the account
   (`status = UserStatus.LOCKED`) once `failed_login_attempts >= _MAX_FAILED_ATTEMPTS` (10, a
   module-level constant in `auth_service.py`), write an audit `LOGIN_FAILED` record, commit, and
   raise `UnauthorizedError("Invalid email or password.")`.
   - The error message is identical whether the email doesn't exist or the password is wrong —
     this endpoint does not distinguish the two failure modes to a caller.
3. If the user exists and the password matches but `status != ACTIVE` (i.e. `INACTIVE` or
   `LOCKED`), audit a `LOGIN_FAILED` with the specific status reason, commit, and raise
   `UnauthorizedError("This account is not active.")`.
4. On success: reset `failed_login_attempts` to 0, stamp `last_login_at`, issue a fresh access +
   refresh token pair (`_issue_token_pair`), write an audit `LOGIN` record, and commit.

All of this — the counter increment, the lock, and the eventual success path — happens inside one
`AsyncSession`/transaction per call, with `audit_service.record()` writing an audit row before the
final commit regardless of outcome.

### Account lockout

`UserStatus.LOCKED` is set by `login()` alone; nothing else in the codebase sets it. There is no
automatic unlock — a locked account requires an administrator to explicitly move it back to
`ACTIVE` via `PATCH` on the user resource (`user_service.update_user()`, which accepts a `status`
field on `UserUpdateRequest`). There is no time-based lockout expiry. See `docs/security.md` for
the fuller picture of what brute-force protection does and does not exist at Phase 0.

## Token refresh and rotation-on-use (`POST /api/v1/auth/refresh`)

`auth_service.refresh()`:

1. Decode the presented token, requiring `expected_type=TokenType.REFRESH`. A malformed, expired,
   or wrong-type token raises `UnauthorizedError` immediately.
2. Look up the `RefreshSession` by `jti`. If it doesn't exist, or `revoked=True`, reject —
   `"Refresh token has been revoked or does not exist."`
3. Check `refresh_session.expires_at < datetime.now(UTC)`. If expired, reject —
   `"Refresh token has expired."`
4. Re-fetch the user by id and require `status == ACTIVE`; a deactivated/locked user cannot refresh
   even with an otherwise-valid, unexpired refresh token.
5. **Rotate**: set `refresh_session.revoked = True` on the token just used, then call
   `_issue_token_pair()` again — which mints a brand-new access token *and* a brand-new refresh
   token with a brand-new `jti` and a brand-new `RefreshSession` row.
6. Commit and return the new pair.

The old refresh token's `jti` is permanently revoked at step 5 whether or not anything went wrong
— a refresh token can only ever be used once. This bounds the damage from a stolen refresh token:
if the legitimate client and an attacker both hold a copy, whichever uses it first invalidates it
for the other, and if the legitimate client is the one locked out, that's a detectable signal
(their next refresh attempt fails) rather than silent, indefinite exposure like a
never-expiring, always-valid refresh token would be.

### A bug that was found and fixed here this session: naive vs. aware datetime comparison

Step 3 above (`refresh_session.expires_at < datetime.now(UTC)`) compares a stored, tz-aware value
against `datetime.now(UTC)`. On PostgreSQL this was never a problem, because `TIMESTAMPTZ` columns
round-trip tzinfo natively. On SQLite — which backs the fast unit-test suite (see
`tests/conftest.py`) — a plain `DateTime(timezone=True)` column silently returns a **naive**
`datetime` on read, and comparing a naive value against an aware one raises
`TypeError: can't compare offset-naive and offset-aware datetimes`. That crashed every refresh call
under SQLite, i.e. every test.

The fix was `UTCDateTime`, a `TypeDecorator` in `backend/app/models/base.py` that wraps
`DateTime(timezone=True)` and re-attaches `tzinfo=UTC` on read if the driver came back naive. Every
timestamp column that gets compared against `datetime.now(UTC)` — including
`RefreshSession.expires_at` and `PasswordResetToken.expires_at`/`used_at` — uses `UTCDateTime()`
instead of `DateTime(timezone=True)` directly, specifically so the same comparison behaves
identically on SQLite and PostgreSQL. See `docs/database.md` for the full writeup of this type and
why the codebase standardizes on it for every timestamp column, not just these two models.

## Logout / session revocation (`POST /api/v1/auth/logout`)

`auth_service.logout()` takes a refresh token (not the access token — there's nothing to revoke on
an access token), decodes it, and:

- If the token doesn't decode as a valid refresh token, **return silently** — logout is
  deliberately idempotent, so presenting an already-invalid/expired/garbage token is not an error.
- If it decodes, look up the `RefreshSession` by `jti`. If found, set `revoked = True`, write an
  audit `LOGOUT` record, and commit. If the session row is already gone or already revoked, this
  is a no-op (still not an error).

This revokes exactly the one session tied to the presented refresh token — i.e. logout is
per-device/per-session, not a blanket "log out everywhere." A `RefreshSession` per login means a
"revoke all sessions" operation (walk every non-revoked `RefreshSession` row for the user and set
`revoked=True`) is a straightforward extension of the same mechanism, but no such endpoint exists
yet in Phase 0 — only single-session logout is wired up via the router.

Access tokens issued before a logout remain valid until they naturally expire (up to 15 minutes by
default) since nothing about logout touches them; this is the direct consequence of access tokens
being stateless (see above).

## Password reset flow

Two endpoints, `POST /auth/forgot-password` and `POST /auth/reset-password`, backed by
`PasswordResetToken` (`backend/app/models/password_reset.py`).

### `request_password_reset(email)`

1. Look up the user by email. If none exists, or the account isn't `ACTIVE`, **return
   immediately with no error and no side effect** — the docstring is explicit:
   *"Always succeeds from the caller's point of view (no user enumeration)."* The router
   (`backend/app/api/v1/auth.py`) always responds with the same message —
   `"If an account exists for this email, a reset link has been sent."` — regardless of whether an
   account actually exists, so an attacker cannot use this endpoint to test which emails are
   registered.
2. If the account is real and active, generate a raw token: `uuid.uuid4().hex + uuid.uuid4().hex`
   (a 64-hex-character random string — not a JWT, not derived from any user data).
3. **Hash the raw token with the same Argon2id hasher used for passwords**
   (`hash_password()`/`verify_password()` from `app/security/passwords.py`) and store only the
   hash in `PasswordResetToken.token_hash`. The raw token is never persisted anywhere — the same
   principle as never storing a plaintext password applies here (see the model's own docstring).
4. Set `expires_at = now + 1 hour`.
5. Commit.

**Phase 0 does not deliver reset emails.** There is no email/SMS channel wired up yet — the raw
token is not dispatched anywhere a real user could retrieve it in production. In non-production
environments only (`if not settings.is_production`), the raw token is logged at **debug** level
(`logging.getLogger("app.auth").debug(...)`) purely so the reset flow is exercisable end-to-end in
local development. The comment in `auth_service.py` notes the intended integration point once it
exists: the notification service's EMAIL channel (`app/services/notification_service.py`). Until
that lands, this endpoint is not usable as an actual "forgot password" feature for real users in
production — only its plumbing exists.

### `reset_password(token, new_password)`

The raw token can't be looked up directly by its hash, because Argon2 hashes are salted (the same
input produces a different hash every time), so there is no `WHERE token_hash = hash(token)`
shortcut. Instead:

1. Select every `PasswordResetToken` row where `used_at IS NULL` (i.e. every still-unused token,
   across all users), and linearly scan them with `verify_password(token, candidate.token_hash)`
   until one matches. The comment in `auth_service.py` acknowledges this is a table scan and calls
   it "acceptable at Phase 0 volumes; revisit if this table grows."
2. If no candidate matches, or the matched token's `expires_at` has passed, raise
   `UnauthorizedError("Password reset token is invalid or has expired.")` — again, the same
   generic message whether the token is garbage, already used, or genuinely expired.
3. Re-fetch the user by `matched.user_id`; if somehow gone, same generic error.
4. Set `user.password_hash = hash_password(new_password)` and `matched.used_at = datetime.now(UTC)`
   — **in the same transaction**, so a token can never be used twice: once `used_at` is set, the
   very next reset attempt won't find this row among the `used_at IS NULL` candidates in step 1.
5. Commit.

Note that `reset_password` does not revoke the user's existing refresh sessions. A password reset
does not, by itself, force other logged-in devices to re-authenticate — anything holding a
still-valid access or refresh token from before the reset keeps working until it naturally expires
or is otherwise revoked via `/auth/logout`.

## `GET /api/v1/auth/me`

The one authenticated-only route in this router. It depends on
`require_authenticated_user` (`app/security/dependencies.py`), which:

1. Extracts the Bearer token via `HTTPBearer(auto_error=False)`, decodes it requiring
   `expected_type=TokenType.ACCESS` (a refresh token is rejected here even if otherwise valid).
2. Re-fetches the `User` row by the token's `sub`, and requires `status == ACTIVE` — a token issued
   while a user was active is rejected the moment their status changes, without waiting for the
   token to expire.
3. Calls `build_security_context()` to resolve roles/permissions/scope fresh from the database
   (see "Why access tokens are stateless" above).

`/me` returns the resolved identity plus sorted `roles` and `permissions` code lists — useful as a
smoke test that a token is valid and to see exactly what the security context resolved to.

## Summary of guarantees and their limits

- One account per email, platform-wide; no tenant selector needed at login.
- Access tokens are cheap to verify, cannot be revoked early, and are kept short-lived to bound
  that risk.
- Refresh tokens are single-use (rotation) and revocable (via `RefreshSession.revoked`), which is
  what makes logout meaningful.
- Login/refresh/reset failures return deliberately generic messages to avoid leaking which part of
  the credential was wrong or whether an account exists.
- Password reset is fully wired end-to-end except for actual delivery — there is no working
  "forgot password" email in this phase, only a debug-log stand-in for local development.
- Logout is per-session; there is currently no "log out everywhere" endpoint, though the data model
  (`RefreshSession` per login) supports adding one without a schema change.
