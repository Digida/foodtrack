import logging
import time
import re
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, or_, and_, func, String
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.taxonomy import TaxonomyNode, TaxonomyItem, ItemName, ItemAttribute, ItemIdentifierLog
from app.models.product import Product
from app.models.tracking import Batch, Warehouse, WarehouseItem, Collection, CollectionItem
from app.models.certificate import Certificate
from app.models.search import SearchLog
from app.services.seo_service import build_json_ld_taxonomy_item, build_json_ld_product, build_json_ld_batch

logger = logging.getLogger(__name__)

PAGE_SIZE = 20
SEARCH_PAGE_SIZE = 24

STOPWORDS: set[str] = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall", "can", "need", "dare", "ought",
    "used", "to", "of", "in", "for", "on", "with", "at", "by", "from",
    "as", "into", "through", "during", "before", "after", "above", "below",
    "between", "out", "off", "over", "under", "again", "further", "then",
    "once", "here", "there", "when", "where", "why", "how", "all", "each",
    "every", "both", "few", "more", "most", "other", "some", "such", "no",
    "nor", "not", "only", "own", "same", "so", "than", "too", "very",
    "just", "because", "but", "and", "or", "if", "while", "although",
}

PRIMARY_LANGUAGES = {"en", "ar", "scientific"}


def _tokenize(term: str) -> list[str]:
    cleaned = re.sub(r'[^\w\s\-\.]', ' ', term.lower())
    return [t for t in cleaned.split() if t not in STOPWORDS and len(t) > 1]


def _levenshtein(a: str, b: str) -> int:
    if len(a) < len(b):
        a, b = b, a
    if not b:
        return len(a)
    prev = range(len(b) + 1)
    for i, ca in enumerate(a):
        curr = [i + 1]
        for j, cb in enumerate(b):
            curr.append(min(curr[j] + 1, prev[j + 1] + 1, prev[j] + (ca != cb)))
        prev = curr
    return prev[-1]


def _trigram_similarity(a: str, b: str) -> float:
    def trigrams(s: str) -> set[str]:
        return {s[i:i + 3] for i in range(len(s) - 2)}
    ta = trigrams(a.lower())
    tb = trigrams(b.lower())
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / max(len(ta | tb), 1)


def _score_field(term_lower: str, field: str | None, exact_boost: float = 10.0) -> float:
    if not field:
        return 0
    fl = field.lower()
    if term_lower == fl:
        return exact_boost
    if fl.startswith(term_lower):
        return exact_boost * 0.8
    if term_lower in fl:
        return exact_boost * 0.5
    trigram = _trigram_similarity(term_lower, fl)
    if trigram > 0.4:
        return exact_boost * 0.3 * trigram
    return 0


async def log_search(
    db: AsyncSession, query: str, result_count: int,
    entity_type: str | None = None, user_id: int | None = None,
    ip_address: str | None = None, response_time_ms: float | None = None,
):
    log = SearchLog(
        query=query, result_count=result_count,
        entity_type=entity_type, user_id=user_id,
        ip_address=ip_address, response_time_ms=response_time_ms,
    )
    db.add(log)
    await db.commit()


async def resolve_scan_code(db: AsyncSession, code: str) -> dict | None:
    code_lower = code.lower().strip()

    item = await db.execute(
        select(TaxonomyItem).where(
            TaxonomyItem.is_active == True,
            or_(
                TaxonomyItem.code == code_lower,
                TaxonomyItem.qr_seed == code_lower,
                TaxonomyItem.barcode_prefix == code_lower,
            ),
        ).limit(1)
    )
    item = item.scalar_one_or_none()
    if item:
        return {"type": "taxonomy_item", "id": item.id, "label": item.common_name, "code": item.code}

    ident = await db.execute(
        select(ItemIdentifierLog).where(
            ItemIdentifierLog.is_active == True,
            ItemIdentifierLog.identifier_value == code_lower,
        ).limit(1)
    )
    ident = ident.scalar_one_or_none()
    if ident:
        return {"type": "taxonomy_item", "id": ident.item_id, "label": f"Identifier {code}", "code": code}

    product = await db.execute(
        select(Product).where(
            Product.is_active == True,
            or_(Product.sku == code_lower, Product.barcode == code_lower),
        ).limit(1)
    )
    product = product.scalar_one_or_none()
    if product:
        return {"type": "product", "id": product.id, "label": product.name, "code": product.sku}

    return None


