"""Tests for search_service: tokenize, scoring, scan resolution, unified search, autocomplete, analytics."""
from datetime import datetime, timedelta, timezone

from app.models.certificate import Certificate, CertificateStatus, CertificateType
from app.models.product import Product, ProductCategory
from app.models.search import SearchLog
from app.models.taxonomy import ItemAttribute, ItemIdentifierLog, ItemName
from app.models.tracking import (
    Batch,
    BatchStatus,
    Collection,
    CollectionItem,
    Warehouse,
    WarehouseItem,
)
from app.services import search_service as ss


async def _make_item(db, code="APPLE-001", common_name="Apple", scientific_name="Malus domestica",
                     active=True, **kw):
    from app.models.taxonomy import Taxonomy, TaxonomyItem, TaxonomyNode
    t = Taxonomy(name="Search Taxonomy", description="t")
    db.add(t)
    await db.commit()
    await db.refresh(t)
    node = TaxonomyNode(taxonomy_id=t.id, code="N-" + code, name="Node " + common_name)
    db.add(node)
    await db.commit()
    await db.refresh(node)
    item = TaxonomyItem(node_id=node.id, code=code, common_name=common_name,
                        scientific_name=scientific_name, is_active=active, **kw)
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


async def _make_product(db, sku="SKU-APPLE-1", name="Fresh Apple", item_id=None,
                        producer_name="Test Farm", category=ProductCategory.FRESH_PRODUCE,
                        barcode=None):
    p = Product(sku=sku, name=name, item_id=item_id, producer_id=1,
                producer_name=producer_name, category=category, barcode=barcode)
    db.add(p)
    await db.commit()
    await db.refresh(p)
    return p


async def _make_warehouse(db, code="WH-DXB", name="Dubai Cold Store"):
    w = Warehouse(code=code, name=name, city="Dubai", country="AE")
    db.add(w)
    await db.commit()
    await db.refresh(w)
    return w


async def _make_batch(db, batch_number="B-100", product_id=None, quantity=50, status=BatchStatus.ACTIVE,
                      production_date=None, expiry_date=None):
    b = Batch(batch_number=batch_number, product_id=product_id, quantity=quantity,
              status=status, created_by=1)
    if production_date:
        b.production_date = datetime.fromisoformat(production_date)
    if expiry_date:
        b.expiry_date = datetime.fromisoformat(expiry_date)
    db.add(b)
    await db.commit()
    await db.refresh(b)
    return b


async def test_tokenize():
    assert ss._tokenize("Fresh Apples 2024!") == ["fresh", "apples", "2024"]
    assert ss._tokenize("the a an") == []
    assert ss._tokenize("x") == []


def test_levenshtein():
    assert ss._levenshtein("kitten", "kitten") == 0
    assert ss._levenshtein("kitten", "sitting") == 3
    assert ss._levenshtein("abc", "") == 3
    assert ss._levenshtein("", "") == 0


def test_trigram_similarity():
    assert ss._trigram_similarity("apple", "apple") == 1.0
    assert ss._trigram_similarity("apple", "orange") == 0.0
    assert ss._trigram_similarity("ab", "abc") == 0.0


def test_score_field():
    assert ss._score_field("apple", "Apple") == 10.0
    assert ss._score_field("appl", "apple") == 8.0
    assert ss._score_field("ppl", "apple") == 5.0
    assert ss._score_field("xyz", "apple") == 0.0
    assert ss._score_field("apple", None) == 0


async def test_log_search(db):
    await ss.log_search(db, "banana", 3, entity_type="taxonomy", user_id=1,
                        ip_address="127.0.0.1", response_time_ms=12.5)
    row = (await db.execute(__import__("sqlalchemy").select(SearchLog))).scalar_one()
    assert row.query == "banana"
    assert row.result_count == 3


async def test_resolve_scan_code_item_code(db):
    item = await _make_item(db, code="avo-777")
    r = await ss.resolve_scan_code(db, "avo-777")
    assert r["type"] == "taxonomy_item"
    assert r["id"] == item.id


async def test_resolve_scan_code_qr_and_barcode(db):
    item = await _make_item(db, code="QR-1", qr_seed="seed123", barcode_prefix="629")
    r = await ss.resolve_scan_code(db, "seed123")
    assert r["id"] == item.id
    r2 = await ss.resolve_scan_code(db, "629")
    assert r2["id"] == item.id


async def test_resolve_scan_code_identifier_log(db, taxonomy_item):
    db.add(ItemIdentifierLog(item_id=taxonomy_item.id, identifier_type="nfc",
                             identifier_value="nfc-tag-1", is_active=True))
    await db.commit()
    r = await ss.resolve_scan_code(db, "NFC-TAG-1")
    assert r["type"] == "taxonomy_item"
    assert r["id"] == taxonomy_item.id


async def test_resolve_scan_code_product(db):
    p = await _make_product(db, sku="sku-xyz", barcode="4006381333931")
    r = await ss.resolve_scan_code(db, "sku-xyz")
    assert r["type"] == "product"
    assert r["id"] == p.id
    r2 = await ss.resolve_scan_code(db, "4006381333931")
    assert r2["type"] == "product"


