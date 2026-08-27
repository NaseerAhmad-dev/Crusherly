"""Async SQLAlchemy engine/session management."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings

settings = get_settings()

_is_sqlite = "sqlite" in settings.database_url

_engine_kwargs: dict = {"echo": False, "pool_pre_ping": True}
if _is_sqlite:
    _engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    _engine_kwargs["pool_size"] = settings.db_pool_size
    _engine_kwargs["max_overflow"] = settings.db_max_overflow

engine = create_async_engine(settings.database_url, **_engine_kwargs)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Base class for all ORM models.

    `eager_defaults` makes UPDATE/INSERT fetch server-computed columns (e.g. the
    `onupdate=func.now()` timestamp in TimestampMixin) via RETURNING during the flush,
    instead of leaving them expired. Without this, reading such a column right after a
    flush/commit — e.g. serializing the ORM object into a response schema — triggers an
    implicit lazy-load, which raises MissingGreenlet because it happens outside the
    async session's IO-bridging context.
    """

    __mapper_args__ = {"eager_defaults": True}


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding a request-scoped async session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
