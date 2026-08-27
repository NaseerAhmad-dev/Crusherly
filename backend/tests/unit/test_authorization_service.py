"""Scope authorization: RBAC answers 'what', this answers 'where' (spec section 10/12)."""

import pytest

from app.services.authorization_service import is_authorized
from app.services.security_context_service import build_security_context

pytestmark = pytest.mark.asyncio


async def test_plant_scoped_manager_authorized_for_own_plant(
    db_session, tenant_a_plant_manager, tenant_a_plants
):
    context = await build_security_context(db_session, tenant_a_plant_manager)
    assert await is_authorized(
        db_session,
        context,
        "users.view",
        resource_organization_unit_id=tenant_a_plants["pampore"].id,
    )


async def test_plant_scoped_manager_denied_for_other_plant(
    db_session, tenant_a_plant_manager, tenant_a_plants
):
    context = await build_security_context(db_session, tenant_a_plant_manager)
    assert not await is_authorized(
        db_session,
        context,
        "users.view",
        resource_organization_unit_id=tenant_a_plants["pulwama"].id,
    )


async def test_tenant_admin_authorized_for_every_plant(db_session, tenant_a_admin, tenant_a_plants):
    context = await build_security_context(db_session, tenant_a_admin)
    assert await is_authorized(
        db_session,
        context,
        "users.view",
        resource_organization_unit_id=tenant_a_plants["pampore"].id,
    )
    assert await is_authorized(
        db_session,
        context,
        "users.view",
        resource_organization_unit_id=tenant_a_plants["pulwama"].id,
    )


async def test_platform_super_admin_authorized_everywhere(db_session, super_admin, tenant_a_plants):
    context = await build_security_context(db_session, super_admin)
    assert await is_authorized(
        db_session,
        context,
        "users.view",
        resource_organization_unit_id=tenant_a_plants["pampore"].id,
    )


async def test_missing_permission_denied_regardless_of_scope(
    db_session, tenant_a_plant_manager, tenant_a_plants
):
    context = await build_security_context(db_session, tenant_a_plant_manager)
    assert not await is_authorized(
        db_session,
        context,
        "tenants.delete",
        resource_organization_unit_id=tenant_a_plants["pampore"].id,
    )


async def test_user_with_no_roles_has_no_grants(db_session, tenant_a):
    from app.models.enums import UserStatus
    from app.models.user import User
    from app.security.passwords import hash_password

    lonely_user = User(
        tenant_id=tenant_a.id,
        email="lonely@tenanta.example.com",
        password_hash=hash_password("whatever12345"),
        first_name="Lonely",
        last_name="User",
        status=UserStatus.ACTIVE,
        is_verified=True,
    )
    db_session.add(lonely_user)
    await db_session.commit()

    context = await build_security_context(db_session, lonely_user)
    assert context.grants == []
    assert not context.has_permission("dashboard.view")
