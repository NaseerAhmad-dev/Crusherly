"""FastAPI application entrypoint.

Backend request flow (Master Build Specification section 4):

    API -> Authentication -> Authorization -> Service -> Repository -> Database

No business logic lives in routers; routers parse/validate input, call a service, and shape the
response.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.error_handlers import register_exception_handlers
from app.core.logging_config import configure_logging
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.request_context import RequestContextMiddleware
from app.middleware.security_headers import SecurityHeadersMiddleware

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.project_name,
        version="0.1.0",
        docs_url=f"{settings.api_v1_prefix}/docs",
        redoc_url=f"{settings.api_v1_prefix}/redoc",
        openapi_url=f"{settings.api_v1_prefix}/openapi.json",
        lifespan=lifespan,
    )

    # Order matters: outermost middleware runs first on the way in / last on the way out.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(RequestContextMiddleware)

    register_exception_handlers(app)

    app.include_router(api_router, prefix=settings.api_v1_prefix)

    @app.get("/health", tags=["observability"])
    async def health() -> dict:
        """Liveness probe: process is up. Does not touch the database."""
        return {"status": "ok"}

    @app.get("/ready", tags=["observability"])
    async def ready() -> dict:
        """Readiness probe: the app can actually serve traffic (database reachable)."""
        from sqlalchemy import text

        from app.core.database import engine

        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
        except Exception as exc:  # pragma: no cover - exercised via integration/infra tests
            return {"status": "not_ready", "detail": str(exc)}
        return {"status": "ready"}

    return app


app = create_app()