async def test_resolve_scan_code_none(db):
    assert await ss.resolve_scan_code(db, "does-not-exist") is None


async def test_unified_search_scan_resolved(db):
    await _make_item(db, code="scan-1")
    out = await ss.unified_search(db, "scan-1")
    assert out["scan_resolved"] is True
    assert out["results"][0]["type"] == "scan_resolved"
    assert out["results"][0]["score"] == 1000


async def test_unified_search_taxonomy_items(db):
    item = await _make_item(db, code="KIWI-1", common_name="Kiwi", scientific_name="Actinidia deliciosa")
    db.add(ItemName(item_id=item.id, language="fr", name="Kiwi francais", is_primary=False))
    await db.commit()
    out = await ss.unified_search(db, "kiwi")
    types = {r["type"] for r in out["results"]}
    assert "taxonomy_item" in types
    assert out["total"] >= 1


async def test_unified_search_entity_type_filter(db):
    await _make_item(db, code="IT-1", common_name="Papaya")
    p = await _make_product(db, sku="SKU-PAPAYA", name="Papaya Fruit")
    await _make_batch(db, "B-PAPAYA", product_id=p.id)
    out = await ss.unified_search(db, "papaya", entity_type="products", include_batches=False)
    assert all(r["type"] == "product" for r in out["results"])
    out_items = await ss.unified_search(db, "papaya", entity_type="items")
    assert all(r["type"] == "taxonomy_item" for r in out_items["results"])


async def test_unified_search_batches_and_warehouses(db):
    p = await _make_product(db, sku="SKU-WH", name="Mangoes")
    b = await _make_batch(db, "B-WH-1", product_id=p.id)
    w = await _make_warehouse(db, code="WH-MG", name="Mango Cold Store")
    item = await _make_item(db, code="MANGO-1", common_name="Mango")
    db.add(WarehouseItem(warehouse_id=w.id, batch_id=b.id, item_id=item.id, quantity=10))
    await db.commit()

    out = await ss.unified_search(db, "mango")
    types = {r["type"] for r in out["results"]}
    assert "batch" in types
    assert "warehouse" in types


async def test_unified_search_certificates(db, taxonomy_item):
    db.add(Certificate(certificate_id="CERT-1", item_id=taxonomy_item.id, type=CertificateType.HALAL,
                       status=CertificateStatus.VERIFIED, issuer_id=1, issuer_name="DM",
                       recipient_entity="Test Co", description="Halal cert"))
    await db.commit()
    out = await ss.unified_search(db, "cert-1")
    assert any(r["type"] == "certificate" for r in out["results"])


async def test_unified_search_collections(db, taxonomy_item):
    c = Collection(name="Tropical Fruits", slug="tropical-fruits")
    db.add(c)
    await db.commit()
    await db.refresh(c)
    db.add(CollectionItem(collection_id=c.id, item_id=taxonomy_item.id))
    await db.commit()
    out = await ss.unified_search(db, "tropical")
    assert any(r["type"] == "collection" for r in out["results"])


async def test_unified_search_suggestion_and_pagination(db):
    item = await _make_item(db, code="AVO-1", common_name="Avocado")
    db.add(ItemName(item_id=item.id, language="en", name="Avocado", is_primary=True))
    db.add(ItemName(item_id=item.id, language="es", name="Aguacate", is_primary=False))
    await db.commit()
    out = await ss.unified_search(db, "avoacdo", page=2)
    assert "suggestion" in out
    assert out["page"] == 2
    assert out["page_size"] == ss.SEARCH_PAGE_SIZE


async def test_search_taxonomy_items_taxonomy_filter(db, taxonomy, taxonomy_node):
    from app.models.taxonomy import TaxonomyItem
    item = TaxonomyItem(node_id=taxonomy_node.id, code="N1", common_name="N1 Name")
    db.add(item)
    await db.commit()
    total, items = await ss.search_taxonomy_items(db, "%N1%", "n1", 20, 0, taxonomy.id)
    assert total == 1
    assert items[0]["common_name"] == "N1 Name"


async def test_search_products(db):
    await _make_product(db, sku="SKU-A", name="Product Alpha", producer_name="Farm A")
    total, items = await ss.search_products(db, "%alpha%", "alpha", 20, 0)
    assert total == 1
    assert items[0]["sku"] == "SKU-A"
    assert items[0]["category"] == "fresh_produce"


async def test_search_batches(db):
    p = await _make_product(db, sku="SKU-B", name="Beta Product")
    await _make_batch(db, "B-BETA", product_id=p.id, production_date="2024-01-01",
                      expiry_date="2025-01-01")
    total, items = await ss.search_batches(db, "%B-BETA%", "b-beta", 20, 0)
    assert total == 1
    assert items[0]["batch_number"] == "B-BETA"
    assert items[0]["product_name"] == "Beta Product"
    assert items[0]["production_date"].startswith("2024")


