"""Tests for item_enrichment_service."""
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.certificate import Certificate, CertificateStatus, CertificateType
from app.models.inventory import ItemInventory
from app.models.product import Product, ProductCategory
from app.models.taxonomy import Taxonomy, TaxonomyItem, TaxonomyNode
from app.models.tracking import (
    Batch,
    BatchStatus,
    ItemShipmentStatus,
    ShipmentBatch,
    ShipmentTrackingEvent,
    Warehouse,
    WarehouseItem,
)
from app.services import item_enrichment_service as ies


async def _make_item(db: AsyncSession, code: str = "IE-ITEM", common_name: str = "Mango") -> TaxonomyItem:
    t = Taxonomy(name=f"T-{uuid.uuid4().hex[:8]}")
    db.add(t)
    await db.commit()
    await db.refresh(t)
    n = TaxonomyNode(taxonomy_id=t.id, code="N", name="Fruits")
    db.add(n)
    await db.commit()
    await db.refresh(n)
    item = TaxonomyItem(node_id=n.id, code=code, common_name=common_name,
                        scientific_name="M. indica", local_uses="juice fruit")
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


async def _make_batch(db: AsyncSession, item: TaxonomyItem) -> Batch:
    p = Product(sku=f"SKU-{uuid.uuid4().hex[:6]}", name="Box", category=ProductCategory.OTHER,
                item_id=item.id, producer_id=1, producer_name="Farm")
    db.add(p)
    await db.commit()
    await db.refresh(p)
    b = Batch(batch_number=f"B-{uuid.uuid4().hex[:6]}", product_id=p.id, item_id=item.id,
              quantity=10, created_by=1, status=BatchStatus.ACTIVE)
    db.add(b)
    await db.commit()
    await db.refresh(b)
    return b


async def _make_warehouse(db: AsyncSession) -> Warehouse:
    w = Warehouse(code=f"W-{uuid.uuid4().hex[:6]}", name="Warehouse")
    db.add(w)
    await db.commit()
    await db.refresh(w)
    return w


async def test_enrich_from_web(db, admin_user, viewer_user, monkeypatch):
    item = await _make_item(db)
    calls = []
    async def fake_translate(text, target_lang):
        calls.append(target_lang)
        return {"translated_text": f"trans-{target_lang}"}
    async def fake_nutrition(name):
        return {"calories": 50}
    async def fake_price(name):
        return {"price": 2}
    async def fake_weather(location):
        calls.append(("weather", location))
        return {"temp": 30}
    def fake_search(*a, **k):
        return {"results": [{"title": "Mango info", "link": "https://example.com/mango", "snippet": "s"}]}
    def fake_read(url):
        return "content"
    monkeypatch.setattr("app.services.item_enrichment_service.web_search", fake_search)
    monkeypatch.setattr("app.services.item_enrichment_service.read_url", fake_read)
    monkeypatch.setattr("app.services.item_enrichment_service.translate_text", fake_translate)
    monkeypatch.setattr("app.services.item_enrichment_service.fetch_nutrition", fake_nutrition)
    monkeypatch.setattr("app.services.item_enrichment_service.fetch_market_price", fake_price)
    monkeypatch.setattr("app.services.item_enrichment_service.fetch_weather", fake_weather)
    with pytest.raises(PermissionError):
        await ies.enrich_from_web(db, viewer_user, item.id)
    with pytest.raises(ValueError):
        await ies.enrich_from_web(db, admin_user, 99999)
    out = await ies.enrich_from_web(db, admin_user, item.id)
    assert out["sources_consulted"] == 1
    assert out["nutrition_added"] == 1
    assert out["prices_added"] == 1
    assert out["translations_added"] == 6
    assert any(isinstance(c, tuple) and c[0] == "weather" for c in calls)


