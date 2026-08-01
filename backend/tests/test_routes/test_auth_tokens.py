"""API tests for the token-pair lifecycle: register/login/refresh/logout."""
from httpx import AsyncClient


async def _register(anon_client: AsyncClient, email: str = "tok@example.com") -> dict:
    resp = await anon_client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "password123", "full_name": "Token User"},
    )
    assert resp.status_code == 200
    return resp.json()


async def test_register_returns_token_pair(anon_client: AsyncClient):
    body = await _register(anon_client)
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["token_type"] == "bearer"
    assert body["user"]["role"] == "enterprise"
    assert body["user"]["user_type"] == "organization"


async def test_register_accepts_user_type(anon_client: AsyncClient):
    resp = await anon_client.post(
        "/api/v1/auth/register",
        json={
            "email": "consumer@example.com",
            "password": "password123",
            "full_name": "Consumer",
            "user_type": "consumer",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["user"]["user_type"] == "consumer"


async def test_login_returns_token_pair(anon_client: AsyncClient):
    await _register(anon_client, "login@example.com")
    resp = await anon_client.post(
        "/api/v1/auth/login",
        json={"email": "login@example.com", "password": "password123"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["access_token"]
    assert body["refresh_token"]


async def test_login_wrong_password_401(anon_client: AsyncClient):
    await _register(anon_client, "badpw@example.com")
    resp = await anon_client.post(
        "/api/v1/auth/login",
        json={"email": "badpw@example.com", "password": "wrongpass"},
    )
    assert resp.status_code == 401


async def test_refresh_rotates_token_pair(anon_client: AsyncClient):
    body = await _register(anon_client)
    old_refresh = body["refresh_token"]
    resp = await anon_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": old_refresh},
    )
    assert resp.status_code == 200
    new = resp.json()
    assert new["access_token"]
    assert new["refresh_token"] != old_refresh

    # replaying the consumed refresh token is rejected
    resp = await anon_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": old_refresh},
    )
    assert resp.status_code == 401


async def test_refresh_invalid_token_401(anon_client: AsyncClient):
    resp = await anon_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": "not-a-real-token"},
    )
    assert resp.status_code == 401


async def test_logout_revokes_all_tokens(anon_client: AsyncClient):
    body = await _register(anon_client)
    access, refresh = body["access_token"], body["refresh_token"]
    resp = await anon_client.post(
        "/api/v1/auth/logout",
        json={},
        headers={"Authorization": f"Bearer {access}"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "logged_out"

    # revoked refresh token can no longer be used
    resp = await anon_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh},
    )
    assert resp.status_code == 401


async def test_logout_requires_auth(anon_client: AsyncClient):
    resp = await anon_client.post("/api/v1/auth/logout", json={})
    assert resp.status_code == 401
