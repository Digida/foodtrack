from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.taxonomy import TaxonomyItem, ItemName, TaxonomyNode
from app.models.tracking import WarehouseItem, ShipmentBatch, ShipmentTrackingEvent
from app.models.inventory import ItemInventory
from app.models.certificate import Certificate
from app.models.user import User, UserRole
from tools.web_search import web_search
from tools.web_reader import read_url
from tools.nutrition_fetcher import fetch_nutrition
from tools.translator import translate_text
from tools.price_fetcher import fetch_market_price
from tools.weather_fetcher import fetch_weather
from tools.report_audit import ReportAudit


async def enrich_from_web(db: AsyncSession, user: User, item_id: int) -> dict:
    if user.role not in (UserRole.SUPERUSER, UserRole.ADMIN, UserRole.ENTERPRISE):
        raise PermissionError("Only ADMIN and ENTERPRISE users can enrich items")

    item = await db.get(TaxonomyItem, item_id)
    if not item:
        raise ValueError(f"TaxonomyItem {item_id} not found")

    search_term = f"{item.common_name} {item.scientific_name or ''} food origin nutrition price"
    search_results = web_search(search_term, max_results=5)
    enriched = {"item_id": item_id, "sources_consulted": 0, "nutrition_added": 0, "prices_added": 0, "translations_added": 0}

    results_list = search_results.get("results", []) if isinstance(search_results, dict) else (search_results or [])
    if results_list:
        enriched["sources_consulted"] = len(results_list)
        for result in results_list[:3]:
            url = result.get("link") or result.get("href") or result.get("url")
            if url:
                read_url(url)

    existing_langs = set()
    rows = await db.execute(select(ItemName.language).where(ItemName.item_id == item_id).distinct())
    for (lang,) in rows.all():
        existing_langs.add(lang)

    target_langs = ["ar", "sw", "hi", "zh", "fr", "pt"]
    missing = [l for l in target_langs if l not in existing_langs]
    for lang in missing:
        try:
            result = await translate_text(item.common_name, target_lang=lang)
            translated = result.get("translated_text") if isinstance(result, dict) else str(result)
            if translated and translated != item.common_name:
                name = ItemName(item_id=item_id, language=lang, name=translated)
                db.add(name)
                enriched["translations_added"] += 1
        except Exception:
            pass

    try:
        nutrition = await fetch_nutrition(item.common_name)
        if nutrition:
            enriched["nutrition_added"] = 1
    except Exception:
        pass

    try:
        price_info = await fetch_market_price(item.common_name)
        if price_info:
            enriched["prices_added"] = 1
    except Exception:
        pass

    try:
        await fetch_weather(location=item.origin_region or "global")
    except Exception:
        pass

    await db.commit()
    return enriched


async def suggest_item_classification(db: AsyncSession, name: str) -> dict:
    query = f"biological classification taxonomy of {name} food species genus family"
    results = web_search(query, max_results=5)

    results_list = results.get("results", []) if isinstance(results, dict) else (results or [])
    suggestions = []
    seen = set()
    for r in results_list[:5]:
        snippet = (r.get("snippet") or r.get("body") or "")[:300]
        words = snippet.lower().split()
        for node_type in ["family", "genus", "species", "order", "class", "phylum"]:
            idx = -1
            for i, w in enumerate(words):
                if w == node_type and i + 1 < len(words):
                    idx = i
                    break
            if idx >= 0 and idx + 2 < len(words):
                candidate = words[idx + 1]
                if candidate not in seen and len(candidate) > 2:
                    seen.add(candidate)
                    suggestions.append({"rank": len(suggestions) + 1, "type": node_type, "value": candidate.title(), "source": r.get("link") or r.get("href")})

    existing_nodes = await db.execute(select(TaxonomyNode.name).distinct())
    existing_set = set()
    for (name_val,) in existing_nodes.all():
        existing_set.add(name_val.lower())

    matched = [s for s in suggestions if s["value"].lower() in existing_set]
    return {"query": name, "suggested_nodes": suggestions, "existing_matches": matched}


async def detect_anomalies(db: AsyncSession, user: User, item_id: int) -> dict:
    if user.role not in (UserRole.SUPERUSER, UserRole.ADMIN, UserRole.ENTERPRISE, UserRole.VERIFIER):
        raise PermissionError("Insufficient permissions to detect anomalies")

    item = await db.get(TaxonomyItem, item_id)
    if not item:
        raise ValueError(f"TaxonomyItem {item_id} not found")

    anomalies = []

    rows = await db.execute(
        select(WarehouseItem).where(WarehouseItem.item_id == item_id)
    )
    for wi in rows.scalars().all():
        if wi.temperature_celsius is not None:
            if wi.temperature_celsius > 8 and wi.temperature_celsius < 60:
                pass
            elif wi.temperature_celsius >= 60:
                anomalies.append({"type": "temperature_warning", "severity": "high", "detail": f"WarehouseItem {wi.id}: temp {wi.temperature_celsius}°C exceeds safe range", "entity": "WarehouseItem", "entity_id": wi.id})
            elif wi.temperature_celsius < -10:
                anomalies.append({"type": "temperature_warning", "severity": "medium", "detail": f"WarehouseItem {wi.id}: temp {wi.temperature_celsius}°C below freezing threshold", "entity": "WarehouseItem", "entity_id": wi.id})

    rows = await db.execute(
        select(ShipmentBatch).where(ShipmentBatch.item_id == item_id)
    )
    for sb in rows.scalars().all():
        if sb.status.value in ("delayed", "cancelled"):
            anomalies.append({"type": "shipment_anomaly", "severity": "high", "detail": f"ShipmentBatch {sb.id} is {sb.status.value}", "entity": "ShipmentBatch", "entity_id": sb.id})

    rows = await db.execute(
        select(ShipmentTrackingEvent).where(ShipmentTrackingEvent.item_id == item_id)
    )
    events = rows.scalars().all()
    if len(events) > 50:
        anomalies.append({"type": "high_event_volume", "severity": "low", "detail": f"{len(events)} tracking events for this item — unusually high", "entity": "ShipmentTrackingEvent", "entity_id": None})

    certs = await db.execute(
        select(Certificate).where(Certificate.item_id == item_id)
    )
    now = datetime.now(timezone.utc)
    for c in certs.scalars().all():
        if c.expiry_date and c.expiry_date < now:
            anomalies.append({"type": "expired_certificate", "severity": "high", "detail": f"Certificate {c.id} ({c.type.value}) expired on {c.expiry_date.date()}", "entity": "Certificate", "entity_id": c.id})
        elif c.status.value in ("rejected", "revoked"):
            anomalies.append({"type": "certificate_status", "severity": "medium", "detail": f"Certificate {c.id} ({c.type.value}) status is {c.status.value}", "entity": "Certificate", "entity_id": c.id})

    inv = await db.execute(
        select(ItemInventory).where(ItemInventory.item_id == item_id)
    )
    for inv_rec in inv.scalars().all():
        if inv_rec.quantity_on_hand < 0:
            anomalies.append({"type": "negative_inventory", "severity": "high", "detail": f"ItemInventory {inv_rec.id} has negative stock: {inv_rec.quantity_on_hand}", "entity": "ItemInventory", "entity_id": inv_rec.id})

    audit = ReportAudit()
    audit_result = audit.extract_figures(item.common_name)
    if audit_result:
        anomalies.append({"type": "audit_flag", "severity": "info", "detail": str(audit_result)[:200], "entity": "ReportAudit", "entity_id": None})

    return {"item_id": item_id, "item_name": item.common_name, "anomaly_count": len(anomalies), "anomalies": anomalies}
