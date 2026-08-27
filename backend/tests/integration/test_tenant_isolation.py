"""Mandatory tenant isolation tests (Master Build Specification section 12)."""

import pytest

from tests.conftest import login_headers

pytestmark = pytest.mark.asyncio


async def _create_tenant_b_user(client, tenant_b_admin) -> str:
    headers = await login_headers(client, tenant_b_admin.email)
    response = await client.post(
        "/api/v1/users",
        json={
            "email": "victim@tenantb.example.com",
            "password": "SomePassword!123",
            "first_name": "Victim",
            "last_name": "User",
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()["data"]["id"]


async def test_tenant_a_cannot_read_tenant_b_user(client, tenant_a_admin, tenant_b_admin):
    victim_id = await _create_tenant_b_user(client, tenant_b_admin)

    headers = await login_headers(client, tenant_a_admin.email)
    response = await client.get(f"/api/v1/users/{victim_id}", headers=headers)
    assert response.status_code == 404  # not "403" — tenant A must not even learn it exists


async def test_tenant_a_cannot_update_tenant_b_user(client, tenant_a_admin, tenant_b_admin):
    victim_id = await _create_tenant_b_user(client, tenant_b_admin)

    headers = await login_headers(client, tenant_a_admin.email)
    response = await client.patch(
        f"/api/v1/users/{victim_id}", json={"first_name": "Hacked"}, headers=headers
    )
    assert response.status_code == 404


async def test_tenant_a_cannot_deactivate_tenant_b_user(client, tenant_a_admin, tenant_b_admin):
    victim_id = await _create_tenant_b_user(client, tenant_b_admin)

    headers = await login_headers(client, tenant_a_admin.email)
    response = await client.delete(f"/api/v1/users/{victim_id}", headers=headers)
    assert response.status_code == 404


async def test_tenant_a_admin_does_not_see_tenant_b_users_in_list(
    client, tenant_a_admin, tenant_b_admin
):
    await _create_tenant_b_user(client, tenant_b_admin)

    headers = await login_headers(client, tenant_a_admin.email)
    response = await client.get("/api/v1/users", headers=headers)
    assert response.status_code == 200
    emails = [u["email"] for u in response.json()["data"]]
    assert "victim@tenantb.example.com" not in emails


async def test_changing_id_in_request_cannot_bypass_tenant_isolation(
    client, tenant_a_admin, tenant_b_admin
):
    """Guessing/enumerating another tenant's resource ID must not leak or allow mutation."""
    victim_id = await _create_tenant_b_user(client, tenant_b_admin)

    headers = await login_headers(client, tenant_a_admin.email)
    get_response = await client.get(f"/api/v1/users/{victim_id}", headers=headers)
    patch_response = await client.patch(
        f"/api/v1/users/{victim_id}", json={"last_name": "Pwned"}, headers=headers
    )
    delete_response = await client.delete(f"/api/v1/users/{victim_id}", headers=headers)

    assert get_response.status_code == 404
    assert patch_response.status_code == 404
    assert delete_response.status_code == 404


async def test_plant_scoped_user_cannot_access_another_plant(
    client, db_session, tenant_a_plant_manager, tenant_a_plants
):
    from app.services.authorization_service import is_authorized
    from app.services.security_context_service import build_security_context

    context = await build_security_context(db_session, tenant_a_plant_manager)
    assert await is_authorized(
        db_session,
        context,
        "users.view",
        resource_organization_unit_id=tenant_a_plants["pampore"].id,
    )
    assert not await is_authorized(
        db_session,
        context,
        "users.view",
        resource_organization_unit_id=tenant_a_plants["pulwama"].id,
    )
