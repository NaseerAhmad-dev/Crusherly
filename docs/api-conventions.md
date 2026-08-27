# API Conventions

This document describes the HTTP conventions implemented in `backend/app/api/v1/`,
`backend/app/schemas/common.py`, `backend/app/core/error_handlers.py`, and
`backend/app/security/dependencies.py`. Every current and future router (business modules
included, once their phase starts — see [README.md](../README.md)) follows these conventions;
none of it is per-router improvisation.

## Prefix and docs

Every route is mounted under `settings.api_v1_prefix` (`/api/v1` by default —
`backend/app/core/config.py`), applied once in `create_app()`:

```python
app.include_router(api_router, prefix=settings.api_v1_prefix)
```

OpenAPI docs are served from the same prefix rather than FastAPI's defaults —
`docs_url=f"{settings.api_v1_prefix}/docs"`, `redoc_url=.../redoc`,
`openapi_url=.../openapi.json` — so interactive docs live at `/api/v1/docs` (Swagger) and
`/api/v1/redoc`, per the README's Quick Start. `/health` and `/ready` are the two exceptions:
liveness/readiness probes sit outside the versioned API entirely, at the application root, since
infra health checks shouldn't need to know the API version.

## Response envelopes (`app/schemas/common.py`)

Every response body — success or error — is a JSON object with a top-level `"success"` boolean.
There is no bare/unwrapped response anywhere in the API; a client can always branch on
`response.success` without needing to know the endpoint's specific shape first.

Three envelope shapes cover every endpoint:

```python
class SuccessResponse[T](BaseModel):
    success: bool = True
    data: T

class PageMeta(BaseModel):
    page: int
    page_size: int
    total_items: int
    total_pages: int

class Page[T](BaseModel):
    success: bool = True
    data: list[T]
    meta: PageMeta

class MessageResponse(BaseModel):
    success: bool = True
    message: str
```

`SuccessResponse[T]` and `Page[T]` use PEP 695 generic syntax (`class Page[T](BaseModel)`), not
the older `Generic[T]`/`TypeVar` style — this is a Python 3.12+ codebase (see
`pyproject.toml`'s `target-version = "py312"`) and the newer syntax is what current Pydantic v2
expects for clean generic model resolution; mixing in the old `Generic[T]` style caused schema
generation issues and was corrected.

- **Single-resource reads/writes** return `SuccessResponse[SomeResponse]` — e.g.
  `GET /api/v1/tenants/{id}` and `POST /api/v1/tenants` both return
  `{"success": true, "data": {...}}` (see `backend/app/api/v1/tenants.py`).
- **List endpoints that support pagination** return `Page[SomeResponse]` — a `"data"` array plus
  a `"meta"` block, never a bare array. `GET /api/v1/tenants`, `GET /api/v1/users`, and
  `GET /api/v1/audit` all follow this shape.
- **List endpoints that don't paginate** (small, fully-seeded reference lists, not paged for
  their own sake) still return `SuccessResponse[list[T]]`, e.g. `GET /api/v1/roles` and
  `GET /api/v1/permissions` — the `"data"` field is a list rather than a scalar, but there is no
  `"meta"` because the route never accepted `page`/`page_size` in the first place.
- **Actions with no meaningful resource body** (logout, forgot-password, delete/deactivate)
  return `MessageResponse` — `{"success": true, "message": "..."}`.

`ORMModel` (also in `common.py`) is the base class every `*Response` schema extends:
`model_config = ConfigDict(from_attributes=True)`, so a schema can be built directly from an ORM
instance via `SomeResponse.model_validate(orm_object)` without manually unpacking attributes.

## Pagination

Paginated list routes accept `page` (default `1`, `ge=1`) and `page_size` (default `20`,
`ge=1, le=200`) as query parameters — `Query(default=1, ge=1)` /
`Query(default=20, ge=1, le=200)`, identical across `tenants.py`, `users.py`, and `audit.py`.
`PaginationParams` in `common.py` documents the same defaults and derives `offset`/`limit` for
callers that want a single object instead of two loose parameters, though the current routers
compute the offset inline (`(page - 1) * page_size`) rather than instantiating it.

The response's `meta` block always reports `page`, `page_size`, `total_items`, and
`total_pages`, computed as:

```python
total_pages=max(1, math.ceil(total / page_size))
```

The `max(1, ...)` means an empty result set still reports `total_pages: 1`, not `0` — a client
paginator never has to special-case "zero pages" to render an empty state.

Example (`GET /api/v1/tenants?page=1&page_size=20`):

```json
{
  "success": true,
  "data": [{"id": "...", "name": "...", "code": "...", "status": "ACTIVE", "...": "..."}],
  "meta": {"page": 1, "page_size": 20, "total_items": 3, "total_pages": 1}
}
```

## Errors (`app/core/exceptions.py` + `app/core/error_handlers.py`)

Every error response — regardless of cause — is shaped identically:

```json
{"success": false, "error": {"code": "FORBIDDEN", "message": "...", "request_id": "..."}}
```

`AppError` is the base domain exception; each subclass fixes an HTTP status and a stable `code`:

