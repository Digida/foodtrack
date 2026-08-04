"""Tests for taxonomy_service."""
import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.taxonomy import Taxonomy, TaxonomyItem, TaxonomyNode
from app.services import taxonomy_service as ts
from app.services.taxonomy_service import (
    serialize_item,
    serialize_item_detail,
    serialize_taxonomy,
)


async def _make_item(db: AsyncSession, code: str = "TX-1", common_name: str = "Mango") -> TaxonomyItem:
    t = Taxonomy(name=f"T-{uuid.uuid4().hex[:8]}", description="d")
    db.add(t)
    await db.commit()
    await db.refresh(t)
    n = TaxonomyNode(taxonomy_id=t.id, code="N", name="Node", description="nd")
    db.add(n)
    await db.commit()
    await db.refresh(n)
    item = TaxonomyItem(node_id=n.id, code=code, common_name=common_name, scientific_name="M. indica")
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


async def test_list_taxonomies_active_only(db):
    t1 = Taxonomy(name="One")
    t2 = Taxonomy(name="Two", is_active=False)
    db.add_all([t1, t2])
    await db.commit()
    out = await ts.list_taxonomies(db)
    assert [t.name for t in out] == ["One"]


async def test_get_taxonomy(db):
    t = Taxonomy(name="One")
    db.add(t)
    await db.commit()
    await db.refresh(t)
    found = await ts.get_taxonomy(db, t.id)
    assert found is not None and found.name == "One"
    assert await ts.get_taxonomy(db, 99999) is None


async def test_create_and_update_taxonomy(db):
    t = await ts.create_taxonomy(db, "Created", description="desc", icon="leaf")
    assert t.name == "Created" and t.icon == "leaf"
    updated = await ts.update_taxonomy(db, t.id, {"name": "Renamed", "description": "new"})
    assert updated.name == "Renamed" and updated.description == "new"
    assert await ts.update_taxonomy(db, 99999, {"name": "x"}) is None


async def test_delete_taxonomy(db):
    t = await ts.create_taxonomy(db, "ToDelete")
    assert await ts.delete_taxonomy(db, t.id) is True
    await db.refresh(t)
    assert t.is_active is False
    assert await ts.delete_taxonomy(db, 99999) is False


async def test_get_taxonomy_tree_nested(db):
    t = await ts.create_taxonomy(db, "TreeTax")
    root = await ts.create_node(db, t.id, "R", "Root", sort_order=1)
    child = await ts.create_node(db, t.id, "C", "Child", parent_id=root.id, sort_order=2)
    await ts.create_node(db, t.id, "C2", "Child2", parent_id=root.id, sort_order=1)
    tree = await ts.get_taxonomy_tree(db, t.id)
    assert len(tree) == 1
    assert tree[0]["name"] == "Root"
    assert [c["name"] for c in tree[0]["children"]] == ["Child2", "Child"]
    assert child.parent_id == root.id


async def test_create_update_delete_node(db):
    t = await ts.create_taxonomy(db, "Nodes")
    n = await ts.create_node(db, t.id, "A", "Alpha", description="alpha", sort_order=5)
    assert n.code == "A" and n.sort_order == 5
    updated = await ts.update_node(db, n.id, {"name": "Beta"})
    assert updated.name == "Beta"
    assert await ts.update_node(db, 99999, {"name": "x"}) is None
    assert await ts.delete_node(db, n.id) is True
    assert await ts.delete_node(db, 99999) is False


async def test_list_items_filter_and_search(db):
    item = await _make_item(db, code="LIST-1", common_name="Papaya")
    other = await _make_item(db, code="LIST-2", common_name="Lime")
    all_items = await ts.list_items(db)
    assert {i.id for i in all_items} == {item.id, other.id}
    node_items = await ts.list_items(db, node_id=item.node_id)
    assert {i.id for i in node_items} == {item.id}
    searched = await ts.list_items(db, search="pap")
    assert [i.id for i in searched] == [item.id]


async def test_get_item_and_by_code(db):
    item = await _make_item(db)
    assert (await ts.get_item(db, item.id)).id == item.id
    assert (await ts.get_item_by_code(db, item.code)).id == item.id
    assert await ts.get_item_by_code(db, "NOPE") is None


async def test_create_update_delete_item(db):
    item = await _make_item(db, code="CRUD-1", common_name="Apple")
    created = await ts.create_item(db, item.node_id, "CRUD-2", "Berry", scientific_name="Rubus")
    assert created.code == "CRUD-2" and created.scientific_name == "Rubus"
    updated = await ts.update_item(db, created.id, {"common_name": "Blackberry"})
    assert updated.common_name == "Blackberry"
    assert await ts.update_item(db, 99999, {"common_name": "x"}) is None
    assert await ts.delete_item(db, created.id) is True
    assert await ts.delete_item(db, 99999) is False


async def test_item_names_and_attributes(db):
    item = await _make_item(db)
    n = await ts.add_item_name(db, item.id, "fr", "Mangue", is_primary=True)
    assert n.language == "fr"
    names = await ts.list_item_names(db, item.id)
    assert [x.name for x in names] == ["Mangue"]
    a = await ts.add_item_attribute(db, item.id, "color", "yellow", "hex")
    assert a.key == "color" and a.value == "yellow"
    attrs = await ts.list_item_attributes(db, item.id)
    assert [(x.key, x.unit) for x in attrs] == [("color", "hex")]


async def test_search_taxonomy(db):
    item = await _make_item(db, code="SEARCH-1", common_name="Dragonfruit")
    await ts.add_item_name(db, item.id, "vi", "Thanh Long")
    by_name = await ts.search_taxonomy(db, "dragon")
    assert any(r["id"] == item.id for r in by_name)
    by_alt_name = await ts.search_taxonomy(db, "thanh")
    assert any(r["id"] == item.id for r in by_alt_name)
    by_code = await ts.search_taxonomy(db, "SEARCH-1")
    assert any(r["id"] == item.id for r in by_code)


async def test_suggest_taxonomy_changes(db):
    item = await _make_item(db)
    out = await ts.suggest_taxonomy_changes(db, item.id, {"family": "Anacardiaceae"})
    assert out["status"] == "pending_review"
    assert out["current"]["common_name"] == "Mango"
    assert out["suggested"]["family"] == "Anacardiaceae"
    missing = await ts.suggest_taxonomy_changes(db, 99999, {})
    assert missing["error"] == "Item not found"


async def test_serializers(db):
    item = await _make_item(db)
    await ts.add_item_name(db, item.id, "fr", "Mangue")
    await ts.add_item_attribute(db, item.id, "color", "yellow")
    await db.refresh(item, attribute_names=["names", "attributes"])
    detail = serialize_item_detail(item)
    assert detail["common_name"] == "Mango"
    assert detail["names"][0]["name"] == "Mangue"
    assert detail["attributes"][0]["key"] == "color"
    assert serialize_item(item)["code"] == item.code
    node = await db.get(TaxonomyNode, item.node_id)
    tax = await db.get(Taxonomy, node.taxonomy_id)
    assert serialize_taxonomy(tax)["name"].startswith("T-")


@pytest.mark.parametrize("fn_kwargs", [
    {"name": "Missing", "description": None},
])
async def test_update_missing_returns_none(db, fn_kwargs):
    assert await ts.update_taxonomy(db, 12345, fn_kwargs) is None
