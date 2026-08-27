import pytest

from tests.conftest import login_headers

pytestmark = pytest.mark.asyncio


async def test_authenticated_user_can_list_units(client, tenant_a_admin, ton_unit):
    headers = await login_headers(client, tenant_a_admin.email)
    response = await client.get("/api/v1/units", headers=headers)
    assert response.status_code == 200, response.text
    codes = [u["code"] for u in response.json()["data"]]
    assert "ton" in codes


async def test_organization_units_are_scoped_to_the_caller_tenant(
    client, tenant_a_admin, tenant_b_admin, tenant_a_plants
):
    headers_a = await login_headers(client, tenant_a_admin.email)
    response_a = await client.get("/api/v1/organization-units", headers=headers_a)
    assert response_a.status_code == 200, response_a.text
    names_a = {u["name"] for u in response_a.json()["data"]}
    assert names_a == {"Pampore Plant", "Pulwama Plant"}

    headers_b = await login_headers(client, tenant_b_admin.email)
    response_b = await client.get("/api/v1/organization-units", headers=headers_b)
    assert response_b.status_code == 200
    assert response_b.json()["data"] == []


async def test_platform_user_cannot_list_organization_units(client, super_admin):
    headers = await login_headers(client, super_admin.email)
    response = await client.get("/api/v1/organization-units", headers=headers)
    assert response.status_code == 403
