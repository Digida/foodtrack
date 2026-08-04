"""Tests for the /api/v1/ai orchestration routes."""

import pytest


@pytest.mark.asyncio
async def test_orchestrate_returns_strategy(client):
    resp = await client.post("/api/v1/ai/orchestrate", json={
        "task": "plan bulking register for maize",
        "context": {"item_name": "maize", "target_quantity": 5000, "target_price": 0.35},
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["strategy"] in {"mag", "dag", "rag", "fallback"}
    assert body["task"] == "plan bulking register for maize"


@pytest.mark.asyncio
async def test_orchestrate_persists_memory(client):
    await client.post("/api/v1/ai/orchestrate", json={"task": "plan bulking register for maize"})
    resp = await client.get("/api/v1/ai/memories")
    assert resp.status_code == 200
    assert resp.json()["memories"]


@pytest.mark.asyncio
async def test_orchestrate_empty_task_rejected(client):
    resp = await client.post("/api/v1/ai/orchestrate", json={"task": "   "})
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_tool_catalog_lists_forty(client):
    resp = await client.get("/api/v1/ai/tools")
    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] == 40
    names = {t["name"] for t in body["tools"]}
    assert {"bulking_planner", "escrow_calculator", "settlement_calculator"} <= names


@pytest.mark.asyncio
async def test_execute_tool_direct(client):
    resp = await client.post("/api/v1/ai/tools/execute", json={
        "tool": "barcode_tool",
        "args": {"action": "validate", "barcode": "5901234123457"},
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["tool"] == "barcode_tool"


@pytest.mark.asyncio
async def test_execute_unknown_tool(client):
    resp = await client.post("/api/v1/ai/tools/execute", json={"tool": "nope"})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_pipeline_catalog(client):
    resp = await client.get("/api/v1/ai/pipelines")
    assert resp.status_code == 200
    assert resp.json()["count"] >= 4


@pytest.mark.asyncio
async def test_clear_memories(client):
    await client.post("/api/v1/ai/orchestrate", json={"task": "plan bulking register for maize"})
    resp = await client.delete("/api/v1/ai/memories")
    assert resp.status_code == 200
    assert resp.json()["removed"] >= 1
    resp = await client.get("/api/v1/ai/memories")
    assert resp.json()["memories"] == []


@pytest.mark.asyncio
async def test_orchestrate_requires_auth(anon_client):
    resp = await anon_client.post("/api/v1/ai/orchestrate", json={"task": "hello"})
    assert resp.status_code == 401
