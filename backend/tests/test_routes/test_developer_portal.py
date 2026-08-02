"""Developer portal — API-key generation emails the key to the developer.

The create route must not fail when email is unconfigured, and must hand the
raw key to the email transport (dev email by default, or an explicit
notify_email recipient) when it is configured.
"""
import pytest
from httpx import AsyncClient

import app.routes.developer_portal as dp


async def test_create_key_without_email_config(client: AsyncClient):
    resp = await client.post("/api/v1/developer/api-keys", json={"name": "no-email"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["api_key"].startswith("ft_")
    assert body["email_to"] == "digikiminvest@gmail.com"
    assert body["email_status"] == "not_configured"


async def test_create_key_emails_dev_by_default(client: AsyncClient, monkeypatch):
    sent: list[tuple[str, str, str]] = []
    monkeypatch.setattr(dp, "email_configured", lambda: True)

    async def fake_send_email(to, subject, body):
        sent.append((to, subject, body))
        return True

    monkeypatch.setattr(dp, "send_email", fake_send_email)

    resp = await client.post("/api/v1/developer/api-keys", json={"name": "dev-mail"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["email_status"] == "sent"
    assert body["email_to"] == "digikiminvest@gmail.com"
    assert len(sent) == 1
    to, subject, body_text = sent[0]
    assert to == "digikiminvest@gmail.com"
    assert "API Key" in subject
    assert body["api_key"] in body_text


async def test_create_key_emails_custom_recipient(client: AsyncClient, monkeypatch):
    sent: list[str] = []
    monkeypatch.setattr(dp, "email_configured", lambda: True)

    async def fake_send_email(to, subject, body):
        sent.append(to)
        return True

    monkeypatch.setattr(dp, "send_email", fake_send_email)

    resp = await client.post(
        "/api/v1/developer/api-keys",
        json={"name": "custom-mail", "notify_email": "ops@example.com"},
    )
    assert resp.status_code == 200
    assert resp.json()["email_to"] == "ops@example.com"
    assert sent == ["ops@example.com"]


async def test_create_key_email_failure_reported_but_key_created(
    client: AsyncClient, monkeypatch
):
    monkeypatch.setattr(dp, "email_configured", lambda: True)

    async def fake_send_email(to, subject, body):
        return False

    monkeypatch.setattr(dp, "send_email", fake_send_email)

    resp = await client.post("/api/v1/developer/api-keys", json={"name": "mail-fail"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["email_status"] == "failed"
    assert body["api_key"].startswith("ft_")
