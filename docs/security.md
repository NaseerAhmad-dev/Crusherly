# Security

This document covers the platform-wide security controls that apply regardless of module or
tenant: password hashing, rate limiting, security headers, CORS, and secret management. For
authentication (login, tokens, sessions, password reset) see `docs/authentication.md`; for
authorization (roles, permissions, scopes) see `docs/authorization.md`.

Source of truth for everything below:

- `backend/app/security/passwords.py`
- `backend/app/middleware/rate_limit.py`
- `backend/app/middleware/security_headers.py`
- `backend/app/core/config.py`
- `backend/app/main.py` (middleware registration and ordering)

## Password hashing

`backend/app/security/passwords.py` hashes every password with **Argon2id**, via `argon2-cffi`'s
`PasswordHasher()` constructed with its library defaults (the module's own docstring: *"Never store
plaintext passwords. `argon2-cffi`'s default `PasswordHasher` uses Argon2id."*). No custom
time/memory/parallelism cost parameters are set — the library's defaults are used as-is.

Three functions, and nothing else touches a password hash directly anywhere else in the codebase:

- `hash_password(plain_password) -> str` — used for real passwords at signup/reset, and reused
  as-is to hash password-reset tokens before they're stored (see `docs/authentication.md`) and to
  compare a presented reset token against stored hashes with `verify_password`. Reusing the same
  primitive for both is deliberate: a reset token needs the same "never store the raw secret"
  property a password does.
- `verify_password(plain_password, password_hash) -> bool` — wraps `_hasher.verify()` and turns
  `VerifyMismatchError`, `VerificationError`, and `InvalidHash` all into a plain `False` rather than
  letting any of them propagate. A malformed or foreign-format hash in the database fails a login
  attempt instead of throwing a 500.
- `needs_rehash(password_hash) -> bool` — wraps `_hasher.check_needs_rehash()`, for detecting a
  hash that was created under weaker-than-current Argon2 parameters (e.g. after a future parameter
  upgrade). Nothing currently calls this function — it exists as a ready-made upgrade path, not
  something wired into the login flow yet.

## Rate limiting

`backend/app/middleware/rate_limit.py` — `RateLimitMiddleware`, registered globally in
`backend/app/main.py`, applies to **every** request except `/health` and `/ready`.

It is explicitly documented as a Phase 0 starting point, not a production-grade distributed
limiter:

- **Fixed-window, in-memory, per-process.** State is a `dict[str, deque]` held in the middleware
  instance itself — not Redis, not any shared store. It resets on process restart and is **not
  shared across multiple backend replicas**: if the app is horizontally scaled, each instance
  enforces its own independent limit, so the effective platform-wide limit is
  `limit x replica_count`, not `limit`.
- **Keyed by client IP** (`request.client.host`, falling back to the literal string `"unknown"` if
  the ASGI server didn't supply a client). There's no per-user or per-API-key bucketing — two
  different authenticated users behind the same NAT/proxy IP share one bucket, and one abusive
  actor behind a shared IP can exhaust the budget for everyone else on that IP.
- **Window**: a hardcoded 60-second sliding window (`_WINDOW_SECONDS = 60`), implemented as a
  `deque` of monotonic timestamps per client key; on each request, entries older than 60 seconds
  are popped off the front before the current count is checked.
- **Limit**: `settings.rate_limit_per_minute`, which defaults to **120 requests per minute per
  client key** (`RATE_LIMIT_PER_MINUTE` env var / `Settings.rate_limit_per_minute` in
  `app/core/config.py`). The middleware also accepts an explicit `requests_per_minute` constructor
  override, but nothing in `main.py` currently passes one — it runs at the configured default.
- **Exceeding the limit** returns HTTP `429` with a JSON body matching the platform's standard
  error envelope:
  ```json
  {
    "success": false,
    "error": {
      "code": "RATE_LIMITED",
      "message": "Too many requests. Please slow down.",
      "request_id": "<the request's correlation id, if one was assigned yet>"
    }
  }
  ```
  Note `request_id` is read from `request.state.request_id`, which is set by
  `RequestContextMiddleware` — and per the registration order in `main.py` (rate limiting is added
  *before* request-context, and Starlette/ASGI middleware executes outer-to-inner in registration
  order for the "in" direction), the rate limiter actually runs **before** the request-ID
  middleware assigns an ID for that request, so `request_id` on a 429 body will typically be
  `None` unless the caller supplied their own `X-Request-ID` header.
- There is **no per-route configuration** — login, refresh, password-reset, and every business
  endpoint all share the same global 120/minute/IP budget. There is no tighter, purpose-specific
  limit on `/auth/login` or `/auth/forgot-password` specifically (see "Known gaps" below).

The middleware's own docstring states the intended evolution: it "gives future modules a place to
plug in a Redis-backed limiter later without changing call sites" — i.e. the `dispatch()` interface
is meant to stay the same when the in-memory `deque` is eventually swapped for a shared store.

## Security headers

`backend/app/middleware/security_headers.py` — `SecurityHeadersMiddleware`, registered globally,
sets these headers on **every** response (via `setdefault`, so a route that explicitly sets one of
these headers itself wins; nothing currently does):

| Header | Value | Always set? |
|---|---|---|
| `X-Content-Type-Options` | `nosniff` | Yes |
| `X-Frame-Options` | `DENY` | Yes |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | Yes |
| `Permissions-Policy` | `geolocation=(), microphone=(), camera=()` | Yes |
| `Strict-Transport-Security` | `max-age=63072000; includeSubDomains; preload` | Only when `settings.is_production` is `True` |

HSTS is deliberately withheld outside production — sending `Strict-Transport-Security` over plain
HTTP local development would be actively harmful (browsers would start forcing HTTPS for that host
even though local dev typically doesn't terminate TLS).

Notably absent: no `Content-Security-Policy` header is set anywhere. There is no CSP at all in
Phase 0 (see "Known gaps").

## CORS

Configured once in `backend/app/main.py` via Starlette's `CORSMiddleware`, using
`settings.cors_origins_list`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)
```

`cors_origins_list` (a `@property` on `Settings` in `app/core/config.py`) splits the single
`cors_allowed_origins` env var on commas and strips whitespace, so multiple allowed origins are
configured as one comma-separated string (e.g.
`CORS_ALLOWED_ORIGINS=http://localhost:4200,https://app.example.com`). The default is
`http://localhost:4200` — the Angular dev server's origin — so nothing outside local development is
allowed to call the API cross-origin until this is explicitly configured per environment.

`allow_credentials=True` combined with `allow_methods=["*"]`/`allow_headers=["*"]` means: any
origin present in the explicit allow-list can make credentialed cross-origin requests (cookies /
Authorization headers) using any method and any header. This is safe specifically *because*
`allow_origins` is an explicit list rather than a wildcard (`allow_credentials=True` with a literal
`"*"` origin is disallowed by browsers anyway) — so the security boundary here is entirely the
contents of `CORS_ALLOWED_ORIGINS` per environment, not the method/header permissiveness. Getting
that env var right per deployment is what actually matters.

`expose_headers=["X-Request-ID"]` lets frontend JS read the correlation ID
(`RequestContextMiddleware`, see `docs/authentication.md`/architecture docs) off the response for
client-side logging/support correlation — it wouldn't be visible to `fetch`/`XHR` otherwise, since
browsers only expose a small default header allowlist to script unless a header is explicitly
listed here.

## Middleware ordering

Registered in `main.py` in this order (with the comment *"Order matters: outermost middleware runs
first on the way in / last on the way out"*):

1. `CORSMiddleware`
2. `SecurityHeadersMiddleware`
3. `RateLimitMiddleware`
4. `RequestContextMiddleware`

Since Starlette wraps each `add_middleware` call around the previous stack, the **last** one
registered (`RequestContextMiddleware`) is actually the **innermost** — closest to the route
handler — and runs last on the way in. Concretely: CORS preflight/headers are handled outermost;
security headers are added on the way out after everything else; rate limiting rejects over-budget
requests before they reach request-ID assignment or the route handler (which is why a 429 body's
`request_id` is often empty, as noted above); and `request_id_var`/`request.state.request_id` are
only populated for requests that make it past the rate limiter.

## Secret management: `.env` in development, Azure Key Vault in production

`backend/app/core/config.py` loads all configuration through `pydantic-settings`
(`Settings(BaseSettings)`), and its module docstring states the pattern directly:

> Local secrets live in `.env` (never committed); production secrets are injected via Azure Key
> Vault into the same environment variable names, so no code branches on where the secret
> physically lives.

Concretely: `Settings` declares fields like `jwt_secret_key`, `database_url`,
`azure_storage_connection_string`, and `applicationinsights_connection_string` as ordinary
environment-variable-backed settings (`model_config` points at `.env` via
`SettingsConfigDict(env_file=".env", ...)`). In development, these come from a local `.env` file
(see `backend/.env.example`, copied per the top-level README's quick-start). In production, the
same environment variable names (`JWT_SECRET_KEY`, `DATABASE_URL`, etc.) are populated by whatever
injects Key Vault secrets into the process environment before startup — `Settings` itself has no
Key Vault client code and doesn't need one; `azure_key_vault_url` is just another settings field
(currently unused by any Key Vault-fetching code in this repo — the injection is assumed to happen
outside the Python process, e.g. at the container/App Service level). This is what "no code
branches on where the secret physically lives" means literally: `get_settings()` is identical code
in both environments, only the source of the process environment differs.

The default `jwt_secret_key` — `"dev-only-insecure-secret-change-me"` — is intentionally an obvious
placeholder baked into the `Field(default=...)`, not a "works but is weak" secret, so that running
with the literal default is unmistakable to a reviewer. There's no runtime check that refuses to
start in production with the default secret still set; the safety here is purely the value's
own honesty.

`Settings.is_production` (`environment == "production"`) is the single flag several other security
decisions branch on: HSTS emission (`SecurityHeadersMiddleware`) and whether a password-reset token
is ever logged (`auth_service.request_password_reset`, see `docs/authentication.md`) both key off
it.

## Known gaps (Phase 0)

These are verified absences in the current code, not a roadmap — they're called out so nobody
assumes protections exist that don't yet:

- **No account lockout beyond a permanent flag.** `auth_service.py`'s `_MAX_FAILED_ATTEMPTS = 10`
  and `User.failed_login_attempts` (`app/models/user.py`) implement a simple "lock after N failed
  attempts" counter that sets `status = UserStatus.LOCKED`. There is no automatic unlock, no
  time-boxed lockout (e.g. "locked for 15 minutes"), and no exponential backoff between attempts —
  a locked account stays locked until an administrator manually resets its `status` via
  `PATCH` on the user resource (`user_service.update_user`). There is also no CAPTCHA or
  progressive delay on the login endpoint itself.
- **No per-endpoint rate limiting.** As described above, `/auth/login`, `/auth/forgot-password`,
  and `/auth/reset-password` share the same global 120-requests/minute/IP budget as every other
  route. A credential-stuffing or token-guessing attempt distributed across many source IPs is not
  meaningfully slowed by this limiter.
- **No MFA / two-factor authentication.** There is no TOTP, WebAuthn, SMS, or email-based
  second factor anywhere in the codebase — login is single-factor (email + password) for every
  account, including platform-level (`is_platform_user=True`) accounts.
- **No Content-Security-Policy header.** `SecurityHeadersMiddleware` sets
  `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy`, and
  (production-only) HSTS, but no `Content-Security-Policy` at all.
- **No distributed/shared rate-limit state.** Confirmed above: the limiter is in-process memory,
  so it does not coordinate across multiple backend replicas and resets on every restart.
- **Password-reset delivery is not implemented.** Covered in full in `docs/authentication.md`: the
  reset-token flow is complete end-to-end except for actually emailing/texting the token to the
  user, which does not exist yet in Phase 0.
- **`needs_rehash()` is unused.** The function exists in `passwords.py` for detecting
  under-parameterized Argon2 hashes but nothing calls it — there is no automatic rehash-on-login
  upgrade path wired up yet.

None of these are treated here as defects to be silently patched — they're explicit Phase 0
boundaries. Anyone building on top of this foundation should not assume brute-force protection,
CSP, distributed rate limiting, or MFA exist until a later phase actually adds them.
