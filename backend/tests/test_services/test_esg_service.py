"""Integration tests for ESG routes: carbon footprint CRUD, summary, auth boundary."""
import pytest
from httpx import AsyncClient


async def test_create_carbon_footprint(client: AsyncClient, taxonomy_item):
    resp = await client.post(
        f"/api/v1/esg/items/{taxonomy_item.id}/carbon-footprint",
        json={"kg_co2e_per_kg": 2.5, "water_usage_l_per_kg": 100.0, "source": "IPCC 2023"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["kg_co2e_per_kg"] == 2.5


async def test_get_esg_for_item(client: AsyncClient, taxonomy_item):
    await client.post(
        f"/api/v1/esg/items/{taxonomy_item.id}/carbon-footprint",
        json={"kg_co2e_per_kg": 1.8},
    )
    resp = await client.get(f"/api/v1/esg/items/{taxonomy_item.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["item_id"] == taxonomy_item.id
    assert len(data["carbon_footprints"]) >= 1
    # created_at should be ISO 8601, not Python repr
    ts = data["carbon_footprints"][0]["created_at"]
    if ts:
        assert "T" in ts or ts is None


async def test_esg_summary(client: AsyncClient, taxonomy_item):
    await client.post(
        f"/api/v1/esg/items/{taxonomy_item.id}/carbon-footprint",
        json={"kg_co2e_per_kg": 3.0},
    )
    resp = await client.get("/api/v1/esg/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert "average_kg_co2e_per_kg" in data
    assert "items" in data


async def test_esg_requires_auth(anon_client: AsyncClient, taxonomy_item):
    """ESG endpoints must return 401 for unauthenticated requests."""
    resp = await anon_client.get(f"/api/v1/esg/items/{taxonomy_item.id}")
    assert resp.status_code == 401

    resp = await anon_client.get("/api/v1/esg/summary")
    assert resp.status_code == 401


async def test_esg_viewer_cannot_write(viewer_client: AsyncClient, taxonomy_item):
    """VIEWER role must not be allowed to create carbon footprint records."""
    resp = await viewer_client.post(
        f"/api/v1/esg/items/{taxonomy_item.id}/carbon-footprint",
        json={"kg_co2e_per_kg": 1.0},
    )
    assert resp.status_code == 403
