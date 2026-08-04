"""API tests for SSO endpoints (no network): provider list, authorize, bad state."""
from httpx import AsyncClient


def _enable_google(monkeypatch):
    from app.services import auth_service
    monkeypatch.setattr(auth_service.settings, "GOOGLE_CLIENT_ID", "test-google.apps.googleusercontent.com")
    monkeypatch.setattr(auth_service.settings, "GOOGLE_CLIENT_SECRET", "test-secret")
    monkeypatch.setattr(auth_service.settings, "SSO_REDIRECT_URI", "http://localhost:5173/sso.html")


# ── provider list ────────────────────────────────────────────────────────────

async def test_sso_providers_endpoint(anon_client: AsyncClient):
    resp = await anon_client.get("/api/v1/auth/sso-providers")
    assert resp.status_code == 200
    providers = resp.json()["providers"]
    names = {p["provider"] for p in providers}
    assert names == {"google", "microsoft", "apple", "github"}
    by_name = {p["provider"]: p for p in providers}
    for provider in names:
        assert "authorize_endpoint" in by_name[provider]


# ── authorize ────────────────────────────────────────────────────────────────

async def test_sso_authorize_unconfigured_400(anon_client: AsyncClient, monkeypatch):
    # Force the provider unconfigured regardless of .env bleed (load_dotenv)
    from app.services import auth_service
    monkeypatch.setattr(auth_service.settings, "GOOGLE_CLIENT_ID", "")
    monkeypatch.setattr(auth_service.settings, "GOOGLE_CLIENT_SECRET", "")
    resp = await anon_client.get("/api/v1/auth/sso/google/authorize")
    assert resp.status_code == 400  # GOOGLE_CLIENT_ID intentionally cleared


async def test_sso_authorize_returns_pkce_url(anon_client: AsyncClient, monkeypatch):
    _enable_google(monkeypatch)
    resp = await anon_client.get(
        "/api/v1/auth/sso/google/authorize?redirect_uri=http://localhost:5173/sso.html&state=xyz"
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["provider"] == "google"
    assert body["authorize_url"].startswith("https://accounts.google.com/o/oauth2/v2/auth")
    assert "code_challenge=" in body["authorize_url"]
    assert "code_challenge_method=S256" in body["authorize_url"]
    assert "state=" in body["authorize_url"]
    assert "redirect_uri=" in body["authorize_url"]
    assert body["code_verifier"]  # PKCE verifier returned to the SPA
    assert body["expires_in"] == 600


async def test_sso_authorize_unknown_provider_400(anon_client: AsyncClient, monkeypatch):
    _enable_google(monkeypatch)
    resp = await anon_client.get("/api/v1/auth/sso/facebook/authorize")
    assert resp.status_code == 400


async def test_sso_authorize_apple_uses_query_mode(anon_client: AsyncClient, monkeypatch):
    from app.services import auth_service
    monkeypatch.setattr(auth_service.settings, "APPLE_CLIENT_ID", "com.foodtrack.app")
    monkeypatch.setattr(auth_service.settings, "SSO_REDIRECT_URI", "http://localhost:5173/sso.html")
    resp = await anon_client.get("/api/v1/auth/sso/apple/authorize")
    assert resp.status_code == 200
    body = resp.json()
    assert body["provider"] == "apple"
    assert "response_mode=query" in body["authorize_url"]


# ── completion with a bogus state (no network needed) ────────────────────────

async def test_sso_callback_bad_state_400(anon_client: AsyncClient):
    resp = await anon_client.get("/api/v1/auth/sso/google/callback?code=abc&state=garbage")
    assert resp.status_code == 400


async def test_sso_token_bad_state_400(anon_client: AsyncClient):
    resp = await anon_client.post(
        "/api/v1/auth/sso/google/token",
        json={"code": "abc", "state": "garbage"},
    )
    assert resp.status_code == 400
