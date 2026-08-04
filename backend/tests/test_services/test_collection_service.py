"""Tests for collection_service."""
import sys
import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.taxonomy import Taxonomy, TaxonomyItem, TaxonomyNode
from app.models.tracking import Collection, CollectionItem, FeedSource
from app.services import collection_service as cs


async def _make_item(db: AsyncSession, node: TaxonomyNode, code: str,
                     common_name: str, local_uses: str | None = None,
                     phylum: str | None = None) -> TaxonomyItem:
    item = TaxonomyItem(node_id=node.id, code=code, common_name=common_name,
                        scientific_name=f"{common_name} spp", local_uses=local_uses, phylum=phylum)
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


def test_slugify():
    assert cs.slugify("  Tropical Fruits! ") == "tropical-fruits"
    assert cs.slugify("A & B 2024") == "a-b-2024"
    assert cs.slugify("underscore_case") == "underscore-case"


async def test_list_collections(db):
    c1 = Collection(name="One", slug="one", sort_order=1)
    c2 = Collection(name="Two", slug="two", sort_order=0)
    c3 = Collection(name="Hidden", slug="hidden", is_active=False)
    db.add_all([c1, c2, c3])
    await db.commit()
    out = await cs.list_collections(db)
    assert out["total"] == 2
    assert [c["name"] for c in out["collections"]] == ["Two", "One"]
    assert out["total_pages"] == 1


async def test_get_collection(db):
    node = await _node(db)
    item = await _make_item(db, node, "G-1", "Mango")
    coll = Collection(name="Tropical", slug="tropical")
    db.add(coll)
    await db.commit()
    await db.refresh(coll)
    db.add(CollectionItem(collection_id=coll.id, item_id=item.id, sort_order=2))
    await db.commit()
    out = await cs.get_collection(db, coll.id)
    assert out["name"] == "Tropical"
    assert out["items"][0]["common_name"] == "Mango"
    assert out["items"][0]["sort_order"] == 2
    assert await cs.get_collection(db, 99999) is None


async def _node(db: AsyncSession) -> TaxonomyNode:
    t = Taxonomy(name=f"T-{uuid.uuid4().hex[:8]}")
    db.add(t)
    await db.commit()
    await db.refresh(t)
    n = TaxonomyNode(taxonomy_id=t.id, code="N", name="Fruits")
    db.add(n)
    await db.commit()
    await db.refresh(n)
    return n


async def test_create_collection_slug_unique(db, admin_user, viewer_user):
    c1 = await cs.create_collection(db, admin_user, "Tropical Fruits")
    c2 = await cs.create_collection(db, admin_user, "Tropical Fruits")
    assert c1.slug == "tropical-fruits"
    assert c2.slug.startswith("tropical-fruits-")
    with pytest.raises(PermissionError):
        await cs.create_collection(db, viewer_user, "Nope")


async def test_update_collection(db, admin_user, viewer_user):
    c = await cs.create_collection(db, admin_user, "Old Name")
    updated = await cs.update_collection(db, admin_user, c.id, {"name": "New Name", "description": "d"})
    assert updated.name == "New Name"
    assert updated.slug == "new-name"
    with pytest.raises(ValueError):
        await cs.update_collection(db, admin_user, 99999, {"name": "x"})
    with pytest.raises(PermissionError):
        await cs.update_collection(db, viewer_user, c.id, {"name": "y"})


async def test_delete_collection(db, admin_user, viewer_user):
    c = await cs.create_collection(db, admin_user, "ToDelete")
    with pytest.raises(PermissionError):
        await cs.delete_collection(db, viewer_user, c.id)
    with pytest.raises(ValueError):
        await cs.delete_collection(db, admin_user, 99999)
    await cs.delete_collection(db, admin_user, c.id)
    await db.refresh(c)
    assert c.is_active is False


async def test_add_remove_item(db, admin_user, viewer_user):
    node = await _node(db)
    item = await _make_item(db, node, "AD-1", "Mango")
    coll = await cs.create_collection(db, admin_user, "Tropical")
    ci = await cs.add_item_to_collection(db, admin_user, coll.id, item.id, sort_order=1, notes="n")
    assert ci.sort_order == 1 and ci.notes == "n"
    with pytest.raises(ValueError):
        await cs.add_item_to_collection(db, admin_user, 99999, item.id)
    with pytest.raises(ValueError):
        await cs.add_item_to_collection(db, admin_user, coll.id, 99999)
    with pytest.raises(ValueError):
        await cs.add_item_to_collection(db, admin_user, coll.id, item.id)
    with pytest.raises(PermissionError):
        await cs.add_item_to_collection(db, viewer_user, coll.id, item.id)
    with pytest.raises(PermissionError):
        await cs.remove_item_from_collection(db, viewer_user, ci.id)
    with pytest.raises(ValueError):
        await cs.remove_item_from_collection(db, admin_user, 99999)
    await cs.remove_item_from_collection(db, admin_user, ci.id)
    out = await cs.get_collection(db, coll.id)
    assert out["items"] == []


