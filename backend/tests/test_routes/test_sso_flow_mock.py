"""Mocked end-to-end SSO flow: authorize -> (provider) -> callback -> tokens."""
from httpx import AsyncClient

from app.services import auth_service
from app.models.user import User
from sqlalchemy import select


def _enable_google(monkeypatch):
    monkeypatch.setattr(auth_service.settings, "GOOGLE_CLIENT_ID", "test-google.apps.googleusercontent.com")
    monkeypatch.setattr(auth_service.settings, "GOOGLE_CLIENT_SECRET", "test-secret")
    monkeypatch.setattr(auth_service.settings, "SSO_REDIRECT_URI", "http://localhost:8000/api/v1/auth/sso/google/callback")
    monkeypatch.setattr(auth_service.settings, "SITE_URL", "http://localhost:8000")


async def test_full_sso_code_flow(anon_client: AsyncClient, db, monkeypatch):
    _enable_google(monkeypatch)

    async def fake_exchange(provider, cfg, code, verifier, redirect_uri=None):
        assert code == "provider-code"
        assert verifier
        assert redirect_uri
        return {"access_token": "provider-access-token"}

    async def fake_profile(provider, cfg, tokens):
        return {"email": "sso.user@gmail.com", "name": "SSO User", "id": "abc123"}

    monkeypatch.setattr(auth_service, "_exchange_code_for_tokens", fake_exchange)
    monkeypatch.setattr(auth_service, "_profile_from_tokens", fake_profile)

    # 1. authorize
    authz = await anon_client.get("/api/v1/auth/sso/google/authorize")
    assert authz.status_code == 200
    state = authz.json()["state"]
    assert state

    # 2. callback
    resp = await anon_client.get(
        "/api/v1/auth/sso/google/callback",
        params={"code": "provider-code", "state": state},
    )
    assert resp.status_code in (302, 307), resp.text
    location = resp.headers["location"]
    assert location.startswith("http://localhost:8000/sso.html#access_token="), location
    assert "refresh_token=" in location

    # 3. user upserted with SSO metadata
    user = (await db.execute(select(User).where(User.email == "sso.user@gmail.com"))).scalar_one()
    assert user.sso_provider == "google"
    assert user.sso_id == "abc123"
    assert user.email_verified is True