async def test_enrich_from_web_skip_same_translation(db, admin_user, monkeypatch):
    item = await _make_item(db)
    async def fake_translate(text, target_lang):
        return {"translated_text": text}
    async def fake_nutrition(name):
        return None
    async def fake_price(name):
        return None
    async def fake_weather(location):
        return {}
    monkeypatch.setattr("app.services.item_enrichment_service.web_search", lambda *a, **k: {"results": []})
    monkeypatch.setattr("app.services.item_enrichment_service.translate_text", fake_translate)
    monkeypatch.setattr("app.services.item_enrichment_service.fetch_nutrition", fake_nutrition)
    monkeypatch.setattr("app.services.item_enrichment_service.fetch_market_price", fake_price)
    monkeypatch.setattr("app.services.item_enrichment_service.fetch_weather", fake_weather)
    out = await ies.enrich_from_web(db, admin_user, item.id)
    assert out["translations_added"] == 0
    assert out["nutrition_added"] == 0


async def test_suggest_item_classification(db, monkeypatch):
    def fake_search(query, max_results=5):
        return {"results": [{
            "title": "Mango classification",
            "link": "https://example.com/mango",
            "snippet": "The genus Mangifera family Anacardiaceae order Sapindales",
        }]}
    monkeypatch.setattr("app.services.item_enrichment_service.web_search", fake_search)
    t = Taxonomy(name=f"T-{uuid.uuid4().hex[:8]}")
    db.add(t)
    await db.commit()
    await db.refresh(t)
    n = TaxonomyNode(taxonomy_id=t.id, code="N", name="Anacardiaceae")
    db.add(n)
    await db.commit()
    out = await ies.suggest_item_classification(db, "Mango")
    assert out["query"] == "Mango"
    assert len(out["suggested_nodes"]) >= 2
    assert any(s["value"] == "Anacardiaceae" for s in out["suggested_nodes"])
    assert any(s["value"] == "Mangifera" for s in out["suggested_nodes"])
    assert len(out["existing_matches"]) >= 1


async def test_detect_anomalies(db, admin_user, viewer_user):
    item = await _make_item(db)
    with pytest.raises(PermissionError):
        await ies.detect_anomalies(db, viewer_user, item.id)
    with pytest.raises(ValueError):
        await ies.detect_anomalies(db, admin_user, 99999)
    out = await ies.detect_anomalies(db, admin_user, item.id)
    assert out["anomaly_count"] == 0


async def test_detect_anomalies_all_cases(db, admin_user):
    item = await _make_item(db)
    batch = await _make_batch(db, item)
    wh = await _make_warehouse(db)
    db.add(WarehouseItem(warehouse_id=wh.id, batch_id=batch.id, item_id=item.id, quantity=-5))
    db.add(ShipmentBatch(shipment_id=1, batch_id=batch.id, item_id=item.id, quantity=3,
                         item_shipment_status=ItemShipmentStatus.EXCEPTION))
    db.add(ItemInventory(item_id=item.id, warehouse_id=wh.id, total_quantity=-2))
    past = datetime.now(timezone.utc) - timedelta(days=30)
    db.add(Certificate(certificate_id="FT-EXPIRED", item_id=item.id, type=CertificateType.HALAL,
                       status=CertificateStatus.ISSUED, issuer_id=1, issuer_name="Admin",
                       expiry_date=past))
    for i in range(55):
        db.add(ShipmentTrackingEvent(shipment_id=1, item_id=item.id, status="in_transit",
                                     event_timestamp=datetime.now(timezone.utc)))
    await db.commit()
    out = await ies.detect_anomalies(db, admin_user, item.id)
    types = {a["type"] for a in out["anomalies"]}
    assert "negative_stock" in types
    assert "shipment_anomaly" in types
    assert "negative_inventory" in types
    assert "expired_certificate" in types
    assert "high_event_volume" in types


async def test_detect_anomalies_revoked_certificate(db, admin_user):
    item = await _make_item(db)
    db.add(Certificate(certificate_id="FT-REV", item_id=item.id, type=CertificateType.ORGANIC,
                       status=CertificateStatus.REVOKED, issuer_id=1, issuer_name="Admin"))
    await db.commit()
    out = await ies.detect_anomalies(db, admin_user, item.id)
    assert any(a["type"] == "certificate_status" for a in out["anomalies"])
