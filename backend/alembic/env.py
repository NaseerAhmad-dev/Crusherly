import asyncio
from logging.config import fileConfig

from sqlalchemy import Enum as SAEnum
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# Ensure every model module is imported so Base.metadata is fully populated for autogenerate.
from app.core.config import get_settings
from app.core.database import Base
from app.models.base import UTCDateTime
import app.models  # noqa: F401

config = context.config

# Postgres ENUM types shared by more than one table (autogenerate emits `CREATE TYPE` per
# `op.create_table()` call, which fails with "type already exists" the second time a migration
# touches a second table using the same enum — see `master_data_status`, shared by `Location`
# since Phase 0 and by every `CodedMasterDataMixin` model since Phase 1). Any name listed here is
# always rendered with `create_type=False`, since the type is guaranteed to already exist by the
# time a *second* table's migration runs.
_SHARED_ENUM_TYPE_NAMES = {"master_data_status"}


def render_item(type_, obj, autogen_context):
    """Render our custom `UTCDateTime` TypeDecorator as the plain `sa.DateTime(timezone=True)`
    it wraps, instead of alembic's default `app.models.base.UTCDateTime(...)` fallback repr —
    which would leave the generated migration referencing application code it never imports.
    The column's actual DDL type is identical either way (`UTCDateTime.impl` *is*
    `DateTime(timezone=True)`); only the Python-side read behavior differs, and that lives in the
    ORM layer, not the schema.

    Also renders any enum in `_SHARED_ENUM_TYPE_NAMES` as `postgresql.ENUM(..., create_type=False)`
    — tried the generic, dialect-agnostic `sa.Enum(..., create_type=False)` first, and it does NOT
    suppress `CREATE TYPE` during `op.create_table()` (confirmed empirically: the migration still
    failed with `DuplicateObjectError: type "master_data_status" already exists` on the second
    table with `create_type=False` present in the rendered code). `create_type` is only actually
    honored on the Postgres-dialect-specific `postgresql.ENUM` class. Without this, every migration
    that creates a second table using `master_data_status` would try to `CREATE TYPE` it again and
    fail — it's shared by `Location` since Phase 0 and by every `CodedMasterDataMixin` model since
    Phase 1.
    """
    if type_ == "type" and isinstance(obj, UTCDateTime):
        return "sa.DateTime(timezone=True)"
    if type_ == "type" and isinstance(obj, SAEnum) and obj.name in _SHARED_ENUM_TYPE_NAMES:
        autogen_context.imports.add("from sqlalchemy.dialects import postgresql")
        values = ", ".join(repr(v) for v in obj.enums)
        return f"postgresql.ENUM({values}, name={obj.name!r}, create_type=False)"
    return False


if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

settings = get_settings()
config.set_main_option("sqlalchemy.url", settings.database_url)


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        render_item=render_item,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        render_item=render_item,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