async def test_run_ai_feed_not_found(db, admin_user):
    with pytest.raises(ValueError):
        await cs.run_ai_feed(db, 99999)
    fs = FeedSource(name="feed", url="https://feeds.example.com/rss", is_active=False)
    db.add(fs)
    await db.commit()
    await db.refresh(fs)
    with pytest.raises(ValueError):
        await cs.run_ai_feed(db, fs.id)


async def test_run_ai_feed_success(db, monkeypatch):
    node = await _node(db)
    await _make_item(db, node, "RF-1", "Mango")
    feed = FeedSource(name="Tropical Feed", url="https://feeds.example.com/rss")
    db.add(feed)
    await db.commit()
    await db.refresh(feed)

    class FakeResponse:
        def __init__(self, text):
            self.text = text
        def raise_for_status(self):
            pass
    class FakeClient:
        def __init__(self, text):
            self.text = text
        async def __aenter__(self):
            return self
        async def __aexit__(self, *a):
            return False
        async def get(self, url):
            return FakeResponse(self.text)
    class FakeHttpx:
        def __init__(self):
            self.client_text = None
        def AsyncClient(self, timeout):
            return FakeClient(self.client_text)
    fake = FakeHttpx()
    fake.client_text = (
        "<rss><channel><item><title>Mango</title>"
        "<link>https://feeds.example.com/article</link>"
        "<description>Fresh mangoes</description></item></channel></rss>"
    )
    monkeypatch.setitem(sys.modules, "httpx", fake)
    out = await cs.run_ai_feed(db, feed.id)
    assert out["collection_name"].startswith("Tropical Feed")
    coll = await cs.get_collection(db, out["collection_id"])
    assert [i["common_name"] for i in coll["items"]] == ["Mango"]


async def test_run_ai_feed_fetch_error(db, monkeypatch):
    await _node(db)
    feed = FeedSource(name="Broken Feed", url="https://feeds.example.com/rss")
    db.add(feed)
    await db.commit()
    await db.refresh(feed)
    class BadClient:
        async def __aenter__(self):
            return self
        async def __aexit__(self, *a):
            return False
        async def get(self, url):
            raise OSError("boom")
    class FakeHttpx:
        def AsyncClient(self, timeout):
            return BadClient()
    monkeypatch.setitem(sys.modules, "httpx", FakeHttpx())
    with pytest.raises(ValueError):
        await cs.run_ai_feed(db, feed.id)


def test_assortment_subsets():
    assert cs._assortment_subsets([1, 2, 3], 0) == []
    assert cs._assortment_subsets([], 3) == []
    out = cs._assortment_subsets([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12], 8)
    assert len(out) == 8
    assert out[0] == [1, 2, 3]
    wrap = cs._assortment_subsets([1, 2], 3)
    assert len(wrap) == 3
    assert all(len(s) == 2 for s in wrap)


def test_theme_match():
    item = TaxonomyItem(node_id=1, code="X", common_name="Juice", local_uses="juice drink")
    item.phylum = "Chordata"
    assert cs._theme_match(item, None, {"Chordata"}) is True
    assert cs._theme_match(item, None, {"Mollusca"}) is False
    assert cs._theme_match(item, None, None) is False


async def test_seed_collections_from_taxonomy(db):
    t = Taxonomy(name=f"Seed-{uuid.uuid4().hex[:8]}")
    db.add(t)
    await db.commit()
    await db.refresh(t)
    node = TaxonomyNode(taxonomy_id=t.id, code="veg", name="Vegetables", sort_order=1)
    db.add(node)
    await db.commit()
    await db.refresh(node)
    for i in range(12):
        local_uses = "juice drink" if i < 3 else None
        await _make_item(db, node, f"V-{i}", f"Veg {i}", local_uses=local_uses)
    first = await cs.seed_collections_from_taxonomy(db, t.id)
    assert first["nodes"] == 1
    assert first["collections"] == 10
    second = await cs.seed_collections_from_taxonomy(db, t.id)
    assert second["collections"] == 0
    assert second["items"] == 0
    collections = await cs.list_collections(db)
    names = [c["name"] for c in collections["collections"]]
    assert any("Beverage & Drink" in n for n in names)
    assert any("Selection 1" in n for n in names)


async def test_seed_collections_empty_taxonomy(db):
    out = await cs.seed_collections_from_taxonomy(db, 99999)
    assert out == {"nodes": 0, "collections": 0, "items": 0}


async def test_feed_source_crud(db, admin_user, viewer_user):
    fs = await cs.create_feed_source(db, admin_user, "Feed A", "https://a.com/rss", feed_type="rss")
    assert fs.name == "Feed A"
    with pytest.raises(PermissionError):
        await cs.create_feed_source(db, viewer_user, "Feed B", "https://b.com/rss")
    feeds = await cs.list_feed_sources(db)
    assert [f["id"] for f in feeds] == [fs.id]
    with pytest.raises(ValueError):
        await cs.delete_feed_source(db, admin_user, 99999)
    with pytest.raises(PermissionError):
        await cs.delete_feed_source(db, viewer_user, fs.id)
    await cs.delete_feed_source(db, admin_user, fs.id)
    assert await cs.list_feed_sources(db) == []
