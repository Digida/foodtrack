"""Integration tests for certificate API endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_issue_certificate_endpoint(client: AsyncClient, taxonomy_item):
    """POST /certificates should issue a certificate."""
    # Create a product first
    prod_resp = await client.post("/products", json={
        "sku": "CERT-TEST-SKU", "name": "Cert Test Product",
        "category": "fresh_produce",
    })
    assert prod_resp.status_code == 200
    product_id = prod_resp.json()["id"]

    response = await client.post("/certificates", json={
        "product_id": product_id,
        "type": "organic",
        "issuing_body": "Test Certifier",
        "recipient_entity": "Test Co",
        "description": "Integration test cert",
    })
    assert response.status_code == 200
    data = response.json()
    assert "certificate" in data
    assert data["certificate"]["type"] == "organic"
    assert data["certificate"]["status"] == "issued"


@pytest.mark.asyncio
async def test_list_certificates_endpoint(client: AsyncClient):
    """GET /certificates should return certificate list."""
    response = await client.get("/certificates")
    assert response.status_code == 200
    data = response.json()
    assert "certificates" in data
    assert isinstance(data["certificates"], list)


@pytest.mark.asyncio
async def test_get_certificate_endpoint(client: AsyncClient):
    """GET /certificates/{id} should return certificate details."""
    # First issue one
    prod_resp = await client.post("/products", json={
        "sku": "CERT-GET-SKU", "name": "Cert Get Product", "category": "fresh_produce",
    })
    assert prod_resp.status_code == 200
    product_id = prod_resp.json()["id"]

    issue_resp = await client.post("/certificates", json={
        "product_id": product_id, "type": "halal",
    })
    assert issue_resp.status_code == 200
    cert_id = issue_resp.json()["certificate"]["certificate_id"]

    # Get by certificate_id
    get_resp = await client.get(f"/certificates/{cert_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["certificate_id"] == cert_id


@pytest.mark.asyncio
async def test_notify_expiring_endpoint(client: AsyncClient):
    """POST /certificates/notify-expiring should return check results."""
    response = await client.post("/certificates/notify-expiring")
    assert response.status_code == 200
    data = response.json()
    assert "total_expiring" in data
    assert "notified_count" in data
    assert "certificates" in data


@pytest.mark.asyncio
async def test_certificate_request_flow(client: AsyncClient, taxonomy_item):
    """End-to-end: request -> list -> approve."""
    # Request a certificate
    req_resp = await client.post("/certificates/requests", json={
        "item_id": taxonomy_item.id,
        "requested_type": "organic",
        "applicant_notes": "Need for Dubai",
        "target_market": "dubai_import",
    })
    assert req_resp.status_code == 200
    req_id = req_resp.json()["certificate_request"]["id"]

    # List requests
    list_resp = await client.get("/certificates/requests")
    assert list_resp.status_code == 200
    request_ids = [r["id"] for r in list_resp.json()["certificate_requests"]]
    assert req_id in request_ids

    # Get single request
    get_resp = await client.get(f"/certificates/requests/{req_id}")
    assert get_resp.status_code == 200

    # Approve it (requires a product to auto-issue certificate)
    prod_resp = await client.post("/products", json={
        "sku": "CERT-REQ-SKU", "name": "Req Product", "category": "fresh_produce",
    })
    assert prod_resp.status_code == 200

    review_resp = await client.post(f"/certificates/requests/{req_id}/review", json={
        "decision": "approved",
        "reviewer_notes": "Approved for testing",
    })
    assert review_resp.status_code == 200
    assert review_resp.json()["certificate_request"]["status"] == "approved"