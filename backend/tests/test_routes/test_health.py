"""Tests for GET /health endpoint."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_endpoint(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("ok", "degraded")


@pytest.mark.asyncio
async def test_metrics_endpoint(client: AsyncClient):
    response = await client.get("/metrics")
    assert response.status_code == 200
    data = response.json()
    assert "tables" in data


@pytest.mark.asyncio
async def test_sla_endpoint(client: AsyncClient):
    response = await client.get("/sla")
    assert response.status_code == 200
    data = response.json()
    assert "uptime_pct" in data
    assert "p95_latency_ms_1h" in data
    assert "error_budget_remaining_pct" in data
