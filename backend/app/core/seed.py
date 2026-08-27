"""Idempotent seed script for local/dev environments.

Run with:

    python -m app.core.seed

Seeds:
- The fixed permission set (Master Build Specification section 9)
- The seven system roles (SUPER_ADMIN .. VIEWER), each pre-wired with a sensible permission set
- A platform SUPER_ADMIN user (email/password from SEED_SUPER_ADMIN_EMAIL/PASSWORD, defaulting
  to a clearly-fake local-only credential)
- A demo tenant plus one user per non-platform role (TENANT_ADMIN, MANAGER, OPERATOR,
  ACCOUNTANT, STOREKEEPER, VIEWER), tenant-wide scoped, for trying out role differences locally
- A base UnitCategory/Unit set (kg, ton, litre, km, hour, piece, set) with valid conversions

Safe to run multiple times: every insert first checks for an existing row by its natural key.
"""

import asyncio
import os
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import AsyncSessionLocal
from app.models.enums import TenantStatus, UserStatus
from app.models.fiscal_year import FiscalYear
from app.models.rbac import Permission, Role, RolePermission, UserRole
from app.models.tenant import Tenant
from app.models.unit import Unit, UnitCategory, UnitConversion
from app.models.user import User
from app.repositories import (
    fiscal_year_repository,
    permission_repository,
    role_repository,
    tenant_repository,
    user_repository,
)
from app.security.passwords import hash_password

PERMISSIONS: list[tuple[str, str, str]] = [
    ("dashboard.view", "View dashboard", "platform"),
    ("users.view", "View users", "identity"),
    ("users.create", "Create users", "identity"),
    ("users.update", "Update users", "identity"),
    ("users.delete", "Deactivate users", "identity"),
    ("roles.view", "View roles", "authz"),
    ("roles.create", "Create roles", "authz"),
    ("roles.update", "Update roles", "authz"),
    ("roles.delete", "Delete roles", "authz"),
    ("permissions.view", "View permissions", "authz"),
    ("tenants.view", "View tenants", "tenancy"),
    ("tenants.create", "Create tenants", "tenancy"),
    ("tenants.update", "Update tenants", "tenancy"),
    ("tenants.delete", "Delete tenants", "tenancy"),
    ("settings.view", "View settings", "platform"),
    ("settings.update", "Update settings", "platform"),
    ("audit.view", "View audit log", "platform"),
    ("documents.view", "View documents", "documents"),
    ("documents.upload", "Upload documents", "documents"),
    ("documents.delete", "Delete documents", "documents"),
    ("weighbridge.view", "View weighbridge tickets", "weighbridge"),
    ("weighbridge.create", "Create weighbridge tickets", "weighbridge"),
    ("weighbridge.update", "Complete or cancel weighbridge tickets", "weighbridge"),
    ("production.view", "View production entries", "production"),
    ("production.create", "Create production entries", "production"),
    ("production.update", "Submit or cancel production entries", "production"),
]

# Master-data entities (Master Build Specification "PHASE 1 — Master Data Foundation") all share
# the exact same three-permission shape (view/create/update via app/api/v1/master_data_router.py),
# so their permission codes are generated rather than hand-typed 30 times over.
MASTER_DATA_ENTITIES: list[tuple[str, str]] = [
    ("material_categories", "material categories"),
    ("materials", "materials"),
    ("product_categories", "product categories"),
    ("products", "products"),
    ("tax_codes", "tax codes"),
    ("payment_terms", "payment terms"),
    ("customers", "customers"),
    ("suppliers", "suppliers"),
    ("vehicles", "vehicles"),
    ("drivers", "drivers"),
]
MASTER_DATA_PERMISSION_CODES: list[str] = []
for _prefix, _label in MASTER_DATA_ENTITIES:
    PERMISSIONS.append((f"{_prefix}.view", f"View {_label}", "master_data"))
    PERMISSIONS.append((f"{_prefix}.create", f"Create {_label}", "master_data"))
    PERMISSIONS.append((f"{_prefix}.update", f"Update or deactivate {_label}", "master_data"))
    MASTER_DATA_PERMISSION_CODES.extend(
        [f"{_prefix}.view", f"{_prefix}.create", f"{_prefix}.update"]
    )
MASTER_DATA_VIEW_ONLY_CODES: list[str] = [f"{prefix}.view" for prefix, _ in MASTER_DATA_ENTITIES]

