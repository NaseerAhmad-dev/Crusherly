import pytest

from tests.conftest import login_headers

pytestmark = pytest.mark.asyncio


async def test_permission_granted_allows_action(client, tenant_a_admin):
    headers = await login_headers(client, tenant_a_admin.email)
    response = await client.get("/api/v1/users", headers=headers)
    assert response.status_code == 200


async def test_permission_denied_returns_403(client, tenant_a_viewer):
    headers = await login_headers(client, tenant_a_viewer.email)
    response = await client.post(
        "/api/v1/users",
        json={
            "email": "new@tenanta.example.com",
            "password": "Password!123",
            "first_name": "A",
            "last_name": "B",
        },
        headers=headers,
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


async def test_unauthenticated_request_returns_401(client):
    response = await client.get("/api/v1/users")
    assert response.status_code == 401


async def test_role_assignment_grants_new_permission(client, db_session, tenant_a, tenant_a_admin):
    from app.models.enums import UserStatus
    from app.models.rbac import Role, RolePermission
    from app.models.user import User
    from app.security.passwords import hash_password

    role = Role(tenant_id=tenant_a.id, code="CUSTOM_VIEWER", name="Custom Viewer", is_system=False)
    db_session.add(role)
    await db_session.flush()

    from app.repositories import permission_repository

    permission = await permission_repository.get_by_code(db_session, "dashboard.view")
    db_session.add(RolePermission(role_id=role.id, permission_id=permission.id))

    plain_user = User(
        tenant_id=tenant_a.id,
        email="plain@tenanta.example.com",
        password_hash=hash_password("Password!123"),
        first_name="Plain",
        last_name="User",
        status=UserStatus.ACTIVE,
        is_verified=True,
    )
    db_session.add(plain_user)
    await db_session.commit()

    admin_headers = await login_headers(client, tenant_a_admin.email)
    assign_response = await client.post(
        f"/api/v1/users/{plain_user.id}/role-assignments",
        json={"role_id": str(role.id)},
        headers=admin_headers,
    )
    assert assign_response.status_code == 201
    assert assign_response.json()["data"]["role_code"] == "CUSTOM_VIEWER"


async def test_user_can_hold_multiple_roles(
    client, db_session, tenant_a, tenant_a_viewer, seed_roles
):
    from app.models.rbac import UserRole

    db_session.add(UserRole(user_id=tenant_a_viewer.id, role_id=seed_roles["OPERATOR"].id))
    await db_session.commit()

    headers = await login_headers(client, tenant_a_viewer.email)
    response = await client.get("/api/v1/auth/me", headers=headers)
    roles = response.json()["data"]["roles"]
    assert "VIEWER" in roles and "OPERATOR" in roles


async def test_system_role_cannot_be_deleted(client, tenant_a_admin, seed_roles):
    headers = await login_headers(client, tenant_a_admin.email)
    response = await client.delete(f"/api/v1/roles/{seed_roles['VIEWER'].id}", headers=headers)
    assert response.status_code == 403
