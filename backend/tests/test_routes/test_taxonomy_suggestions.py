import pytest
from sqlalchemy import select

from app.models.taxonomy import TaxonomySuggestion, TaxonomyItem, ItemName, ItemAttribute, SuggestionStatus


@pytest.mark.asyncio
async def test_create_name_suggestion_as_viewer(viewer_client, taxonomy_item):
    resp = await viewer_client.post("/api/v1/taxonomy/suggestions", json={
        "kind": "name",
        "item_id": taxonomy_item.id,
        "language": "ar",
        "value": "موز",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["kind"] == "name"
    assert data["language"] == "ar"
    assert data["value"] == "موز"
    assert data["status"] == "pending"
    assert data["item_code"] == taxonomy_item.code


@pytest.mark.asyncio
async def test_create_suggestion_requires_auth(anon_client, taxonomy_item):
    resp = await anon_client.post("/api/v1/taxonomy/suggestions", json={
        "kind": "name",
        "item_id": taxonomy_item.id,
        "language": "ar",
        "value": "موز",
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_create_name_suggestion_requires_language(viewer_client, taxonomy_item):
    resp = await viewer_client.post("/api/v1/taxonomy/suggestions", json={
        "kind": "name",
        "item_id": taxonomy_item.id,
        "value": "Banana",
    })
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_create_suggestion_invalid_item(viewer_client):
    resp = await viewer_client.post("/api/v1/taxonomy/suggestions", json={
        "kind": "name",
        "item_id": 999999,
        "language": "ar",
        "value": "موز",
    })
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_create_attribute_suggestion(viewer_client, taxonomy_item):
    resp = await viewer_client.post("/api/v1/taxonomy/suggestions", json={
        "kind": "attribute",
        "item_id": taxonomy_item.id,
        "key": "sugars_per_100g",
        "value": "12.2",
        "unit": "g",
    })
    assert resp.status_code == 200
    assert resp.json()["key"] == "sugars_per_100g"


@pytest.mark.asyncio
async def test_create_missing_item_suggestion(viewer_client, taxonomy_node):
    resp = await viewer_client.post("/api/v1/taxonomy/suggestions", json={
        "kind": "missing_item",
        "node_id": taxonomy_node.id,
        "value": "Dragon Fruit (Yellow)",
    })
    assert resp.status_code == 200
    assert resp.json()["node_name"] == taxonomy_node.name


@pytest.mark.asyncio
async def test_non_admin_cannot_list_all(viewer_client):
    resp = await viewer_client.get("/api/v1/taxonomy/suggestions")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_my_suggestions_only_own(viewer_client, taxonomy_item):
    await viewer_client.post("/api/v1/taxonomy/suggestions", json={
        "kind": "name", "item_id": taxonomy_item.id, "language": "sw", "value": "Ndizi",
    })
    resp = await viewer_client.get("/api/v1/taxonomy/suggestions/mine")
    assert resp.status_code == 200
    assert len(resp.json()["suggestions"]) == 1


@pytest.mark.asyncio
async def test_admin_lists_all_suggestions(client, viewer_client, taxonomy_item):
    await viewer_client.post("/api/v1/taxonomy/suggestions", json={
        "kind": "name", "item_id": taxonomy_item.id, "language": "fr", "value": "Banane",
    })
    resp = await client.get("/api/v1/taxonomy/suggestions")
    assert resp.status_code == 200
    assert len(resp.json()["suggestions"]) == 1


@pytest.mark.asyncio
async def test_admin_accept_name_adds_item_name(client, viewer_client, db, taxonomy_item):
    created = await viewer_client.post("/api/v1/taxonomy/suggestions", json={
        "kind": "name", "item_id": taxonomy_item.id, "language": "ja", "value": "バナナ",
    })
    sid = created.json()["id"]
    resp = await client.post(f"/api/v1/taxonomy/suggestions/{sid}/accept", params={"note": "good"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "accepted"
    name = (await db.execute(
        select(ItemName).where(ItemName.item_id == taxonomy_item.id)
    )).scalar_one_or_none()
    assert name is not None and name.name == "バナナ"


@pytest.mark.asyncio
async def test_admin_accept_attribute_adds_item_attribute(client, viewer_client, db, taxonomy_item):
    created = await viewer_client.post("/api/v1/taxonomy/suggestions", json={
        "kind": "attribute", "item_id": taxonomy_item.id, "key": "energy_kcal", "value": "89", "unit": "kcal",
    })
    sid = created.json()["id"]
    resp = await client.post(f"/api/v1/taxonomy/suggestions/{sid}/accept")
    assert resp.status_code == 200
    attr = (await db.execute(
        select(ItemAttribute).where(ItemAttribute.item_id == taxonomy_item.id)
    )).scalar_one_or_none()
    assert attr is not None and attr.key == "energy_kcal" and attr.unit == "kcal"


@pytest.mark.asyncio
async def test_admin_accept_field_updates_item(client, viewer_client, db, taxonomy_item):
    created = await viewer_client.post("/api/v1/taxonomy/suggestions", json={
        "kind": "field", "item_id": taxonomy_item.id, "key": "description", "value": "Ripe tropical fruit.",
    })
    sid = created.json()["id"]
    resp = await client.post(f"/api/v1/taxonomy/suggestions/{sid}/accept")
    assert resp.status_code == 200
    await db.refresh(taxonomy_item)
    assert taxonomy_item.description == "Ripe tropical fruit."


@pytest.mark.asyncio
async def test_admin_accept_missing_item_creates_item(client, viewer_client, db, taxonomy_node):
    created = await viewer_client.post("/api/v1/taxonomy/suggestions", json={
        "kind": "missing_item", "node_id": taxonomy_node.id, "value": "Purple Sweet Potato",
    })
    sid = created.json()["id"]
    resp = await client.post(f"/api/v1/taxonomy/suggestions/{sid}/accept")
    assert resp.status_code == 200
    item = (await db.execute(
        select(TaxonomyItem).where(TaxonomyItem.common_name == "Purple Sweet Potato")
    )).scalar_one_or_none()
    assert item is not None and item.code.startswith("SUG-")


@pytest.mark.asyncio
async def test_admin_reject_suggestion(client, viewer_client, taxonomy_item):
    created = await viewer_client.post("/api/v1/taxonomy/suggestions", json={
        "kind": "name", "item_id": taxonomy_item.id, "language": "el", "value": "Μπανάνα",
    })
    sid = created.json()["id"]
    resp = await client.post(f"/api/v1/taxonomy/suggestions/{sid}/reject", params={"note": "duplicate"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "rejected"
    assert resp.json()["review_note"] == "duplicate"


@pytest.mark.asyncio
async def test_review_twice_fails(client, viewer_client, taxonomy_item):
    created = await viewer_client.post("/api/v1/taxonomy/suggestions", json={
        "kind": "name", "item_id": taxonomy_item.id, "language": "it", "value": "Banana",
    })
    sid = created.json()["id"]
    await client.post(f"/api/v1/taxonomy/suggestions/{sid}/accept")
    resp = await client.post(f"/api/v1/taxonomy/suggestions/{sid}/accept")
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_non_admin_cannot_accept(viewer_client, taxonomy_item):
    created = await viewer_client.post("/api/v1/taxonomy/suggestions", json={
        "kind": "name", "item_id": taxonomy_item.id, "language": "pt", "value": "Banana",
    })
    sid = created.json()["id"]
    resp = await viewer_client.post(f"/api/v1/taxonomy/suggestions/{sid}/accept")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_admin_accept_unknown_suggestion_404(client):
    resp = await client.post("/api/v1/taxonomy/suggestions/999999/accept")
    assert resp.status_code == 404
