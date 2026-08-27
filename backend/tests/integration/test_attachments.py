import pytest

from tests.conftest import login_headers

pytestmark = pytest.mark.asyncio


@pytest.fixture(autouse=True)
def _local_storage(tmp_path, monkeypatch):
    import app.services.storage_service as storage_service

    monkeypatch.setattr(storage_service, "_provider", None)
    monkeypatch.setattr(storage_service.settings, "local_storage_path", str(tmp_path))


async def test_upload_list_download_delete_attachment(client, tenant_a_admin):
    headers = await login_headers(client, tenant_a_admin.email)

    upload_response = await client.post(
        "/api/v1/attachments",
        data={"entity_type": "test_entity", "entity_id": "123"},
        files={"file": ("hello.txt", b"hello world", "text/plain")},
        headers=headers,
    )
    assert upload_response.status_code == 201, upload_response.text
    attachment_id = upload_response.json()["data"]["id"]

    list_response = await client.get(
        "/api/v1/attachments",
        params={"entity_type": "test_entity", "entity_id": "123"},
        headers=headers,
    )
    assert list_response.status_code == 200
    assert len(list_response.json()["data"]) == 1

    download_response = await client.get(
        f"/api/v1/attachments/{attachment_id}/download", headers=headers
    )
    assert download_response.status_code == 200
    assert download_response.json()["data"]["file_name"] == "hello.txt"

    delete_response = await client.delete(f"/api/v1/attachments/{attachment_id}", headers=headers)
    assert delete_response.status_code == 200

    list_after_delete = await client.get(
        "/api/v1/attachments",
        params={"entity_type": "test_entity", "entity_id": "123"},
        headers=headers,
    )
    assert list_after_delete.json()["data"] == []


async def test_attachment_upload_requires_permission(client, tenant_a_viewer):
    headers = await login_headers(client, tenant_a_viewer.email)
    response = await client.post(
        "/api/v1/attachments",
        data={"entity_type": "test_entity", "entity_id": "123"},
        files={"file": ("hello.txt", b"hello", "text/plain")},
        headers=headers,
    )
    assert response.status_code == 403


async def test_tenant_b_cannot_download_tenant_a_attachment(client, tenant_a_admin, tenant_b_admin):
    headers_a = await login_headers(client, tenant_a_admin.email)
    upload_response = await client.post(
        "/api/v1/attachments",
        data={"entity_type": "test_entity", "entity_id": "123"},
        files={"file": ("secret.txt", b"secret", "text/plain")},
        headers=headers_a,
    )
    attachment_id = upload_response.json()["data"]["id"]

    headers_b = await login_headers(client, tenant_b_admin.email)
    response = await client.get(f"/api/v1/attachments/{attachment_id}/download", headers=headers_b)
    assert response.status_code == 404