async def test_search_warehouses(db):
    await _make_warehouse(db)
    total, items = await ss.search_warehouses(db, "%Dubai%", "dubai", 20, 0)
    assert total == 1
    assert items[0]["name"] == "Dubai Cold Store"


async def test_search_certificates(db, taxonomy_item):
    db.add(Certificate(certificate_id="C-999", item_id=taxonomy_item.id, type=CertificateType.ORGANIC,
                       status=CertificateStatus.ISSUED, issuer_id=1, issuer_name="GlobalCert",
                       recipient_entity="Acme"))
    await db.commit()
    total, items = await ss.search_certificates(db, "%C-999%", "c-999", 20, 0)
    assert total == 1
    assert items[0]["issuer_name"] == "GlobalCert"


async def test_search_collections(db, taxonomy_item):
    c = Collection(name="Green Basket", slug="green-basket")
    db.add(c)
    await db.commit()
    await db.refresh(c)
    db.add(CollectionItem(collection_id=c.id, item_id=taxonomy_item.id))
    await db.commit()
    total, items = await ss.search_collections(db, "%green%", "green", 20, 0)
    assert total == 1
    assert items[0]["item_count"] == 1


async def test_autocomplete_search(db):
    item = await _make_item(db, code="MANGO-9", common_name="Mango M", scientific_name="M. indica")
    db.add(ItemName(item_id=item.id, language="fr", name="Mango francais", is_primary=False))
    p = await _make_product(db, sku="SKU-MANGO", name="Mango Product")
    await _make_batch(db, "B-MANGO", product_id=p.id)
    await db.commit()
    results = await ss.autocomplete_search(db, "mango")
    types = {r["type"] for r in results}
    assert "taxonomy_item" in types
    assert "multilingual_name" in types
    assert "product" in types
    assert "batch" in types
    results2 = await ss.autocomplete_search(db, "mango", include_batches=False)
    assert all(r["type"] != "batch" for r in results2)


async def test_get_search_analytics(db):
    now = datetime.now(timezone.utc) - timedelta(hours=1)
    db.add_all([
        SearchLog(query="mango", result_count=5, response_time_ms=10, created_at=now),
        SearchLog(query="mango", result_count=3, response_time_ms=20, created_at=now),
        SearchLog(query="nope", result_count=0, response_time_ms=5, created_at=now),
    ])
    await db.commit()
    out = await ss.get_search_analytics(db, days=7)
    assert out["total_queries"] == 3
    assert out["top_queries"][0]["query"] == "mango"
    assert out["top_queries"][0]["count"] == 2
    assert out["zero_result_queries"][0]["query"] == "nope"
    assert out["avg_response_time_ms"] == round((10 + 20 + 5) / 3, 2)


async def test_get_taxonomy_item_detail(db, taxonomy_node):
    from app.models.taxonomy import TaxonomyItem
    item = TaxonomyItem(node_id=taxonomy_node.id, code="D-1", common_name="Durian",
                        scientific_name="Durio zibethinus")
    db.add(item)
    await db.commit()
    await db.refresh(item)
    db.add_all([
        ItemName(item_id=item.id, language="en", name="Durian", is_primary=True),
        ItemAttribute(item_id=item.id, key="taste", value="creamy"),
    ])
    p = await _make_product(db, sku="SKU-DURIAN", name="Durian", item_id=item.id)
    w = await _make_warehouse(db, code="WH-SG")
    b = await _make_batch(db, "B-DURIAN", product_id=p.id)
    db.add(WarehouseItem(warehouse_id=w.id, batch_id=b.id, item_id=item.id, quantity=7, location_zone="Z1"))
    await db.commit()

    detail = await ss.get_taxonomy_item_detail(db, item.id)
    assert detail["common_name"] == "Durian"
    assert detail["names"][0]["name"] == "Durian"
    assert detail["attributes"][0]["key"] == "taste"
    assert len(detail["linked_products"]) == 1
    assert len(detail["linked_batches"]) == 1
    assert detail["linked_batches"][0]["locations"][0]["warehouse_name"] == "Dubai Cold Store"


async def test_get_taxonomy_item_detail_inactive(db, taxonomy_item):
    taxonomy_item.is_active = False
    await db.commit()
    assert await ss.get_taxonomy_item_detail(db, taxonomy_item.id) is None
    assert await ss.get_taxonomy_item_detail(db, 99999) is None


async def test_get_taxonomy_item_by_code(db, taxonomy_item):
    detail = await ss.get_taxonomy_item_by_code(db, taxonomy_item.code)
    assert detail["id"] == taxonomy_item.id
    assert await ss.get_taxonomy_item_by_code(db, "NOPE") is None


async def test_unified_search_negative_stock_and_empty(db):
    out = await ss.unified_search(db, "zzzz_not_here")
    assert out["total"] == 0
    assert out["suggestion"] is None


async def test_suggestion_short_query(db):
    assert await ss._suggestion(db, "xy") is None
