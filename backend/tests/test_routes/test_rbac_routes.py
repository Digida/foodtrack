"""API tests for RBAC endpoints: roles, permissions, role/type assignment."""
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.rbac_service import seed_system_rbac
from app.services.auth_service import register_user


# ── /me exposes permissions + account type ───────────────────────────────────

async def test_me_includes_permissions_and_type(client: AsyncClient):
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 200
    data = resp.json()
    assert "user_type" in data
    assert data["role"] == "admin"
    assert "roles" in data and "admin" in data["roles"]
    assert "users.manage" in data["permissions"]
    assert "system.admin" not in data["permissions"]


async def test_me_requires_auth(anon_client: AsyncClient):
    resp = await anon_client.get("/api/v1/auth/me")
    assert resp.status_code == 401


# ── roles / permissions listing ──────────────────────────────────────────────

async def test_list_roles_admin_allowed(client: AsyncClient, db: AsyncSession):
    await seed_system_rbac(db)
    resp = await client.get("/api/v1/auth/roles")
    assert resp.status_code == 200
    codes = {r["code"] for r in resp.json()["roles"]}
    assert "clerk" in codes and "superuser" in codes


async def test_list_roles_viewer_denied(viewer_client: AsyncClient):
    resp = await viewer_client.get("/api/v1/auth/roles")
    assert resp.status_code == 403


async def test_list_permissions_admin_allowed(client: AsyncClient):
    resp = await client.get("/api/v1/auth/permissions")
    assert resp.status_code == 200
    codes = {p["code"] for p in resp.json()["permissions"]}
    assert "certificates.approve" in codes
    assert "commerce.jobs" in codes


async def test_list_permissions_viewer_denied(viewer_client: AsyncClient):
    resp = await viewer_client.get("/api/v1/auth/permissions")
    assert resp.status_code == 403


# ── custom role CRUD ─────────────────────────────────────────────────────────

async def test_create_role_admin(client: AsyncClient, db: AsyncSession):
    await seed_system_rbac(db)
    resp = await client.post(
        "/api/v1/auth/roles",
        json={"code": "quality", "name": "Quality Lead", "permissions": ["items.read", "certificates.verify"]},
    )
    assert resp.status_code == 200
    assert resp.json()["code"] == "quality"
    assert resp.json()["is_system"] is False


async def test_create_role_unknown_permission_400(client: AsyncClient, db: AsyncSession):
    await seed_system_rbac(db)
    resp = await client.post(
        "/api/v1/auth/roles",
        json={"code": "bad", "name": "Bad", "permissions": ["not.a.perm"]},
    )
    assert resp.status_code == 400


async def test_create_role_viewer_denied(viewer_client: AsyncClient):
    resp = await viewer_client.post(
        "/api/v1/auth/roles",
        json={"code": "quality", "name": "Quality", "permissions": []},
    )
    assert resp.status_code == 403


async def test_delete_custom_role_flow(client: AsyncClient, db: AsyncSession):
    await seed_system_rbac(db)
    await client.post(
        "/api/v1/auth/roles",
        json={"code": "temp", "name": "Temp", "permissions": ["items.read"]},
    )
    resp = await client.delete("/api/v1/auth/roles/temp")
    assert resp.status_code == 200
    assert resp.json()["deleted"] is True
    # deleting again → 404
    resp = await client.delete("/api/v1/auth/roles/temp")
    assert resp.status_code == 404


async def test_delete_system_role_forbidden(client: AsyncClient, db: AsyncSession):
    await seed_system_rbac(db)
    resp = await client.delete("/api/v1/auth/roles/admin")
    assert resp.status_code == 403


# ── role / type assignment endpoints ─────────────────────────────────────────

async def test_assign_roles_route(client: AsyncClient, db: AsyncSession):
    await seed_system_rbac(db)
    target, _ = await register_user(db, "assign@example.com", "password123", "Assign")
    resp = await client.post(
        f"/api/v1/auth/users/{target.id}/roles",
        json={"roles": ["clerk", "courier"]},
    )
    assert resp.status_code == 200
    assert "clerk" in resp.json()["roles"]
    assert "courier" in resp.json()["roles"]


async def test_assign_roles_unknown_400(client: AsyncClient, db: AsyncSession):
    await seed_system_rbac(db)
    target, _ = await register_user(db, "assign2@example.com", "password123", "Assign 2")
    resp = await client.post(
        f"/api/v1/auth/users/{target.id}/roles",
        json={"roles": ["nope"]},
    )
    assert resp.status_code == 400


async def test_assign_roles_viewer_denied(viewer_client: AsyncClient, db: AsyncSession):
    target, _ = await register_user(db, "assign3@example.com", "password123", "Assign 3")
    resp = await viewer_client.post(
        f"/api/v1/auth/users/{target.id}/roles",
        json={"roles": ["clerk"]},
    )
    assert resp.status_code == 403


async def test_set_user_type_route(client: AsyncClient, db: AsyncSession):
    target, _ = await register_user(db, "type@example.com", "password123", "Type")
    resp = await client.put(
        f"/api/v1/auth/users/{target.id}/type",
        json={"user_type": "operations"},
    )
    assert resp.status_code == 200
    assert resp.json()["user_type"] == "operations"


async def test_update_role_route_syncs_user_type(client: AsyncClient, db: AsyncSession):
    target, _ = await register_user(db, "roleroute@example.com", "password123", "Role Route")
    resp = await client.put(
        "/api/v1/auth/users/role",
        json={"user_id": target.id, "role": "clerk"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["role"] == "clerk"
    assert body["user_type"] == "operations"


async def test_role_endpoints_require_auth(anon_client: AsyncClient):
    for method, path in [
        ("get", "/api/v1/auth/roles"),
        ("get", "/api/v1/auth/permissions"),
        ("get", "/api/v1/auth/users"),
    ]:
        resp = await anon_client.request(method, path)
        assert resp.status_code == 401