async def unified_search(
    db: AsyncSession,
    q: str,
    page: int = 1,
    category: str | None = None,
    taxonomy_id: int | None = None,
    entity_type: str | None = None,
    collection_id: int | None = None,
    warehouse_id: int | None = None,
    sort_by: str = "relevance",
    user_id: int | None = None,
    ip_address: str | None = None,
) -> dict:
    start = time.monotonic()
    term = f"%{q}%"
    term_lower = q.lower().strip()
    limit = SEARCH_PAGE_SIZE
    offset = (page - 1) * limit

    results: list[dict] = []
    total = 0
    facets: dict[str, Any] = {"types": {}, "categories": {}, "taxonomies": {}, "languages": {}}

    scan_result = await resolve_scan_code(db, q)
    if scan_result:
        results.append({
            "type": "scan_resolved",
            "id": scan_result["id"],
            "title": scan_result["label"],
            "subtitle": scan_result["code"],
            "description": f"Resolved from scan code: {q}",
            "code": scan_result["code"],
            "url": f"#taxonomy/item/{scan_result['id']}" if scan_result["type"] == "taxonomy_item" else f"#product/{scan_result['id']}",
            "score": 1000,
            "image_url": None,
            "category": scan_result["type"],
            "extra": {"resolved_type": scan_result["type"]},
            "meta": {},
        })
        facets["types"]["scan_resolved"] = 1

    if entity_type in (None, "items", "taxonomy"):
        items_total, items = await search_taxonomy_items(db, term, term_lower, limit, offset, taxonomy_id)
        total += items_total
        for i in items:
            score = i.pop("_score", 0)
            results.append({
                "type": "taxonomy_item",
                "id": i["id"],
                "title": i["common_name"],
                "subtitle": i.get("scientific_name") or "",
                "description": (i.get("description") or "")[:200],
                "code": i["code"],
                "url": f"#taxonomy/item/{i['id']}",
                "score": score,
                "image_url": i.get("image_url"),
                "category": "taxonomy",
                "extra": {
                    "scientific_name": i.get("scientific_name"),
                    "genre": i.get("genre"),
                    "phylum": i.get("phylum"),
                    "family": i.get("family"),
                    "names": i.get("names", []),
                },
                "meta": {"ld_json": build_json_ld_taxonomy_item(i)},
            })
            facets["types"]["taxonomy_item"] = facets["types"].get("taxonomy_item", 0) + 1

    if entity_type in (None, "products"):
        prod_total, products = await search_products(db, term, term_lower, limit, offset)
        total += prod_total
        for p in products:
            score = p.pop("_score", 0)
            cat = p.get("category", "")
            results.append({
                "type": "product",
                "id": p["id"],
                "title": p["name"],
                "subtitle": p.get("sku", ""),
                "description": (p.get("description") or "")[:200],
                "code": p["sku"],
                "url": f"#product/{p['id']}",
                "score": score,
                "image_url": None,
                "category": cat,
                "extra": {"producer": p.get("producer_name"), "origin": p.get("origin_country")},
                "meta": {"ld_json": build_json_ld_product(p)},
            })
            facets["types"]["product"] = facets["types"].get("product", 0) + 1
            if cat:
                facets["categories"][cat] = facets["categories"].get(cat, 0) + 1

    if entity_type in (None, "batches"):
        batch_total, batches = await search_batches(db, term, term_lower, limit, offset)
        total += batch_total
        for b in batches:
            score = b.pop("_score", 0)
            results.append({
                "type": "batch",
                "id": b["id"],
                "title": b["batch_number"],
                "subtitle": b.get("product_name") or "",
                "description": f"Qty: {b.get('quantity', 0)} | Status: {b.get('status', '')}",
                "code": b["batch_number"],
                "url": f"#batches/{b['id']}",
                "score": score,
                "image_url": None,
                "category": "batch",
                "extra": {"status": b.get("status"), "quantity": b.get("quantity")},
                "meta": {"ld_json": build_json_ld_batch(b)},
            })
            facets["types"]["batch"] = facets["types"].get("batch", 0) + 1

    if entity_type in (None, "warehouses"):
        wh_total, whs = await search_warehouses(db, term, term_lower, limit, offset)
        total += wh_total
        for w in whs:
            score = w.pop("_score", 0)
            results.append({
                "type": "warehouse",
                "id": w["id"],
                "title": w["name"],
                "subtitle": w.get("code", ""),
                "description": f"{w.get('city', '')} {w.get('country', '')}".strip(),
                "code": w["code"],
                "url": f"#warehouses/{w['id']}",
                "score": score,
                "image_url": None,
                "category": "warehouse",
            })
            facets["types"]["warehouse"] = facets["types"].get("warehouse", 0) + 1

    if entity_type in (None, "certificates"):
        cert_total, certs = await search_certificates(db, term, term_lower, limit, offset)
        total += cert_total
        for c in certs:
            score = c.pop("_score", 0)
            results.append({
                "type": "certificate",
                "id": c["id"],
                "title": c["certificate_id"],
                "subtitle": c.get("type", ""),
                "description": c.get("issuer_name") or "",
                "code": c["certificate_id"],
                "url": f"#certificate/{c['certificate_id']}",
                "score": score,
                "image_url": None,
                "category": "certificate",
                "extra": {"status": c.get("status")},
            })
            facets["types"]["certificate"] = facets["types"].get("certificate", 0) + 1

    if entity_type in (None, "collections"):
        coll_total, colls = await search_collections(db, term, term_lower, limit, offset)
        total += coll_total
        for c in colls:
            score = c.pop("_score", 0)
            results.append({
                "type": "collection",
                "id": c["id"],
                "title": c["name"],
                "subtitle": c.get("slug", ""),
                "description": (c.get("description") or "")[:200],
                "code": c["slug"],
                "url": f"#collections/{c['id']}",
                "score": score,
                "image_url": c.get("image_url"),
                "category": "collection",
            })
            facets["types"]["collection"] = facets["types"].get("collection", 0) + 1

    results.sort(key=lambda r: r.get("score", 0) or 0, reverse=True)
    total_pages = max(1, (total + limit - 1) // limit) if entity_type is None else 1
    paged = results[offset:offset + limit] if entity_type is None else results

    suggestion = await _suggestion(db, q)

    elapsed_ms = (time.monotonic() - start) * 1000
    await log_search(db, q, total, entity_type, user_id, ip_address, elapsed_ms)

    return {
        "results": paged,
        "total": total,
        "page": page,
        "page_size": limit,
        "total_pages": total_pages,
        "query": q,
        "facets": facets,
        "suggestion": suggestion,
        "scan_resolved": scan_result is not None,
    }


async def _suggestion(db: AsyncSession, q: str) -> str | None:
    if not q or len(q) < 3:
        return None

    tokens = _tokenize(q)
    if not tokens:
        return None

    names = await db.execute(
        select(ItemName.name).distinct().limit(1000)
    )
    known_terms: set[str] = set()
    for row in names.all():
        known_terms.add(row[0].lower())

    best_dist = float("inf")
    best_term = None
    for term in known_terms:
        dist = _levenshtein(q.lower(), term)
        if dist < best_dist and dist <= max(2, len(q) // 3):
            best_dist = dist
            best_term = term

    if best_term and best_dist > 0:
        return best_term

    if len(tokens) > 1:
        for i in range(len(tokens) - 1):
            shortened = " ".join(tokens[:i + 1]) if i < len(tokens) - 1 else " ".join(tokens[:-1])
            if shortened != q.lower():
                return shortened

    return None


async def search_taxonomy_items(
    db: AsyncSession, term: str, term_lower: str, limit: int, offset: int, taxonomy_id: int | None = None
) -> tuple[int, list[dict]]:
    base = select(TaxonomyItem).where(TaxonomyItem.is_active == True)

    if taxonomy_id:
        base = base.join(TaxonomyNode).where(TaxonomyNode.taxonomy_id == taxonomy_id)

    name_subq = (
        select(ItemName.item_id)
        .where(ItemName.name.ilike(term))
        .distinct()
        .subquery()
    )

    base = base.where(
        or_(
            TaxonomyItem.common_name.ilike(term),
            TaxonomyItem.scientific_name.ilike(term),
            TaxonomyItem.genre.ilike(term),
            TaxonomyItem.phylum.ilike(term),
            TaxonomyItem.tax_class.ilike(term),
            TaxonomyItem.order_name.ilike(term),
            TaxonomyItem.family.ilike(term),
            TaxonomyItem.code.ilike(term),
            TaxonomyItem.description.ilike(term),
            TaxonomyItem.id.in_(select(name_subq.c.item_id)),
        )
    )

    count_q = select(func.count()).select_from(base.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    items = (await db.execute(
        base.offset(offset).limit(limit).order_by(TaxonomyItem.common_name)
    )).scalars().all()

    result = []
    for item in items:
        names = await db.execute(select(ItemName).where(ItemName.item_id == item.id))
        names_list = [{"language": n.language, "name": n.name, "is_primary": n.is_primary} for n in names.scalars().all()]

        score = max(
            _score_field(term_lower, item.common_name, 10),
            _score_field(term_lower, item.scientific_name, 8),
            _score_field(term_lower, item.code, 6),
            _score_field(term_lower, item.local_uses, 4),
        )

        for n in names_list:
            ns = _score_field(term_lower, n["name"], 7)
            if n["language"] in PRIMARY_LANGUAGES:
                ns *= 1.2
            score = max(score, ns)

        result.append({
            "id": item.id, "node_id": item.node_id, "code": item.code,
            "common_name": item.common_name, "scientific_name": item.scientific_name,
            "genre": item.genre, "phylum": item.phylum, "tax_class": item.tax_class,
            "order_name": item.order_name, "family": item.family,
            "gestation_period": item.gestation_period, "gestation_unit": item.gestation_unit,
            "local_uses": item.local_uses,
            "description": item.description, "image_url": item.image_url,
            "names": names_list,
            "_score": score,
        })

    result.sort(key=lambda r: r.get("_score", 0), reverse=True)
    return total, result


async def search_products(
    db: AsyncSession, term: str, term_lower: str, limit: int, offset: int
) -> tuple[int, list[dict]]:
    q = select(Product).where(
        Product.is_active == True,
        or_(
            Product.name.ilike(term), Product.sku.ilike(term),
            Product.description.ilike(term), Product.origin_country.ilike(term),
            Product.producer_name.ilike(term),
        ),
    )
    count_q = select(func.count()).select_from(q.subquery())
    total = (await db.execute(count_q)).scalar() or 0
    items = (await db.execute(q.offset(offset).limit(limit).order_by(Product.name))).scalars().all()
    result = []
    for p in items:
        score = max(
            _score_field(term_lower, p.name, 8),
            _score_field(term_lower, p.sku, 7),
            _score_field(term_lower, p.producer_name, 5),
        )
        result.append({
            "id": p.id, "sku": p.sku, "name": p.name,
            "category": p.category.value if hasattr(p.category, 'value') else str(p.category),
            "description": p.description, "origin_country": p.origin_country,
            "producer_name": p.producer_name, "weight_kg": p.weight_kg,
            "image_url": None,
            "_score": score,
        })
    return total, result


async def search_batches(
    db: AsyncSession, term: str, term_lower: str, limit: int, offset: int
) -> tuple[int, list[dict]]:
    q = (
        select(Batch)
        .join(Product, Batch.product_id == Product.id)
        .where(
            or_(
                Batch.batch_number.ilike(term),
                Product.name.ilike(term),
                Product.sku.ilike(term),
                Batch.notes.ilike(term),
            )
        )
    )
    count_q = select(func.count()).select_from(q.subquery())
    total = (await db.execute(count_q)).scalar() or 0
    items = (await db.execute(q.offset(offset).limit(limit).order_by(Batch.batch_number))).scalars().all()
    result = []
    for b in items:
        prod = await db.get(Product, b.product_id)
        score = max(
            _score_field(term_lower, b.batch_number, 9),
            _score_field(term_lower, prod.name if prod else "", 5),
        )
        result.append({
            "id": b.id, "batch_number": b.batch_number,
            "product_id": b.product_id, "product_name": prod.name if prod else "",
            "product_sku": prod.sku if prod else "",
            "quantity": b.quantity,
            "serial_number": b.serial_number,
            "manufacturer_part_number": b.manufacturer_part_number,
            "status": b.status.value if hasattr(b.status, 'value') else str(b.status),
            "production_date": str(b.production_date) if b.production_date else None,
            "expiry_date": str(b.expiry_date) if b.expiry_date else None,
            "notes": b.notes,
            "_score": score,
        })
    return total, result


async def search_warehouses(
    db: AsyncSession, term: str, term_lower: str, limit: int, offset: int
) -> tuple[int, list[dict]]:
    q = select(Warehouse).where(
        Warehouse.is_active == True,
        or_(
            Warehouse.name.ilike(term), Warehouse.code.ilike(term),
            Warehouse.city.ilike(term), Warehouse.country.ilike(term),
            Warehouse.address.ilike(term),
        ),
    )
    count_q = select(func.count()).select_from(q.subquery())
    total = (await db.execute(count_q)).scalar() or 0
    items = (await db.execute(q.offset(offset).limit(limit).order_by(Warehouse.name))).scalars().all()
    result = []
    for w in items:
        score = max(
            _score_field(term_lower, w.name, 6),
            _score_field(term_lower, w.code, 5),
            _score_field(term_lower, w.city, 3),
        )
        result.append({
            "id": w.id, "code": w.code, "name": w.name,
            "city": w.city, "country": w.country,
            "address": w.address,
            "capacity_items": w.capacity_items,
            "_score": score,
        })
    return total, result


async def search_certificates(
    db: AsyncSession, term: str, term_lower: str, limit: int, offset: int
) -> tuple[int, list[dict]]:
    q = select(Certificate).where(
        or_(
            Certificate.certificate_id.ilike(term),
            Certificate.issuer_name.ilike(term),
            Certificate.recipient_entity.ilike(term),
            Certificate.description.ilike(term),
        )
    )
    count_q = select(func.count()).select_from(q.subquery())
    total = (await db.execute(count_q)).scalar() or 0
    items = (await db.execute(q.offset(offset).limit(limit).order_by(Certificate.certificate_id))).scalars().all()
    result = []
    for c in items:
        score = _score_field(term_lower, c.certificate_id, 7)
        result.append({
            "id": c.id, "certificate_id": c.certificate_id,
            "type": c.type.value if hasattr(c.type, 'value') else str(c.type),
            "status": c.status.value if hasattr(c.status, 'value') else str(c.status),
            "issuer_name": c.issuer_name,
            "_score": score,
        })
    return total, result


async def search_collections(
    db: AsyncSession, term: str, term_lower: str, limit: int, offset: int
) -> tuple[int, list[dict]]:
    q = select(Collection).where(
        Collection.is_active == True,
        or_(
            Collection.name.ilike(term),
            Collection.slug.ilike(term),
            Collection.description.ilike(term),
        ),
    )
    count_q = select(func.count()).select_from(q.subquery())
    total = (await db.execute(count_q)).scalar() or 0
    items = (await db.execute(q.offset(offset).limit(limit).order_by(Collection.sort_order))).scalars().all()
    result = []
    for c in items:
        score = _score_field(term_lower, c.name, 6)
        result.append({
            "id": c.id, "name": c.name, "slug": c.slug,
            "description": c.description, "image_url": c.image_url,
            "is_ai_generated": c.is_ai_generated,
            "item_count": len(c.items) if hasattr(c, 'items') else 0,
            "_score": score,
        })
    return total, result


async def autocomplete_search(db: AsyncSession, q: str, limit: int = 8) -> list[dict]:
    term = f"%{q}%"
    results: list[dict] = []
    seen: set[str] = set()

    tq = (
        select(TaxonomyItem)
        .where(
            TaxonomyItem.is_active == True,
            or_(
                TaxonomyItem.common_name.ilike(term),
                TaxonomyItem.scientific_name.ilike(term),
                TaxonomyItem.code.ilike(term),
            ),
        )
        .limit(limit)
    )
    for item in (await db.execute(tq)).scalars().all():
        key = f"taxonomy_{item.id}"
        if key in seen:
            continue
        seen.add(key)
        label = item.common_name
        if item.scientific_name:
            label += f" ({item.scientific_name})"
        results.append({
            "type": "taxonomy_item",
            "id": item.id,
            "label": label,
            "subtitle": item.code,
            "url": f"#taxonomy/item/{item.id}",
            "image_url": item.image_url,
        })

    names = await db.execute(
        select(ItemName)
        .where(ItemName.name.ilike(term))
        .limit(limit * 2)
    )
    for n in names.scalars().all():
        key = f"name_{n.id}"
        if key in seen:
            continue
        seen.add(key)
        results.append({
            "type": "multilingual_name",
            "id": n.item_id,
            "label": f"{n.name} ({n.language})",
            "subtitle": f"Item #{n.item_id}",
            "url": f"#taxonomy/item/{n.item_id}",
            "image_url": None,
        })

    pq = (
        select(Product)
        .where(
            Product.is_active == True,
            or_(Product.name.ilike(term), Product.sku.ilike(term)),
        )
        .limit(limit)
    )
    for p in (await db.execute(pq)).scalars().all():
        key = f"product_{p.id}"
        if key in seen:
            continue
        seen.add(key)
        results.append({
            "type": "product",
            "id": p.id,
            "label": p.name,
            "subtitle": p.sku,
            "url": f"#product/{p.id}",
            "image_url": None,
        })

    bq = (
        select(Batch)
        .where(Batch.batch_number.ilike(term))
        .limit(limit)
    )
    for b in (await db.execute(bq)).scalars().all():
        key = f"batch_{b.id}"
        if key in seen:
            continue
        seen.add(key)
        results.append({
            "type": "batch",
            "id": b.id,
            "label": f"Batch {b.batch_number}",
            "subtitle": "",
            "url": f"#batches/{b.id}",
            "image_url": None,
        })

    return results[:limit]


async def get_search_analytics(
    db: AsyncSession, days: int = 7, limit: int = 50,
) -> dict:
    cutoff = datetime.now(timezone.utc)
    top_queries = await db.execute(
        select(SearchLog.query, func.count().label("cnt"))
        .where(SearchLog.created_at >= cutoff)
        .group_by(SearchLog.query)
        .order_by(func.count().desc())
        .limit(limit)
    )
    zero_results = await db.execute(
        select(SearchLog.query, func.count().label("cnt"))
        .where(
            SearchLog.created_at >= cutoff,
            SearchLog.result_count == 0,
        )
        .group_by(SearchLog.query)
        .order_by(func.count().desc())
        .limit(limit)
    )
    total_queries = await db.execute(
        select(func.count()).where(SearchLog.created_at >= cutoff)
    )
    total_queries = total_queries.scalar() or 0

    avg_response = await db.execute(
        select(func.avg(SearchLog.response_time_ms))
        .where(SearchLog.created_at >= cutoff)
    )
    avg_response = avg_response.scalar() or 0

    return {
        "period_days": days,
        "total_queries": total_queries,
        "avg_response_time_ms": round(float(avg_response), 2),
        "top_queries": [{"query": r[0], "count": r[1]} for r in top_queries.all()],
        "zero_result_queries": [{"query": r[0], "count": r[1]} for r in zero_results.all()],
    }


async def get_taxonomy_item_detail(db: AsyncSession, item_id: int) -> dict | None:
    item = await db.get(TaxonomyItem, item_id)
    if not item or not item.is_active:
        return None

    names = await db.execute(select(ItemName).where(ItemName.item_id == item.id))
    names_list = [{"id": n.id, "language": n.language, "name": n.name, "is_primary": n.is_primary} for n in names.scalars().all()]

    attrs = await db.execute(select(ItemAttribute).where(ItemAttribute.item_id == item.id))
    attrs_list = [{"id": a.id, "key": a.key, "value": a.value, "unit": a.unit} for a in attrs.scalars().all()]

    linked_products = []
    prod_q = select(Product).where(
        Product.is_active == True,
        or_(
            Product.name.ilike(f"%{item.common_name}%"),
            Product.name.ilike(f"%{item.scientific_name}%") if item.scientific_name else False,
        ),
    ).limit(10)
    for p in (await db.execute(prod_q)).scalars().all():
        linked_products.append({
            "id": p.id, "sku": p.sku, "name": p.name,
            "category": p.category.value if hasattr(p.category, 'value') else str(p.category),
            "producer_name": p.producer_name,
            "url": f"#product/{p.id}",
        })

    linked_batches = []
    if linked_products:
        prod_ids = [p["id"] for p in linked_products]
        bq = select(Batch).where(Batch.product_id.in_(prod_ids)).limit(20)
        for b in (await db.execute(bq)).scalars().all():
            wh_items = await db.execute(
                select(WarehouseItem)
                .where(WarehouseItem.batch_id == b.id)
                .limit(5)
            )
            locations = []
            for wi in wh_items.scalars().all():
                wh = await db.get(Warehouse, wi.warehouse_id)
                locations.append({
                    "warehouse_name": wh.name if wh else "Unknown",
                    "warehouse_id": wi.warehouse_id,
                    "zone": wi.location_zone,
                    "rack": wi.location_rack,
                    "quantity": wi.quantity,
                })
            linked_batches.append({
                "id": b.id,
                "batch_number": b.batch_number,
                "quantity": b.quantity,
                "status": b.status.value if hasattr(b.status, 'value') else str(b.status),
                "production_date": str(b.production_date) if b.production_date else None,
                "expiry_date": str(b.expiry_date) if b.expiry_date else None,
                "locations": locations,
            })

    return {
        "id": item.id, "node_id": item.node_id, "code": item.code,
        "common_name": item.common_name, "scientific_name": item.scientific_name,
        "genre": item.genre, "phylum": item.phylum,
        "tax_class": item.tax_class, "order_name": item.order_name, "family": item.family,
        "gestation_period": item.gestation_period, "gestation_unit": item.gestation_unit,
        "local_uses": item.local_uses,
        "description": item.description, "image_url": item.image_url,
        "names": names_list, "attributes": attrs_list,
        "linked_products": linked_products,
        "linked_batches": linked_batches,
    }


async def get_taxonomy_item_by_code(db: AsyncSession, code: str) -> dict | None:
    stmt = select(TaxonomyItem).where(TaxonomyItem.code == code, TaxonomyItem.is_active == True)
    item = (await db.execute(stmt)).scalar_one_or_none()
    if not item:
        return None
    return await get_taxonomy_item_detail(db, item.id)
