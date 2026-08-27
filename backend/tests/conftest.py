"""Shared pytest fixtures.

Tests run against an in-memory SQLite database (via StaticPool, so all connections in a test see
the same schema/data) rather than PostgreSQL, so the suite runs anywhere without a running
database server. This is safe because every model column uses SQLAlchemy 2.0's dialect-agnostic
`Uuid`/`JSON` types (see app/models/base.py) — the exact same model definitions run against
PostgreSQL in production.

Fixtures build the standard fixture set from Master Build Specification section 39: two tenants
(so cross-tenant tests have something to violate) and one user per system role.
"""

import os

# Must run before the first `from app...` import below, since `get_settings()` is `@lru_cache`d
# and resolved the first time any module calls it — which happens transitively as soon as
# `app.core.database`/`app.main` are imported. `RateLimitMiddleware` (app/middleware/rate_limit.py)
# is a single instance shared by the whole test session (the FastAPI `app` object is a
# module-level singleton), so its in-memory per-IP hit counter accumulates across every test that
# hits the API rather than resetting per-test. With a large enough suite run inside the default
# 60-second window, that legitimately trips the production rate limit (120/minute) — not a bug in
# the limiter, just not the traffic pattern it's meant to police. Raise it for test runs only.
os.environ.setdefault("RATE_LIMIT_PER_MINUTE", "100000")

from datetime import date  # noqa: E402

import pytest_asyncio  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

import app.models  # noqa: F401,E402  (populate Base.metadata)
from app.core.database import Base, get_db  # noqa: E402
from app.core.seed import MASTER_DATA_PERMISSION_CODES, MASTER_DATA_VIEW_ONLY_CODES  # noqa: E402
from app.main import app  # noqa: E402
from app.models.enums import OrganizationUnitType, TenantStatus, UserStatus  # noqa: E402
from app.models.fiscal_year import FiscalYear  # noqa: E402
from app.models.organization import OrganizationUnit  # noqa: E402
from app.models.rbac import Permission, Role, RolePermission, UserRole  # noqa: E402
from app.models.tenant import Tenant  # noqa: E402
from app.models.unit import Unit, UnitCategory  # noqa: E402
from app.models.user import User  # noqa: E402
from app.security.passwords import hash_password  # noqa: E402

SYSTEM_ROLE_PERMISSIONS = {
    "SUPER_ADMIN": [
        "dashboard.view",
        "users.view",
        "users.create",
        "users.update",
        "users.delete",
        "roles.view",
        "roles.create",
        "roles.update",
        "roles.delete",
        "permissions.view",
        "tenants.view",
        "tenants.create",
        "tenants.update",
        "tenants.delete",
        "settings.view",
        "settings.update",
        "audit.view",
        "documents.view",
        "documents.upload",
        "documents.delete",
        "weighbridge.view",
        "weighbridge.create",
        "weighbridge.update",
        "production.view",
        "production.create",
        "production.update",
    ]
    + MASTER_DATA_PERMISSION_CODES,
    "TENANT_ADMIN": [
        "dashboard.view",
        "users.view",
        "users.create",
        "users.update",
        "users.delete",
        "roles.view",
        "roles.create",
        "roles.update",
        "roles.delete",
        "permissions.view",
        "settings.view",
        "settings.update",
        "audit.view",
        "documents.view",
        "documents.upload",
        "documents.delete",
        "weighbridge.view",
        "weighbridge.create",
        "weighbridge.update",
        "production.view",
        "production.create",
        "production.update",
    ]
    + MASTER_DATA_PERMISSION_CODES,
    "MANAGER": [
        "dashboard.view",
        "users.view",
        "settings.view",
        "audit.view",
        "documents.view",
        "weighbridge.view",
        "weighbridge.create",
        "weighbridge.update",
        "production.view",
        "production.create",
        "production.update",
    ]
    + MASTER_DATA_PERMISSION_CODES,
    "OPERATOR": [
        "dashboard.view",
        "documents.view",
        "documents.upload",
        "weighbridge.view",
        "weighbridge.create",
        "weighbridge.update",
        "production.view",
        "production.create",
        "production.update",
    ]
    + MASTER_DATA_VIEW_ONLY_CODES,
    "VIEWER": [
        "dashboard.view",
        "documents.view",
        "weighbridge.view",
        "production.view",
    ]
    + MASTER_DATA_VIEW_ONLY_CODES,
}

ALL_PERMISSION_CODES = sorted(
    {code for codes in SYSTEM_ROLE_PERMISSIONS.values() for code in codes}
)

RAW_PASSWORD = "TestPassword!123"


@pytest_asyncio.fixture
async def engine():
    test_engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield test_engine
    await test_engine.dispose()


@pytest_asyncio.fixture
async def session_factory(engine):
    return async_sessionmaker(bind=engine, expire_on_commit=False)


@pytest_asyncio.fixture
async def db_session(session_factory) -> AsyncSession:
    async with session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def seed_permissions(db_session: AsyncSession) -> dict[str, Permission]:
    by_code = {}
    for code in ALL_PERMISSION_CODES:
        permission = Permission(code=code, description=code, module="test")
        db_session.add(permission)
        by_code[code] = permission
    await db_session.commit()
    return by_code


@pytest_asyncio.fixture
async def seed_roles(
    db_session: AsyncSession, seed_permissions: dict[str, Permission]
) -> dict[str, Role]:
    roles = {}
    for code, permission_codes in SYSTEM_ROLE_PERMISSIONS.items():
        role = Role(tenant_id=None, code=code, name=code.title(), is_system=True)
        db_session.add(role)
        await db_session.flush()
        for permission_code in permission_codes:
            db_session.add(
                RolePermission(role_id=role.id, permission_id=seed_permissions[permission_code].id)
            )
        roles[code] = role
    await db_session.commit()
    return roles


