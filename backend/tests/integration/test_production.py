import pytest

from tests.conftest import login_headers

pytestmark = pytest.mark.asyncio


def _entry_payload(unit_id, organization_unit_id=None, **overrides):
    payload = {
        "organization_unit_id": str(organization_unit_id) if organization_unit_id else None,
        "production_date": "2026-08-18",
        "shift": "DAY",
        "raw_material_description": "Raw stone",
        "raw_material_quantity": "20000.000",
        "raw_material_unit_id": str(unit_id),
        "outputs": [
            {
                "product_description": "40mm Aggregate",
                "quantity": "8000.000",
                "unit_id": str(unit_id),
            },
            {"product_description": "Dust", "quantity": "2000.000", "unit_id": str(unit_id)},
        ],
    }
    payload.update(overrides)
    return payload


async def test_operator_can_create_and_submit_an_entry_in_their_plant(
    client, tenant_a_operator, tenant_a_plants, tenant_a_fiscal_year, ton_unit
):
    headers = await login_headers(client, tenant_a_operator.email)
    pampore_id = tenant_a_plants["pampore"].id

    create_response = await client.post(
        "/api/v1/production/entries",
        json=_entry_payload(ton_unit.id, pampore_id),
        headers=headers,
    )
    assert create_response.status_code == 201, create_response.text
    entry = create_response.json()["data"]
    assert entry["status"] == "DRAFT"
    assert entry["entry_number"].startswith("PRD-")
    assert len(entry["outputs"]) == 2

    submit_response = await client.post(
        f"/api/v1/production/entries/{entry['id']}/submit", headers=headers
    )
    assert submit_response.status_code == 200, submit_response.text
    assert submit_response.json()["data"]["status"] == "SUBMITTED"


async def test_operator_cannot_create_an_entry_outside_their_plant(
    client, tenant_a_operator, tenant_a_plants, tenant_a_fiscal_year, ton_unit
):
    headers = await login_headers(client, tenant_a_operator.email)
    pulwama_id = tenant_a_plants["pulwama"].id

    response = await client.post(
        "/api/v1/production/entries",
        json=_entry_payload(ton_unit.id, pulwama_id),
        headers=headers,
    )
    assert response.status_code == 403


async def test_manager_cannot_submit_an_entry_from_a_plant_outside_their_scope(
    client,
    tenant_a_admin,
    tenant_a_plant_manager,
    tenant_a_plants,
    tenant_a_fiscal_year,
    ton_unit,
):
    admin_headers = await login_headers(client, tenant_a_admin.email)
    pulwama_id = tenant_a_plants["pulwama"].id

    create_response = await client.post(
        "/api/v1/production/entries",
        json=_entry_payload(ton_unit.id, pulwama_id),
        headers=admin_headers,
    )
    assert create_response.status_code == 201, create_response.text
    entry_id = create_response.json()["data"]["id"]

    manager_headers = await login_headers(client, tenant_a_plant_manager.email)
    submit_response = await client.post(
        f"/api/v1/production/entries/{entry_id}/submit", headers=manager_headers
    )
    assert submit_response.status_code == 403


async def test_viewer_cannot_create_an_entry(
    client, tenant_a_viewer, tenant_a_fiscal_year, ton_unit
):
    headers = await login_headers(client, tenant_a_viewer.email)
    response = await client.post(
        "/api/v1/production/entries", json=_entry_payload(ton_unit.id), headers=headers
    )
    assert response.status_code == 403


async def test_create_entry_requires_at_least_one_output(
    client, tenant_a_admin, tenant_a_fiscal_year, ton_unit
):
    headers = await login_headers(client, tenant_a_admin.email)
    response = await client.post(
        "/api/v1/production/entries",
        json=_entry_payload(ton_unit.id, outputs=[]),
        headers=headers,
    )
    assert response.status_code == 422


async def test_create_entry_fails_without_an_active_fiscal_year(client, tenant_a_admin, ton_unit):
    headers = await login_headers(client, tenant_a_admin.email)
    response = await client.post(
        "/api/v1/production/entries", json=_entry_payload(ton_unit.id), headers=headers
    )
    assert response.status_code == 409


async def test_cannot_submit_an_already_submitted_entry(
    client, tenant_a_admin, tenant_a_fiscal_year, ton_unit
):
    headers = await login_headers(client, tenant_a_admin.email)
    create_response = await client.post(
        "/api/v1/production/entries", json=_entry_payload(ton_unit.id), headers=headers
    )
    entry_id = create_response.json()["data"]["id"]

    first = await client.post(f"/api/v1/production/entries/{entry_id}/submit", headers=headers)
    assert first.status_code == 200

    second = await client.post(f"/api/v1/production/entries/{entry_id}/submit", headers=headers)
    assert second.status_code == 409


async def test_cannot_cancel_an_already_cancelled_entry(
    client, tenant_a_admin, tenant_a_fiscal_year, ton_unit
):
    headers = await login_headers(client, tenant_a_admin.email)
    create_response = await client.post(
        "/api/v1/production/entries", json=_entry_payload(ton_unit.id), headers=headers
    )
    entry_id = create_response.json()["data"]["id"]

    first = await client.post(f"/api/v1/production/entries/{entry_id}/cancel", headers=headers)
    assert first.status_code == 200

    second = await client.post(f"/api/v1/production/entries/{entry_id}/cancel", headers=headers)
    assert second.status_code == 409


async def test_list_entries_is_scoped_to_the_caller_tenant(
    client, tenant_a_admin, tenant_b_admin, tenant_a_fiscal_year, ton_unit
):
    headers_a = await login_headers(client, tenant_a_admin.email)
    await client.post(
        "/api/v1/production/entries", json=_entry_payload(ton_unit.id), headers=headers_a
    )

    list_response_a = await client.get("/api/v1/production/entries", headers=headers_a)
    assert list_response_a.status_code == 200
    assert list_response_a.json()["meta"]["total_items"] == 1

    headers_b = await login_headers(client, tenant_b_admin.email)
    list_response_b = await client.get("/api/v1/production/entries", headers=headers_b)
    assert list_response_b.status_code == 200
    assert list_response_b.json()["meta"]["total_items"] == 0
