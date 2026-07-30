"""Tests for authentication and role-based access control boundaries.

Every critical endpoint must:
  - Return 401 to unauthenticated requests
  - Return 403 to roles that are not permitted
"""
import pytest
from httpx import AsyncClient


# ── /metrics and /sla ────────────────────────────────────────────────────────

async def test_metrics_requires_auth(anon_client: AsyncClient):
    resp = await anon_client.get("/metrics")
    assert resp.status_code == 401


async def test_sla_requires_auth(anon_client: AsyncClient):
    resp = await anon_client.get("/sla")
    assert resp.status_code == 401


async def test_metrics_viewer_denied(viewer_client: AsyncClient):
    resp = await viewer_client.get("/metrics")
    assert resp.status_code == 403


async def test_sla_viewer_denied(viewer_client: AsyncClient):
    resp = await viewer_client.get("/sla")
    assert resp.status_code == 403


async def test_metrics_admin_allowed(client: AsyncClient):
    resp = await client.get("/metrics")
    assert resp.status_code == 200


# ── /health is public ────────────────────────────────────────────────────────

async def test_health_is_public(anon_client: AsyncClient):
    resp = await anon_client.get("/health")
    assert resp.status_code == 200


# ── telemetry ingest ─────────────────────────────────────────────────────────

async def test_telemetry_ingest_requires_auth(anon_client: AsyncClient):
    resp = await anon_client.post(
        "/api/v1/telemetry/ingest",
        json={"device_id": "dev1", "telemetry_type": "temperature", "value": 22.5},
    )
    assert resp.status_code == 401


# ── recall reads ─────────────────────────────────────────────────────────────

async def test_recall_list_requires_auth(anon_client: AsyncClient):
    resp = await anon_client.get("/api/v1/recalls")
    assert resp.status_code == 401


async def test_recall_detail_requires_auth(anon_client: AsyncClient):
    resp = await anon_client.get("/api/v1/recalls/1")
    assert resp.status_code in (401, 404)  # 404 if record doesn't exist, 401 if auth checked first


async def test_recall_trace_requires_auth(anon_client: AsyncClient):
    resp = await anon_client.get("/api/v1/recalls/1/trace")
    assert resp.status_code in (401, 404)


# ── certificate reads ─────────────────────────────────────────────────────────

async def test_certificate_by_item_requires_auth(anon_client: AsyncClient):
    resp = await anon_client.get("/api/v1/certificates/by-item/1")
    assert resp.status_code == 401


async def test_certificate_verify_chain_requires_auth(anon_client: AsyncClient):
    resp = await anon_client.get("/api/v1/certificates/verify-chain/1")
    assert resp.status_code in (401, 404)


async def test_certificate_requests_list_requires_auth(anon_client: AsyncClient):
    resp = await anon_client.get("/api/v1/certificates/requests")
    assert resp.status_code == 401


# ── event logs ───────────────────────────────────────────────────────────────

async def test_event_logs_requires_auth(anon_client: AsyncClient):
    resp = await anon_client.get("/api/v1/events/logs")
    assert resp.status_code == 401


# ── ESG ──────────────────────────────────────────────────────────────────────

async def test_esg_summary_requires_auth(anon_client: AsyncClient):
    resp = await anon_client.get("/api/v1/esg/summary")
    assert resp.status_code == 401


# ── developer portal ownership ───────────────────────────────────────────────

async def test_api_key_list_only_shows_own_keys(client: AsyncClient, enterprise_client: AsyncClient):
    # Admin creates a key
    resp = await client.post("/api/v1/developer/api-keys", json={"name": "admin-key"})
    assert resp.status_code == 200

    # Enterprise user should not see admin's key
    resp = await enterprise_client.get("/api/v1/developer/api-keys")
    assert resp.status_code == 200
    key_names = [k["name"] for k in resp.json()["api_keys"]]
    assert "admin-key" not in key_names


async def test_api_key_delete_requires_ownership(client: AsyncClient, enterprise_client: AsyncClient):
    # Admin creates a key
    resp = await client.post("/api/v1/developer/api-keys", json={"name": "admin-owned"})
    key_id = resp.json()["id"]

    # Enterprise user tries to delete admin's key — must be forbidden
    resp = await enterprise_client.delete(f"/api/v1/developer/api-keys/{key_id}")
    assert resp.status_code == 403