async def _make_tenant(db_session: AsyncSession, code: str) -> Tenant:
    tenant = Tenant(name=f"{code} Corp", code=code, slug=code.lower(), status=TenantStatus.ACTIVE)
    db_session.add(tenant)
    await db_session.commit()
    return tenant


@pytest_asyncio.fixture
async def tenant_a(db_session: AsyncSession) -> Tenant:
    return await _make_tenant(db_session, "TENANTA")


@pytest_asyncio.fixture
async def tenant_b(db_session: AsyncSession) -> Tenant:
    return await _make_tenant(db_session, "TENANTB")


async def _make_user(
    db_session: AsyncSession,
    *,
    tenant_id,
    email: str,
    role: Role,
    is_platform_user: bool = False,
    organization_unit_id=None,
) -> User:
    user = User(
        tenant_id=tenant_id,
        email=email,
        password_hash=hash_password(RAW_PASSWORD),
        first_name="Test",
        last_name="User",
        status=UserStatus.ACTIVE,
        is_verified=True,
        is_platform_user=is_platform_user,
    )
    db_session.add(user)
    await db_session.flush()
    db_session.add(
        UserRole(user_id=user.id, role_id=role.id, organization_unit_id=organization_unit_id)
    )
    await db_session.commit()
    return user


@pytest_asyncio.fixture
async def super_admin(db_session: AsyncSession, seed_roles: dict[str, Role]) -> User:
    return await _make_user(
        db_session,
        tenant_id=None,
        email="superadmin@platform.example.com",
        role=seed_roles["SUPER_ADMIN"],
        is_platform_user=True,
    )


@pytest_asyncio.fixture
async def tenant_a_admin(
    db_session: AsyncSession, tenant_a: Tenant, seed_roles: dict[str, Role]
) -> User:
    return await _make_user(
        db_session,
        tenant_id=tenant_a.id,
        email="admin@tenanta.example.com",
        role=seed_roles["TENANT_ADMIN"],
    )


@pytest_asyncio.fixture
async def tenant_b_admin(
    db_session: AsyncSession, tenant_b: Tenant, seed_roles: dict[str, Role]
) -> User:
    return await _make_user(
        db_session,
        tenant_id=tenant_b.id,
        email="admin@tenantb.example.com",
        role=seed_roles["TENANT_ADMIN"],
    )


@pytest_asyncio.fixture
async def tenant_a_viewer(
    db_session: AsyncSession, tenant_a: Tenant, seed_roles: dict[str, Role]
) -> User:
    return await _make_user(
        db_session,
        tenant_id=tenant_a.id,
        email="viewer@tenanta.example.com",
        role=seed_roles["VIEWER"],
    )


@pytest_asyncio.fixture
async def tenant_a_plants(
    db_session: AsyncSession, tenant_a: Tenant
) -> dict[str, OrganizationUnit]:
    plant_1 = OrganizationUnit(
        tenant_id=tenant_a.id,
        name="Pampore Plant",
        code="PAMP",
        unit_type=OrganizationUnitType.PLANT,
    )
    plant_2 = OrganizationUnit(
        tenant_id=tenant_a.id,
        name="Pulwama Plant",
        code="PULW",
        unit_type=OrganizationUnitType.PLANT,
    )
    db_session.add_all([plant_1, plant_2])
    await db_session.commit()
    return {"pampore": plant_1, "pulwama": plant_2}


@pytest_asyncio.fixture
async def tenant_a_plant_manager(
    db_session: AsyncSession,
    tenant_a: Tenant,
    seed_roles: dict[str, Role],
    tenant_a_plants: dict[str, OrganizationUnit],
) -> User:
    """A MANAGER user scoped only to the Pampore plant (not Pulwama)."""
    return await _make_user(
        db_session,
        tenant_id=tenant_a.id,
        email="manager@tenanta.example.com",
        role=seed_roles["MANAGER"],
        organization_unit_id=tenant_a_plants["pampore"].id,
    )


@pytest_asyncio.fixture
async def tenant_a_operator(
    db_session: AsyncSession,
    tenant_a: Tenant,
    seed_roles: dict[str, Role],
    tenant_a_plants: dict[str, OrganizationUnit],
) -> User:
    """An OPERATOR user scoped only to the Pampore plant (not Pulwama) — mirrors
    `tenant_a_plant_manager` but for the role that actually runs the weighbridge day to day."""
    return await _make_user(
        db_session,
        tenant_id=tenant_a.id,
        email="operator@tenanta.example.com",
        role=seed_roles["OPERATOR"],
        organization_unit_id=tenant_a_plants["pampore"].id,
    )


@pytest_asyncio.fixture
async def tenant_a_fiscal_year(db_session: AsyncSession, tenant_a: Tenant) -> FiscalYear:
    fiscal_year = FiscalYear(
        tenant_id=tenant_a.id,
        code="2026-27",
        start_date=date(2026, 4, 1),
        end_date=date(2027, 3, 31),
        is_active=True,
    )
    db_session.add(fiscal_year)
    await db_session.commit()
    return fiscal_year


@pytest_asyncio.fixture
async def ton_unit(db_session: AsyncSession) -> Unit:
    category = UnitCategory(code="MASS", name="Mass")
    db_session.add(category)
    await db_session.flush()
    unit = Unit(category_id=category.id, code="ton", name="Metric Ton", symbol="t")
    db_session.add(unit)
    await db_session.commit()
    return unit


@pytest_asyncio.fixture
async def client(session_factory):
    async def _override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


async def login_headers(client: AsyncClient, email: str) -> dict[str, str]:
    response = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": RAW_PASSWORD}
    )
    assert response.status_code == 200, response.text
    token = response.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}
