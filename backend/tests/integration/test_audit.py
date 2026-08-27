import pytest

from tests.conftest import login_headers

pytestmark = pytest.mark.asyncio


async def test_login_generates_audit_event(client, db_session, tenant_a_admin):
    from sqlalchemy import select

    from app.models.audit import AuditEvent

    await login_headers(client, tenant_a_admin.email)

    result = await db_session.execute(
        select(AuditEvent).where(
            AuditEvent.action == "LOGIN", AuditEvent.user_id == tenant_a_admin.id
        )
    )
    events = result.scalars().all()
    assert len(events) == 1


async def test_failed_login_generates_audit_event(client, tenant_a_admin, db_session):
    from sqlalchemy import select

    from app.models.audit import AuditEvent

    await client.post(
        "/api/v1/auth/login", json={"email": tenant_a_admin.email, "password": "wrong"}
    )

    result = await db_session.execute(select(AuditEvent).where(AuditEvent.action == "LOGIN_FAILED"))
    assert len(result.scalars().all()) == 1


async def test_user_creation_generates_audit_event(client, db_session, tenant_a_admin):
    from sqlalchemy import select

    from app.models.audit import AuditEvent

    headers = await login_headers(client, tenant_a_admin.email)
    await client.post(
        "/api/v1/users",
        json={
            "email": "audited@tenanta.example.com",
            "password": "Password!123",
            "first_name": "A",
            "last_name": "B",
        },
        headers=headers,
    )

    result = await db_session.execute(select(AuditEvent).where(AuditEvent.action == "USER_CREATED"))
    assert len(result.scalars().all()) == 1


async def test_audit_log_is_tenant_scoped(client, tenant_a_admin, tenant_b_admin):
    await login_headers(client, tenant_a_admin.email)
    await login_headers(client, tenant_b_admin.email)

    headers_a = await login_headers(client, tenant_a_admin.email)
    response = await client.get("/api/v1/audit", headers=headers_a)
    assert response.status_code == 200
    for event in response.json()["data"]:
        assert event["tenant_id"] == str(tenant_a_admin.tenant_id)


async def test_audit_endpoint_requires_permission(client, tenant_a_viewer):
    headers = await login_headers(client, tenant_a_viewer.email)
    response = await client.get("/api/v1/audit", headers=headers)
    assert response.status_code == 403