# code -> (name, description, permission codes)
SYSTEM_ROLES: dict[str, tuple[str, str, list[str]]] = {
    "SUPER_ADMIN": ("Super Admin", "Full platform access.", [p[0] for p in PERMISSIONS]),
    "TENANT_ADMIN": (
        "Tenant Admin",
        "Full administrative access within a tenant.",
        [
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
    ),
    "MANAGER": (
        "Manager",
        "Operational management within assigned scope.",
        [
            "dashboard.view",
            "users.view",
            "settings.view",
            "audit.view",
            "documents.view",
            "documents.upload",
            "weighbridge.view",
            "weighbridge.create",
            "weighbridge.update",
            "production.view",
            "production.create",
            "production.update",
        ]
        + MASTER_DATA_PERMISSION_CODES,
    ),
    "OPERATOR": (
        "Operator",
        "Day-to-day operational access within assigned scope.",
        [
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
    ),
    "ACCOUNTANT": (
        "Accountant",
        "Financial data access within assigned scope.",
        [
            "dashboard.view",
            "documents.view",
            "documents.upload",
            "weighbridge.view",
            "production.view",
        ]
        + MASTER_DATA_VIEW_ONLY_CODES,
    ),
    "STOREKEEPER": (
        "Storekeeper",
        "Inventory/store access within assigned scope.",
        [
            "dashboard.view",
            "documents.view",
            "documents.upload",
            "weighbridge.view",
            "production.view",
        ]
        + MASTER_DATA_VIEW_ONLY_CODES,
    ),
    "VIEWER": (
        "Viewer",
        "Read-only access within assigned scope.",
        ["dashboard.view", "documents.view", "weighbridge.view", "production.view"]
        + MASTER_DATA_VIEW_ONLY_CODES,
    ),
}

UNITS: list[tuple[str, str, list[tuple[str, str, str]], list[tuple[str, str, float]]]] = [
    (
        "MASS",
        "Mass",
        [("kg", "Kilogram", "kg"), ("ton", "Metric Ton", "t")],
        [("kg", "ton", 0.001), ("ton", "kg", 1000.0)],
    ),
    ("VOLUME", "Volume", [("litre", "Litre", "L")], []),
    ("DISTANCE", "Distance", [("km", "Kilometre", "km")], []),
    ("TIME", "Time", [("hour", "Hour", "hr")], []),
    ("COUNT", "Count", [("piece", "Piece", "pc"), ("set", "Set", "set")], []),
]


async def seed_permissions(session) -> dict[str, Permission]:
    by_code: dict[str, Permission] = {}
    for code, description, module in PERMISSIONS:
        existing = await permission_repository.get_by_code(session, code)
        if existing is None:
            existing = Permission(code=code, description=description, module=module)
            session.add(existing)
            await session.flush()
        by_code[code] = existing
    return by_code


async def seed_roles(session, permissions_by_code: dict[str, Permission]) -> None:
    for code, (name, description, permission_codes) in SYSTEM_ROLES.items():
        result = await session.execute(
            select(Role)
            .where(Role.code == code, Role.tenant_id.is_(None))
            .options(selectinload(Role.role_permissions))
        )
        role = result.scalar_one_or_none()
        if role is None:
            role = Role(
                tenant_id=None, code=code, name=name, description=description, is_system=True
            )
            session.add(role)
            await session.flush()
            existing_codes: set[str] = set()
        else:
            existing_codes = {rp.permission_id for rp in role.role_permissions}

        for permission_code in permission_codes:
            permission = permissions_by_code[permission_code]
            if permission.id in existing_codes:
                continue
            session.add(RolePermission(role_id=role.id, permission_id=permission.id))
        await session.flush()


async def seed_super_admin(session) -> None:
    email = os.getenv("SEED_SUPER_ADMIN_EMAIL", "superadmin@stonecrusher.example.com")
    password = os.getenv("SEED_SUPER_ADMIN_PASSWORD", "ChangeMe!12345")

    existing = await user_repository.get_by_email(session, email)
    if existing is not None:
        return

    user = User(
        tenant_id=None,
        email=email.lower(),
        password_hash=hash_password(password),
        first_name="Super",
        last_name="Admin",
        status=UserStatus.ACTIVE,
        is_verified=True,
        is_platform_user=True,
    )
    session.add(user)
    await session.flush()

    role = await role_repository.get_by_code(session, "SUPER_ADMIN", tenant_id=None)
    session.add(UserRole(user_id=user.id, role_id=role.id))
    await session.flush()


DEMO_TENANT = {
    "name": "Demo Stone Crushers",
    "code": "DEMO",
    "slug": "demo",
    "timezone": "Asia/Kolkata",
    "currency": "INR",
}

# role code -> (email local-part, first_name, last_name)
DEMO_USERS: dict[str, tuple[str, str, str]] = {
    "TENANT_ADMIN": ("admin", "Demo", "Admin"),
    "MANAGER": ("manager", "Demo", "Manager"),
    "OPERATOR": ("operator", "Demo", "Operator"),
    "ACCOUNTANT": ("accountant", "Demo", "Accountant"),
    "STOREKEEPER": ("storekeeper", "Demo", "Storekeeper"),
    "VIEWER": ("viewer", "Demo", "Viewer"),
}
DEMO_USER_EMAIL_DOMAIN = "demo.stonecrusher.example.com"
DEMO_USER_PASSWORD = "Demo!12345"


async def seed_fiscal_year(session, tenant: Tenant) -> None:
    """One active April-March fiscal year (the Indian convention, matching DEMO_TENANT's
    timezone/currency) so weighbridge tickets — and any future document-numbered business
    record — have something to number against out of the box."""
    existing = await fiscal_year_repository.get_active_for_tenant(session, tenant.id)
    if existing is not None:
        return

    today = date.today()
    start_year = today.year if today.month >= 4 else today.year - 1
    fiscal_year_repository.add(
        session,
        FiscalYear(
            tenant_id=tenant.id,
            code=f"{start_year}-{str(start_year + 1)[-2:]}",
            start_date=date(start_year, 4, 1),
            end_date=date(start_year + 1, 3, 31),
            is_active=True,
        ),
    )
    await session.flush()


async def seed_demo_tenant_and_users(session) -> None:
    """One user per non-platform role, tenant-wide scoped (no organization_unit_id — see
    security_context_service.build_security_context), so their permission differences are
    visible immediately without also having to set up plants/sites first."""
    tenant = await tenant_repository.get_by_code_or_slug(
        session, DEMO_TENANT["code"], DEMO_TENANT["slug"]
    )
    if tenant is None:
        tenant = Tenant(status=TenantStatus.ACTIVE, **DEMO_TENANT)
        session.add(tenant)
        await session.flush()

    await seed_fiscal_year(session, tenant)

    for role_code, (local_part, first_name, last_name) in DEMO_USERS.items():
        email = f"{local_part}@{DEMO_USER_EMAIL_DOMAIN}"
        if await user_repository.get_by_email(session, email) is not None:
            continue

        user = User(
            tenant_id=tenant.id,
            email=email,
            password_hash=hash_password(DEMO_USER_PASSWORD),
            first_name=first_name,
            last_name=last_name,
            status=UserStatus.ACTIVE,
            is_verified=True,
        )
        session.add(user)
        await session.flush()

        role = await role_repository.get_by_code(session, role_code, tenant_id=None)
        session.add(UserRole(user_id=user.id, role_id=role.id))
        await session.flush()


async def seed_units(session) -> None:
    for category_code, category_name, units, conversions in UNITS:
        result = await session.execute(
            select(UnitCategory).where(UnitCategory.code == category_code)
        )
        category = result.scalar_one_or_none()
        if category is None:
            category = UnitCategory(code=category_code, name=category_name)
            session.add(category)
            await session.flush()

        unit_ids: dict[str, object] = {}
        for unit_code, unit_name, symbol in units:
            existing = await session.execute(select(Unit).where(Unit.code == unit_code))
            unit = existing.scalar_one_or_none()
            if unit is None:
                unit = Unit(category_id=category.id, code=unit_code, name=unit_name, symbol=symbol)
                session.add(unit)
                await session.flush()
            unit_ids[unit_code] = unit.id

        for from_code, to_code, factor in conversions:
            existing = await session.execute(
                select(UnitConversion).where(
                    UnitConversion.from_unit_id == unit_ids[from_code],
                    UnitConversion.to_unit_id == unit_ids[to_code],
                )
            )
            if existing.scalar_one_or_none() is None:
                session.add(
                    UnitConversion(
                        from_unit_id=unit_ids[from_code],
                        to_unit_id=unit_ids[to_code],
                        factor=factor,
                    )
                )
        await session.flush()


async def run() -> None:
    async with AsyncSessionLocal() as session:
        permissions_by_code = await seed_permissions(session)
        await seed_roles(session, permissions_by_code)
        await seed_super_admin(session)
        await seed_demo_tenant_and_users(session)
        await seed_units(session)
        await session.commit()
    print("Seed complete.")


if __name__ == "__main__":
    asyncio.run(run())
