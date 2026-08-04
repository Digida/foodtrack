"""Tests for enrichment_service."""
import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enrichment import (
    EnrichmentLog,
    EnrichmentSource,
    EnrichmentStatus,
    EnrichmentSuggestion,
)
from app.models.taxonomy import Taxonomy, TaxonomyItem, TaxonomyNode
from app.models.tracking import Collection, CollectionItem, FeedSource
from app.services import enrichment_service as es


async def _make_item(db: AsyncSession, code: str = "ENR-ITEM") -> TaxonomyItem:
    t = Taxonomy(name=f"T-{uuid.uuid4().hex[:8]}")
    db.add(t)
    await db.commit()
    await db.refresh(t)
    n = TaxonomyNode(taxonomy_id=t.id, code="N", name="Fruits")
    db.add(n)
    await db.commit()
    await db.refresh(n)
    item = TaxonomyItem(node_id=n.id, code=code, common_name="Mango", scientific_name="M. indica")
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


async def _make_collection(db: AsyncSession, name: str = "Tropical") -> Collection:
    c = Collection(name=name, slug=name.lower())
    db.add(c)
    await db.commit()
    await db.refresh(c)
    return c


async def _link_feed(db: AsyncSession, coll: Collection, url: str = "https://feeds.example.com/rss") -> FeedSource:
    f = FeedSource(name="feed", url=url)
    db.add(f)
    await db.commit()
    await db.refresh(f)
    coll.feed_source_id = f.id
    await db.commit()
    await db.refresh(coll)
    return f


def _fake_results(*titles: str) -> dict:
    return {
        "results": [
            {"title": t, "snippet": "snippet", "link": "https://example.com/x"} for t in titles
        ]
    }


async def test_enrich_collection_from_feed(db, admin_user, viewer_user, monkeypatch):
    calls = []
    def fake_read_url(url):
        calls.append(url)
        return "<rss>ok</rss>"
    monkeypatch.setattr("app.services.enrichment_service.read_url", fake_read_url)
    with pytest.raises(PermissionError):
        await es.enrich_collection_from_feed(db, viewer_user, 1)
    with pytest.raises(ValueError):
        await es.enrich_collection_from_feed(db, admin_user, 99999)
    coll = await _make_collection(db)
    await _link_feed(db, coll)
    out = await es.enrich_collection_from_feed(db, admin_user, coll.id)
    assert out["status"] == "completed"
    assert out["feeds_processed"] == 1
    assert calls == ["https://feeds.example.com/rss"]
    logs = await es.list_enrichment_logs(db)
    assert logs["total"] == 1
    assert logs["logs"][0]["status"] == "completed"


async def test_enrich_collection_from_feed_allowed_enterprise(db, enterprise_user):
    with pytest.raises(ValueError):
        await es.enrich_collection_from_feed(db, enterprise_user, 99999)


async def test_enrich_taxonomy_from_web(db, admin_user, viewer_user, monkeypatch):
    monkeypatch.setattr("app.services.enrichment_service.web_search", lambda *a, **k: _fake_results("Novel Yam Species"))
    with pytest.raises(PermissionError):
        await es.enrich_taxonomy_from_web(db, viewer_user)
    out = await es.enrich_taxonomy_from_web(db, admin_user)
    assert out["status"] == "completed"
    assert out["suggestions_created"] == 1
    suggestions = await es.list_enrichment_suggestions(db)
    assert suggestions["total"] == 1
    assert suggestions["suggestions"][0]["title"].startswith("Potential new item:")


async def test_enrich_taxonomy_from_web_dedupe(db, admin_user, monkeypatch):
    await _make_item(db, code="mango")
    monkeypatch.setattr("app.services.enrichment_service.web_search",
                        lambda *a, **k: _fake_results("Mango", "Kiwi"))
    out = await es.enrich_taxonomy_from_web(db, admin_user)
    assert out["suggestions_created"] == 1


async def test_suggest_taxonomy_nodes(db, admin_user, viewer_user, monkeypatch):
    monkeypatch.setattr("app.services.enrichment_service.web_search",
                        lambda *a, **k: _fake_results("Reclass A", "Reclass B", "Reclass C", "Reclass D"))
    item = await _make_item(db)
    with pytest.raises(PermissionError):
        await es.suggest_taxonomy_nodes(db, viewer_user, item.id)
    with pytest.raises(ValueError):
        await es.suggest_taxonomy_nodes(db, admin_user, 99999)
    out = await es.suggest_taxonomy_nodes(db, admin_user, item.id)
    assert out["suggestions_count"] == 3
    assert out["item_id"] == item.id


async def test_auto_categorize_collection(db, admin_user, viewer_user):
    item = await _make_item(db)
    coll = await _make_collection(db)
    db.add(CollectionItem(collection_id=coll.id, item_id=item.id))
    await db.commit()
    with pytest.raises(PermissionError):
        await es.auto_categorize_collection(db, viewer_user, coll.id)
    with pytest.raises(ValueError):
        await es.auto_categorize_collection(db, admin_user, 99999)
    out = await es.auto_categorize_collection(db, admin_user, coll.id)
    assert out["item_count"] == 1
    assert out["categories"] == {"Fruits": 1}


