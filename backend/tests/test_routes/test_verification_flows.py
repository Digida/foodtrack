"""Route tests for verification endpoints, SSO provider discovery, and superuser access."""
import pytest
from httpx import AsyncClient

from app.services.auth_service import hash_password
from app.models.user import User, UserRole


# ── /auth/sso-providers ───────────────────────────────────────────────────────

async def test_sso_providers_endpoint(anon_client: AsyncClient):
    resp = await anon_client.get("/api/v1/auth/sso-providers")
    assert resp.status_code == 200
    providers = {p["provider"] for p in resp.json()["providers"]}
    assert {"google", "microsoft", "apple"} <= providers


# ── /auth/me exposes new fields ───────────────────────────────────────────────

async def test_me_includes_alternate_fields(client: AsyncClient):
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 200
    data = resp.json()
    assert "alternate_email" in data
    assert "alternate_phone" in data
    assert "phone_verified" in data


# ── email verification endpoint flow ──────────────────────────────────────────

async def test_email_otp_and_verify_endpoints(client: AsyncClient):
    resp = await client.post("/api/v1/auth/email-otp")
    assert resp.status_code == 200
    dev_code = resp.json().get("dev_code")
    assert dev_code

    verify = await client.post("/api/v1/auth/verify-email", json={"code": dev_code})
    assert verify.status_code == 200
    assert verify.json()["email_verified"] is True


async def test_verify_email_wrong_code(client: AsyncClient):
    await client.post("/api/v1/auth/email-otp")
    resp = await client.post("/api/v1/auth/verify-email", json={"code": "000000"})
    assert resp.status_code == 400


# ── phone verification endpoint flow ──────────────────────────────────────────

async def test_phone_otp_requires_phone(anon_client: AsyncClient):
    resp = await anon_client.post("/api/v1/auth/phone-otp")
    assert resp.status_code == 401  # login-gated


async def test_sso_with_invalid_token(anon_client: AsyncClient):
    resp = await anon_client.post("/api/v1/auth/sso", json={"provider": "google", "token": "bogus"})
    assert resp.status_code == 400


# ── superuser can access admin endpoints ──────────────────────────────────────

async def test_superuser_can_list_users(db, superuser_token: str):
    transport = __import__("httpx").ASGITransport
    from httpx import AsyncClient as AC
    from app.main import app
    from app.database import get_db
    from tests.conftest import override_get_db
    app.dependency_overrides[get_db] = override_get_db
    try:
        async with AC(transport=transport(app=app), base_url="http://test",
                      headers={"Authorization": f"Bearer {superuser_token}"}) as c:
            resp = await c.get("/api/v1/auth/users")
            assert resp.status_code == 200
            assert "users" in resp.json()
    finally:
        app.dependency_overrides.clear()


async def test_superuser_can_issue_item_certificate(client: AsyncClient, taxonomy_item, db):
    """Issue a certificate against a taxonomy item without any product."""
    resp = await client.post("/api/v1/certificates", json={
        "item_id": taxonomy_item.id,
        "type": "halal",
        "issuing_body": "Demo Certifier",
    })
    assert resp.status_code == 200
    cert = resp.json()["certificate"]
    assert cert["item_id"] == taxonomy_item.id
    assert cert["status"] == "issued"


# ── role management with SUPERUSER ────────────────────────────────────────────

async def test_admin_role_update_to_superuser_denied(db, admin_token: str):
    """A plain admin cannot grant the superuser role (server-side guard)."""
    from httpx import ASGITransport, AsyncClient as AC
    from app.main import app
    from app.database import get_db
    from tests.conftest import override_get_db

    target = User(email="role-target@test.com", full_name="Role Target",
                  hashed_password=hash_password("pw12345678"), role=UserRole.VIEWER, is_active=True)
    db.add(target)
    await db.commit()
    await db.refresh(target)

    app.dependency_overrides[get_db] = override_get_db
    try:
        async with AC(transport=ASGITransport(app=app), base_url="http://test",
                      headers={"Authorization": f"Bearer {admin_token}"}) as c:
            resp = await c.put("/api/v1/auth/users/role", json={"user_id": target.id, "role": "superuser"})
            assert resp.status_code == 403
    finally:
        app.dependency_overrides.clear()
