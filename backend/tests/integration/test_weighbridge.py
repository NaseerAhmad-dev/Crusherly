import pytest

from tests.conftest import login_headers

pytestmark = pytest.mark.asyncio


def _ticket_payload(unit_id, organization_unit_id=None, **overrides):
    payload = {
        "unit_id": str(unit_id),
        "organization_unit_id": str(organization_unit_id) if organization_unit_id else None,
        "ticket_type": "INBOUND",
        "vehicle_number": "jk01ab1234",
        "driver_name": "Test Driver",
        "party_name": "Test Party",
        "material_description": "Raw stone",
        "first_weight": "12000.500",
    }
    payload.update(overrides)
    return payload


async def test_operator_can_create_and_complete_a_ticket_in_their_plant(
    client, tenant_a_operator, tenant_a_plants, tenant_a_fiscal_year, ton_unit
):
    headers = await login_headers(client, tenant_a_operator.email)
    pampore_id = tenant_a_plants["pampore"].id

    create_response = await client.post(
        "/api/v1/weighbridge/tickets",
        json=_ticket_payload(ton_unit.id, pampore_id),
        headers=headers,
    )
    assert create_response.status_code == 201, create_response.text
    ticket = create_response.json()["data"]
    assert ticket["status"] == "OPEN"
    assert ticket["ticket_number"].startswith("WBT-")
    assert ticket["net_weight"] is None

    complete_response = await client.post(
        f"/api/v1/weighbridge/tickets/{ticket['id']}/complete",
        json={"second_weight": "4000.000"},
        headers=headers,
    )
    assert complete_response.status_code == 200, complete_response.text
    completed = complete_response.json()["data"]
    assert completed["status"] == "COMPLETED"
    assert completed["net_weight"] == "8000.500"


async def test_operator_cannot_create_a_ticket_outside_their_plant(
    client, tenant_a_operator, tenant_a_plants, tenant_a_fiscal_year, ton_unit
):
    headers = await login_headers(client, tenant_a_operator.email)
    pulwama_id = tenant_a_plants["pulwama"].id

    response = await client.post(
        "/api/v1/weighbridge/tickets",
        json=_ticket_payload(ton_unit.id, pulwama_id),
        headers=headers,
    )
    assert response.status_code == 403


async def test_manager_cannot_complete_a_ticket_from_a_plant_outside_their_scope(
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
        "/api/v1/weighbridge/tickets",
        json=_ticket_payload(ton_unit.id, pulwama_id),
        headers=admin_headers,
    )
    assert create_response.status_code == 201, create_response.text
    ticket_id = create_response.json()["data"]["id"]

    manager_headers = await login_headers(client, tenant_a_plant_manager.email)
    complete_response = await client.post(
        f"/api/v1/weighbridge/tickets/{ticket_id}/complete",
        json={"second_weight": "4000.000"},
        headers=manager_headers,
    )
    assert complete_response.status_code == 403


async def test_viewer_cannot_create_a_ticket(
    client, tenant_a_viewer, tenant_a_fiscal_year, ton_unit
):
    headers = await login_headers(client, tenant_a_viewer.email)
    response = await client.post(
        "/api/v1/weighbridge/tickets", json=_ticket_payload(ton_unit.id), headers=headers
    )
    assert response.status_code == 403


async def test_create_ticket_fails_without_an_active_fiscal_year(client, tenant_a_admin, ton_unit):
    headers = await login_headers(client, tenant_a_admin.email)
    response = await client.post(
        "/api/v1/weighbridge/tickets", json=_ticket_payload(ton_unit.id), headers=headers
    )
    assert response.status_code == 409


async def test_cannot_complete_an_already_completed_ticket(
    client, tenant_a_admin, tenant_a_fiscal_year, ton_unit
):
    headers = await login_headers(client, tenant_a_admin.email)
    create_response = await client.post(
        "/api/v1/weighbridge/tickets", json=_ticket_payload(ton_unit.id), headers=headers
    )
    ticket_id = create_response.json()["data"]["id"]

    first = await client.post(
        f"/api/v1/weighbridge/tickets/{ticket_id}/complete",
        json={"second_weight": "4000.000"},
        headers=headers,
    )
    assert first.status_code == 200

    second = await client.post(
        f"/api/v1/weighbridge/tickets/{ticket_id}/complete",
        json={"second_weight": "4000.000"},
        headers=headers,
    )
    assert second.status_code == 409


async def test_list_tickets_is_scoped_to_the_caller_tenant(
    client, tenant_a_admin, tenant_b_admin, tenant_a_fiscal_year, ton_unit
):
    headers_a = await login_headers(client, tenant_a_admin.email)
    await client.post(
        "/api/v1/weighbridge/tickets", json=_ticket_payload(ton_unit.id), headers=headers_a
    )

    list_response_a = await client.get("/api/v1/weighbridge/tickets", headers=headers_a)
    assert list_response_a.status_code == 200
    assert list_response_a.json()["meta"]["total_items"] == 1

    headers_b = await login_headers(client, tenant_b_admin.email)
    list_response_b = await client.get("/api/v1/weighbridge/tickets", headers=headers_b)
    assert list_response_b.status_code == 200
    assert list_response_b.json()["meta"]["total_items"] == 0
