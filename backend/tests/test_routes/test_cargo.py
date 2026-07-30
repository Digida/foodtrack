"""Integration tests for cargo API endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_cargo_endpoint(client: AsyncClient, taxonomy_item):
    """POST /cargo/register should register new cargo."""
    response = await client.post("/cargo/register", json={
        "item_id": taxonomy_item.id,
        "quantity": 1000,
        "unit": "kg",
        "origin_location": "Mombasa",
        "destination_location": "Dubai",
        "mode": "sea_freight",
        "carrier_name": "Maersk",
    })
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert data["status"] == "draft"


@pytest.mark.asyncio
async def test_get_cargo_detail_endpoint(client: AsyncClient, taxonomy_item):
    """GET /cargo/{id} should return cargo detail."""
    reg = await client.post("/cargo/register", json={
        "item_id": taxonomy_item.id, "quantity": 500,
    })
    cargo_id = reg.json()["id"]

    response = await client.get(f"/cargo/{cargo_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == cargo_id
    assert data["item_name"] == taxonomy_item.common_name


@pytest.mark.asyncio
async def test_get_cargo_by_item_endpoint(client: AsyncClient, taxonomy_item):
    """GET /cargo/by-item/{id} should list cargo for an item."""
    await client.post("/cargo/register", json={
        "item_id": taxonomy_item.id, "quantity": 100,
    })

    response = await client.get(f"/cargo/by-item/{taxonomy_item.id}")
    assert response.status_code == 200
    data = response.json()
    assert "cargo" in data
    assert data["total"] >= 1


@pytest.mark.asyncio
async def test_update_cargo_status_endpoint(client: AsyncClient, taxonomy_item):
    """PATCH /cargo/{id}/status should transition cargo status."""
    reg = await client.post("/cargo/register", json={
        "item_id": taxonomy_item.id, "quantity": 200,
    })
    cargo_id = reg.json()["id"]

    response = await client.patch(f"/cargo/{cargo_id}/status", json={
        "status": "registered",
    })
    assert response.status_code == 200
    assert response.json()["status"] == "registered"


@pytest.mark.asyncio
async def test_cargo_certification_status_endpoint(client: AsyncClient, taxonomy_item):
    """GET /cargo/{id}/certification-status should return cert health."""
    reg = await client.post("/cargo/register", json={
        "item_id": taxonomy_item.id, "quantity": 300,
    })
    cargo_id = reg.json()["id"]

    response = await client.get(f"/cargo/{cargo_id}/certification-status")
    assert response.status_code == 200
    data = response.json()
    assert "certification_health" in data
    assert "valid_certificates" in data