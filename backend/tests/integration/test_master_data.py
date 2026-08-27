"""Tests the generic master-data CRUD pattern (app/repositories/master_data_repository.py,
app/services/master_data_service.py, app/api/v1/master_data_router.py) thoroughly through one
representative entity (`material-categories`), then a lighter smoke test per remaining entity to
confirm each is actually wired up correctly — since the whole point of the generic pattern is that
adding an entity is router instantiation, not new logic, a full CRUD test suite per entity would
mostly be testing the same generic code ten times over.
"""

import pytest

from tests.conftest import login_headers

pytestmark = pytest.mark.asyncio

# (endpoint prefix, a valid create payload) for every generic master-data entity.
SMOKE_TEST_ENTITIES = [
    ("material-categories", {"code": "AGG", "name": "Aggregates"}),
    ("product-categories", {"code": "FIN", "name": "Finished Goods"}),
    ("tax-codes", {"code": "GST18", "name": "GST 18%"}),
    ("payment-terms", {"code": "NET30", "name": "Net 30 Days"}),
    ("customers", {"code": "CUST001", "name": "Kashmir Aggregates Pvt Ltd"}),
    ("suppliers", {"code": "SUPP001", "name": "Himalayan Stone Suppliers"}),
    ("vehicles", {"code": "JK01AB1234", "name": "Tipper Truck 1"}),
    ("drivers", {"code": "DL-12345", "name": "Rashid Ahmad"}),
]


async def test_full_crud_lifecycle_for_one_entity(client, tenant_a_admin):
    headers = await login_headers(client, tenant_a_admin.email)

    create_response = await client.post(
        "/api/v1/material-categories",
        json={"code": "AGG", "name": "Aggregates", "description": "Graded stone aggregate"},
        headers=headers,
    )
    assert create_response.status_code == 201, create_response.text
    item = create_response.json()["data"]
    assert item["code"] == "AGG"
    assert item["status"] == "ACTIVE"
    item_id = item["id"]

    get_response = await client.get(f"/api/v1/material-categories/{item_id}", headers=headers)
    assert get_response.status_code == 200
    assert get_response.json()["data"]["name"] == "Aggregates"

    update_response = await client.patch(
        f"/api/v1/material-categories/{item_id}",
        json={"description": "Updated description"},
        headers=headers,
    )
    assert update_response.status_code == 200, update_response.text
    assert update_response.json()["data"]["description"] == "Updated description"
    assert update_response.json()["data"]["name"] == "Aggregates"  # unset fields untouched

    list_response = await client.get("/api/v1/material-categories", headers=headers)
    assert list_response.status_code == 200
    assert list_response.json()["meta"]["total_items"] == 1

    search_response = await client.get(
        "/api/v1/material-categories", params={"search": "aggr"}, headers=headers
    )
    assert search_response.json()["meta"]["total_items"] == 1
    no_match_response = await client.get(
        "/api/v1/material-categories", params={"search": "nonexistent"}, headers=headers
    )
    assert no_match_response.json()["meta"]["total_items"] == 0

    deactivate_response = await client.post(
        f"/api/v1/material-categories/{item_id}/deactivate", headers=headers
    )
    assert deactivate_response.status_code == 200
    assert deactivate_response.json()["data"]["status"] == "INACTIVE"

    second_deactivate = await client.post(
        f"/api/v1/material-categories/{item_id}/deactivate", headers=headers
    )
    assert second_deactivate.status_code == 409


async def test_duplicate_code_in_same_tenant_is_rejected(client, tenant_a_admin):
    headers = await login_headers(client, tenant_a_admin.email)
    payload = {"code": "DUP", "name": "First"}

    first = await client.post("/api/v1/material-categories", json=payload, headers=headers)
    assert first.status_code == 201

    second = await client.post(
        "/api/v1/material-categories", json={"code": "DUP", "name": "Second"}, headers=headers
    )
    assert second.status_code == 409


async def test_same_code_is_allowed_across_different_tenants(
    client, tenant_a_admin, tenant_b_admin
):
    payload = {"code": "SHARED", "name": "Shared Code"}

    headers_a = await login_headers(client, tenant_a_admin.email)
    response_a = await client.post("/api/v1/material-categories", json=payload, headers=headers_a)
    assert response_a.status_code == 201

    headers_b = await login_headers(client, tenant_b_admin.email)
    response_b = await client.post("/api/v1/material-categories", json=payload, headers=headers_b)
    assert response_b.status_code == 201


async def test_list_is_scoped_to_the_caller_tenant(client, tenant_a_admin, tenant_b_admin):
    headers_a = await login_headers(client, tenant_a_admin.email)
    await client.post(
        "/api/v1/material-categories", json={"code": "A", "name": "A"}, headers=headers_a
    )

    headers_b = await login_headers(client, tenant_b_admin.email)
    list_response = await client.get("/api/v1/material-categories", headers=headers_b)
    assert list_response.json()["meta"]["total_items"] == 0


async def test_viewer_cannot_create_but_can_list(client, tenant_a_viewer):
    headers = await login_headers(client, tenant_a_viewer.email)

    create_response = await client.post(
        "/api/v1/material-categories", json={"code": "X", "name": "X"}, headers=headers
    )
    assert create_response.status_code == 403

    list_response = await client.get("/api/v1/material-categories", headers=headers)
    assert list_response.status_code == 200


async def test_material_extends_the_generic_shape_with_category_and_unit(
    client, tenant_a_admin, ton_unit
):
    headers = await login_headers(client, tenant_a_admin.email)

    category_response = await client.post(
        "/api/v1/material-categories", json={"code": "RAW", "name": "Raw Material"}, headers=headers
    )
    category_id = category_response.json()["data"]["id"]

    material_response = await client.post(
        "/api/v1/materials",
        json={
            "code": "STONE",
            "name": "Raw Stone",
            "category_id": category_id,
            "default_unit_id": str(ton_unit.id),
        },
        headers=headers,
    )
    assert material_response.status_code == 201, material_response.text
    material = material_response.json()["data"]
    assert material["category_id"] == category_id
    assert material["default_unit_id"] == str(ton_unit.id)


@pytest.mark.parametrize("prefix,payload", SMOKE_TEST_ENTITIES)
async def test_entity_router_is_wired_up(client, tenant_a_admin, prefix, payload):
    headers = await login_headers(client, tenant_a_admin.email)

    create_response = await client.post(f"/api/v1/{prefix}", json=payload, headers=headers)
    assert create_response.status_code == 201, create_response.text
    item_id = create_response.json()["data"]["id"]

    list_response = await client.get(f"/api/v1/{prefix}", headers=headers)
    assert list_response.status_code == 200
    assert list_response.json()["meta"]["total_items"] == 1

    deactivate_response = await client.post(f"/api/v1/{prefix}/{item_id}/deactivate", headers=headers)
    assert deactivate_response.status_code == 200
    assert deactivate_response.json()["data"]["status"] == "INACTIVE"
