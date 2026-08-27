import pytest

from tests.conftest import login_headers

pytestmark = pytest.mark.asyncio


async def test_super_admin_can_create_tenant(client, super_admin):
    headers = await login_headers(client, super_admin.email)
    response = await client.post(
        "/api/v1/tenants",
        json={
            "name": "New Tenant",
            "code": "NEWCO",
            "slug": "newco",
            "admin_email": "admin@newco.example.com",
            "admin_password": "Password!123",
            "admin_first_name": "New",
            "admin_last_name": "Admin",
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text
    assert response.json()["data"]["code"] == "NEWCO"


async def test_tenant_admin_cannot_create_tenant(client, tenant_a_admin):
    headers = await login_headers(client, tenant_a_admin.email)
    response = await client.post(
        "/api/v1/tenants",
        json={
            "name": "New Tenant",
            "code": "NEWCO2",
            "slug": "newco2",
            "admin_email": "admin@newco2.example.com",
            "admin_password": "Password!123",
            "admin_first_name": "New",
            "admin_last_name": "Admin",
        },
        headers=headers,
    )
    assert response.status_code == 403


async def test_new_tenant_admin_can_login(client, super_admin):
    headers = await login_headers(client, super_admin.email)
    await client.post(
        "/api/v1/tenants",
        json={
            "name": "Another Co",
            "code": "ANOTHER",
            "slug": "another",
            "admin_email": "admin@another.example.com",
            "admin_password": "Password!123",
            "admin_first_name": "A",
            "admin_last_name": "B",
        },
        headers=headers,
    )
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@another.example.com", "password": "Password!123"},
    )
    assert login_response.status_code == 200


async def test_suspend_tenant(client, super_admin, tenant_a):
    headers = await login_headers(client, super_admin.email)
    response = await client.post(f"/api/v1/tenants/{tenant_a.id}/suspend", headers=headers)
    assert response.status_code == 200
    assert response.json()["data"]["status"] == "SUSPENDED"