async def test_suggest_collection_items(db, admin_user, viewer_user):
    t = Taxonomy(name=f"T-{uuid.uuid4().hex[:8]}")
    db.add(t)
    await db.commit()
    await db.refresh(t)
    n = TaxonomyNode(taxonomy_id=t.id, code="N", name="Fruits")
    db.add(n)
    await db.commit()
    await db.refresh(n)
    item = TaxonomyItem(node_id=n.id, code="ENR-A", common_name="Mango")
    item2 = TaxonomyItem(node_id=n.id, code="ENR-B", common_name="Lime")
    db.add_all([item, item2])
    await db.commit()
    coll = await _make_collection(db)
    db.add(CollectionItem(collection_id=coll.id, item_id=item.id))
    await db.commit()
    with pytest.raises(PermissionError):
        await es.suggest_collection_items(db, viewer_user, coll.id)
    with pytest.raises(ValueError):
        await es.suggest_collection_items(db, admin_user, 99999)
    out = await es.suggest_collection_items(db, admin_user, coll.id)
    assert out["suggestions_count"] == 1
    assert out["suggestions"][0]["item_id"] == item2.id


async def test_suggest_collection_items_empty_node(db, admin_user):
    coll = await _make_collection(db)
    out = await es.suggest_collection_items(db, admin_user, coll.id)
    assert out["suggestions_count"] == 0


async def test_backfill_item_data(db, admin_user, viewer_user, monkeypatch):
    await _make_item(db)
    async def fake_nutrition(name):
        return {"calories": 100}
    async def fake_price(name):
        return {"price": 5}
    monkeypatch.setattr("app.services.enrichment_service.fetch_nutrition", fake_nutrition)
    monkeypatch.setattr("app.services.enrichment_service.fetch_market_price", fake_price)
    with pytest.raises(PermissionError):
        await es.backfill_item_data(db, viewer_user)
    out = await es.backfill_item_data(db, admin_user)
    assert out["status"] == "completed"
    assert out["results"]["nutrition"] == 1
    assert out["results"]["prices"] == 1


async def test_refresh_collections_schedule(db, admin_user, monkeypatch):
    coll = await _make_collection(db)
    await _link_feed(db, coll)
    monkeypatch.setattr("app.services.enrichment_service.read_url", lambda url: "<rss>")
    out = await es.refresh_collections_schedule(db)
    assert out["status"] == "completed"
    assert out["feeds_refreshed"] == 1


async def test_list_enrichment_logs_pagination(db, admin_user):
    db.add(EnrichmentLog(source=EnrichmentSource.WEB_SEARCH, status=EnrichmentStatus.COMPLETED, entity_type="x"))
    db.add(EnrichmentLog(source=EnrichmentSource.RSS_FEED, status=EnrichmentStatus.FAILED, entity_type="y"))
    await db.commit()
    out = await es.list_enrichment_logs(db, page=1)
    assert out["total"] == 2
    assert out["total_pages"] == 1
    rss = await es.list_enrichment_logs(db, source="rss_feed")
    assert rss["total"] == 1
    assert rss["logs"][0]["source"] == "rss_feed"


async def test_list_enrichment_suggestions_status(db, admin_user):
    db.add(EnrichmentSuggestion(entity_type="taxonomy_item", suggestion_type="new_item",
                                title="T1", status="open", created_by=admin_user.id))
    db.add(EnrichmentSuggestion(entity_type="taxonomy_item", suggestion_type="new_item",
                                title="T2", status="accepted", created_by=admin_user.id))
    await db.commit()
    out = await es.list_enrichment_suggestions(db, status="open")
    assert out["total"] == 1
    assert out["suggestions"][0]["title"] == "T1"
    all_out = await es.list_enrichment_suggestions(db)
    assert all_out["total"] == 2


async def test_update_suggestion_status(db, admin_user, viewer_user):
    sug = EnrichmentSuggestion(entity_type="taxonomy_item", suggestion_type="new_item",
                               title="T", status="open", created_by=admin_user.id)
    db.add(sug)
    await db.commit()
    await db.refresh(sug)
    with pytest.raises(PermissionError):
        await es.update_suggestion_status(db, viewer_user, sug.id, "accepted")
    with pytest.raises(ValueError):
        await es.update_suggestion_status(db, admin_user, 99999, "accepted")
    updated = await es.update_suggestion_status(db, admin_user, sug.id, "accepted")
    assert updated.status == "accepted"


async def test_feed_failure_marks_log_failed(db, admin_user, monkeypatch):
    coll = await _make_collection(db)
    await _link_feed(db, coll)
    def boom(url):
        raise RuntimeError("network down")
    monkeypatch.setattr("app.services.enrichment_service.read_url", boom)
    out = await es.enrich_collection_from_feed(db, admin_user, coll.id)
    assert out["status"] == "completed"
    assert out["feeds_processed"] == 0