| Exception | Status | Code |
|---|---|---|
| `AppError` (base / generic) | 400 | `BAD_REQUEST` |
| `UnauthorizedError` | 401 | `UNAUTHORIZED` |
| `ForbiddenError` | 403 | `FORBIDDEN` |
| `NotFoundError` | 404 | `NOT_FOUND` |
| `ConflictError` | 409 | `CONFLICT` |
| `ValidationAppError` | 422 | `VALIDATION_ERROR` |

Services raise these directly (e.g. `tenant_service.create_tenant` raises `ConflictError` when
the code/slug is already taken; `dependencies.require_permission` raises `ForbiddenError`) —
routers never construct HTTP responses or status codes themselves; per `app/main.py`'s module
docstring, routers only parse/validate input, call a service, and shape the response.

`register_exception_handlers(app)` wires four handlers so *every* error path — domain, framework,
and unexpected — ends up in the same envelope:

- `AppError` → the envelope above, using the exception's own `status_code`/`code`/`message`.
- Starlette's `HTTPException` (raised by FastAPI/Starlette internals, e.g. 404 on an unmatched
  route, 405 on a wrong method) → mapped through a small status-to-code table
  (`401→UNAUTHORIZED`, `403→FORBIDDEN`, `404→NOT_FOUND`, `405→METHOD_NOT_ALLOWED`,
  `429→RATE_LIMITED`, anything else → generic `ERROR`), same envelope shape.
- `RequestValidationError` (Pydantic/FastAPI request parsing failures) → `422`,
  `code: "VALIDATION_ERROR"`, with the field-level Pydantic error list attached as an extra
  `"details"` key alongside the standard envelope.
- Any other unhandled `Exception` → `500`, `code: "INTERNAL_ERROR"`. The exception is always
  logged server-side with a full traceback (`logger.exception(...)`), but the message returned to
  the client is generic ("An unexpected error occurred.") unless `settings.debug` is true — stack
  traces are never exposed to a production client.

Every envelope carries `request_id`, pulled from `request.state.request_id` (set by
`RequestContextMiddleware`), so a client-reported error can be correlated to a specific
server-side log line.

## Authentication and permission-gated routes (`app/security/dependencies.py`)

Three dependencies cover the whole authorization surface; no route reimplements auth:

- **`get_current_user`** — reads the `Authorization: Bearer <token>` header (via FastAPI's
  `HTTPBearer(auto_error=False)`, so a missing header produces the standard `UnauthorizedError`
  envelope rather than FastAPI's default 403), decodes it as an `ACCESS` token, loads the `User`
  row, and rejects it if the user no longer exists or `status != ACTIVE`.
- **`require_authenticated_user`** — the primary dependency for anything that just needs "a
  logged-in user," building a full `SecurityContext` (roles, permission grants, scope) fresh from
  the database on every single request — deliberately not cached in the JWT — so that revoking a
  role or permission takes effect on the very next request rather than waiting for token
  expiry/refresh.
- **`require_permission(code)`** — a dependency *factory*. `Depends(require_permission("users.view"))`
  resolves the caller's `SecurityContext` and raises `ForbiddenError` (→ 403) unless
  `context.has_permission(code)` — i.e. the caller holds that permission code at *any* scope.
  This is coarse, route-level gating: "can this caller do this kind of thing at all."

For per-resource checks — "can this caller act on *this specific* organization unit's data," not
just "can they do this in general" — routes call
`app.services.authorization_service.authorize(session, context, code, resource_organization_unit_id)`
instead, which walks the resource's organization-unit ancestry and only succeeds if one of the
caller's grants covers it (PLATFORM/TENANT-level grants always cover everything; a
node-scoped grant covers only that node and its descendants). `require_permission` and
`authorize` are complementary, not redundant: list/create routes typically only need the coarse
check, while update/delete routes on a specific record may need both.

Every protected router follows the same shape — a permission-gated dependency injected as a
route parameter, with the underlying service doing the actual work:

```python
@router.get("", response_model=Page[TenantResponse])
async def list_tenants(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    _context: SecurityContext = Depends(require_permission("tenants.view")),
    session: AsyncSession = Depends(get_db),
):
    ...

@router.post("", response_model=SuccessResponse[TenantResponse], status_code=201)
async def create_tenant(
    payload: TenantCreateRequest,
    request: Request,
    context: SecurityContext = Depends(require_permission("tenants.create")),
    session: AsyncSession = Depends(get_db),
):
    ...
```

(`backend/app/api/v1/tenants.py`; `users.py`, `roles.py`, `permissions.py`, and `audit.py` are
structured identically — one permission code per route, generally named
`"<resource>.<view|create|update|delete>"`.) The unauthenticated routes are the small, explicit
set in `backend/app/api/v1/auth.py` — `login`, `refresh`, `logout`, `forgot-password`,
`reset-password` — plus `GET /auth/me`, which only requires `require_authenticated_user` (any
logged-in user can read their own identity/roles/permissions, no specific permission code
needed).

Creating/updating routes that mutate state also take a `Request` parameter purely to pass through
to the service layer for audit logging (IP address, user agent) via `app.services.audit_service`
— every mutation on a Phase 0 platform entity (tenant, user, role, permission set) writes an
`AuditEvent` in the same transaction as the mutation itself, not as an afterthought.
