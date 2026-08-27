import pytest

from tests.conftest import RAW_PASSWORD, login_headers

pytestmark = pytest.mark.asyncio


async def test_valid_login_succeeds(client, tenant_a_admin):
    response = await client.post(
        "/api/v1/auth/login", json={"email": tenant_a_admin.email, "password": RAW_PASSWORD}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert "access_token" in body["data"]
    assert "refresh_token" in body["data"]


async def test_invalid_password_rejected(client, tenant_a_admin):
    response = await client.post(
        "/api/v1/auth/login", json={"email": tenant_a_admin.email, "password": "wrong-password"}
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


async def test_unknown_email_rejected(client):
    response = await client.post(
        "/api/v1/auth/login", json={"email": "nobody@example.com", "password": "whatever"}
    )
    assert response.status_code == 401


async def test_inactive_account_rejected(client, db_session, tenant_a_admin):
    from app.models.enums import UserStatus

    tenant_a_admin.status = UserStatus.INACTIVE
    await db_session.commit()

    response = await client.post(
        "/api/v1/auth/login", json={"email": tenant_a_admin.email, "password": RAW_PASSWORD}
    )
    assert response.status_code == 401


async def test_invalid_token_rejected_on_protected_route(client):
    response = await client.get(
        "/api/v1/auth/me", headers={"Authorization": "Bearer not-a-real-token"}
    )
    assert response.status_code == 401


async def test_expired_token_rejected(client, tenant_a_admin, monkeypatch):
    import app.core.config as config_module

    settings = config_module.get_settings()
    monkeypatch.setattr(settings, "access_token_expire_minutes", -1)

    headers = await login_headers(client, tenant_a_admin.email)
    response = await client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 401


async def test_me_returns_roles_and_permissions(client, tenant_a_admin):
    headers = await login_headers(client, tenant_a_admin.email)
    response = await client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["email"] == tenant_a_admin.email
    assert "TENANT_ADMIN" in data["roles"]
    assert "users.view" in data["permissions"]


async def test_refresh_rotates_token_and_old_refresh_token_is_revoked(client, tenant_a_admin):
    login_response = await client.post(
        "/api/v1/auth/login", json={"email": tenant_a_admin.email, "password": RAW_PASSWORD}
    )
    old_refresh = login_response.json()["data"]["refresh_token"]

    refresh_response = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": old_refresh}
    )
    assert refresh_response.status_code == 200
    new_refresh = refresh_response.json()["data"]["refresh_token"]
    assert new_refresh != old_refresh

    reuse_response = await client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert reuse_response.status_code == 401


async def test_logout_revokes_refresh_token(client, tenant_a_admin):
    login_response = await client.post(
        "/api/v1/auth/login", json={"email": tenant_a_admin.email, "password": RAW_PASSWORD}
    )
    refresh_token = login_response.json()["data"]["refresh_token"]

    logout_response = await client.post(
        "/api/v1/auth/logout", json={"refresh_token": refresh_token}
    )
    assert logout_response.status_code == 200

    reuse_response = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": refresh_token}
    )
    assert reuse_response.status_code == 401
