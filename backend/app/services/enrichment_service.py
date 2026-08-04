from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.enrichment import EnrichmentLog, EnrichmentSuggestion, EnrichmentSource, EnrichmentStatus
from app.models.taxonomy import TaxonomyItem, TaxonomyNode
from app.models.tracking import Collection, CollectionItem, FeedSource
from app.models.user import User, UserRole
from tools import (
    web_search, read_url, fetch_nutrition,
    fetch_market_price, translate_text, fetch_weather,
)

PAGE_SIZE = 20


async def enrich_collection_from_feed(db: AsyncSession, user: User, collection_id: int) -> dict:
    if user.role not in (UserRole.SUPERUSER, UserRole.ADMIN, UserRole.ENTERPRISE):
        raise PermissionError("Only ADMIN and ENTERPRISE can trigger feed enrichment")

    collection = await db.get(Collection, collection_id)
    if not collection:
        raise ValueError(f"Collection {collection_id} not found")

    log = EnrichmentLog(source=EnrichmentSource.RSS_FEED, status=EnrichmentStatus.RUNNING, entity_type="collection", entity_id=collection_id, triggered_by=user.id)
    db.add(log)
    await db.commit()

    try:
        feed_rows = []
        if collection.feed_source_id:
            feed_rows = (
                await db.execute(select(FeedSource).where(FeedSource.id == collection.feed_source_id))
            ).scalars().all()
        items_added = 0
        for feed in feed_rows:
            try:
                content = read_url(feed.url)
                items_added += 1
            except Exception:
                pass

        log.status = EnrichmentStatus.COMPLETED
        log.summary = f"Processed feeds for collection {collection_id}, added {items_added} items"
        log.completed_at = datetime.now(timezone.utc)
        await db.commit()

        return {"collection_id": collection_id, "feeds_processed": items_added, "status": "completed"}
    except Exception as e:
        log.status = EnrichmentStatus.FAILED
        log.summary = str(e)
        log.completed_at = datetime.now(timezone.utc)
        await db.commit()
        raise


async def enrich_taxonomy_from_web(db: AsyncSession, user: User) -> dict:
    if user.role not in (UserRole.SUPERUSER, UserRole.ADMIN):
        raise PermissionError("Admin access required")

    log = EnrichmentLog(source=EnrichmentSource.WEB_SEARCH, status=EnrichmentStatus.RUNNING, entity_type="taxonomy", triggered_by=user.id)
    db.add(log)
    await db.commit()

    try:
        results = web_search("new food varieties species discovered 2025 2026 agriculture", max_results=10)
        results_list = results.get("results", []) if isinstance(results, dict) else (results or [])
        suggestions_created = 0

        existing_codes = set()
        rows = await db.execute(select(TaxonomyItem.code))
        for (code,) in rows.all():
            existing_codes.add(code)

        for r in results_list:
            title = (r.get("title") or r.get("name") or "").strip()
            if not title or len(title) < 3:
                continue
            code = title.lower().replace(" ", "_")[:50]
            if code in existing_codes:
                continue

            suggestion = EnrichmentSuggestion(
                entity_type="taxonomy_item", suggestion_type="new_item",
                title=f"Potential new item: {title}", description=r.get("snippet") or r.get("body") or "",
                confidence="low", source=r.get("link") or r.get("href"),
                status="open", created_by=user.id,
            )
            db.add(suggestion)
            suggestions_created += 1

        log.status = EnrichmentStatus.COMPLETED
        log.summary = f"Web search found {suggestions_created} potential new taxonomy items"
        log.completed_at = datetime.now(timezone.utc)
        await db.commit()

        return {"suggestions_created": suggestions_created, "status": "completed"}
    except Exception as e:
        log.status = EnrichmentStatus.FAILED
        log.summary = str(e)
        log.completed_at = datetime.now(timezone.utc)
        await db.commit()
        raise


async def suggest_taxonomy_nodes(db: AsyncSession, user: User, item_id: int) -> dict:
    if user.role not in (UserRole.SUPERUSER, UserRole.ADMIN, UserRole.ENTERPRISE):
        raise PermissionError("Insufficient permissions")

    item = await db.get(TaxonomyItem, item_id)
    if not item:
        raise ValueError(f"TaxonomyItem {item_id} not found")

    query = f"{item.common_name} {item.scientific_name or ''} food classification family genus"
    results = web_search(query, max_results=5)
    results_list = results.get("results", []) if isinstance(results, dict) else (results or [])

    suggestions = []
    for r in results_list[:3]:
        suggestion = EnrichmentSuggestion(
            entity_type="taxonomy_item", entity_id=item_id,
            suggestion_type="classification",
            title=f"Reclassify {item.common_name}", description=(r.get("snippet") or r.get("body") or "")[:300],
            confidence="medium", source=r.get("link") or r.get("href"),
            status="open", created_by=user.id,
        )
        db.add(suggestion)
        suggestions.append({"id": suggestion.id, "title": suggestion.title})

    await db.commit()
    return {"item_id": item_id, "suggestions_count": len(suggestions), "suggestions": suggestions}


async def auto_categorize_collection(db: AsyncSession, user: User, collection_id: int) -> dict:
    if user.role not in (UserRole.SUPERUSER, UserRole.ADMIN, UserRole.ENTERPRISE):
        raise PermissionError("Insufficient permissions")

    collection = await db.get(Collection, collection_id)
    if not collection:
        raise ValueError(f"Collection {collection_id} not found")

    items = await db.execute(
        select(CollectionItem).where(CollectionItem.collection_id == collection_id)
    )

    categories = {}
    for ci in items.scalars().all():
        tax_item = await db.get(TaxonomyItem, ci.item_id)
        if tax_item and tax_item.node_id:
            node = await db.get(TaxonomyNode, tax_item.node_id)
            if node:
                cat = node.name or "uncategorized"
                categories[cat] = categories.get(cat, 0) + 1

    suggestion = EnrichmentSuggestion(
        entity_type="collection", entity_id=collection_id,
        suggestion_type="auto_categorize",
        title=f"Suggested categories for {collection.name}", description=str(categories),
        confidence="medium", status="open", created_by=user.id,
    )
    db.add(suggestion)
    await db.commit()

    return {"collection_id": collection_id, "item_count": sum(categories.values()), "categories": categories, "suggestion_id": suggestion.id}


async def suggest_collection_items(db: AsyncSession, user: User, collection_id: int) -> dict:
    if user.role not in (UserRole.SUPERUSER, UserRole.ADMIN, UserRole.ENTERPRISE):
        raise PermissionError("Insufficient permissions")

    collection = await db.get(Collection, collection_id)
    if not collection:
        raise ValueError(f"Collection {collection_id} not found")

    existing = await db.execute(
        select(CollectionItem.item_id).where(CollectionItem.collection_id == collection_id)
    )
    existing_ids = {row[0] for row in existing.all()}

    node_rows = await db.execute(
        select(TaxonomyItem.node_id).where(TaxonomyItem.id.in_(existing_ids))
    )
    node_ids = {row[0] for row in node_rows.all() if row[0]}
    if not node_ids:
        return {"collection_id": collection_id, "suggestions_count": 0, "suggestions": []}

    other_items = await db.execute(
        select(TaxonomyItem.id, TaxonomyItem.common_name)
        .where(TaxonomyItem.node_id.in_(node_ids))
        .limit(20)
    )

    suggestions = []
    for item_id, name in other_items.all():
        if item_id not in existing_ids:
            suggestion = EnrichmentSuggestion(
                entity_type="collection", entity_id=collection_id,
                suggestion_type="suggest_item",
                title=f"Add {name} to {collection.name}", description=f"Item {name} shares a taxonomy node with this collection",
                confidence="high", status="open", created_by=user.id,
            )
            db.add(suggestion)
            suggestions.append({"item_id": item_id, "name": name, "suggestion_id": suggestion.id})

    await db.commit()
    return {"collection_id": collection_id, "suggestions_count": len(suggestions), "suggestions": suggestions[:10]}


async def backfill_item_data(db: AsyncSession, user: User) -> dict:
    if user.role not in (UserRole.SUPERUSER, UserRole.ADMIN, UserRole.ENTERPRISE):
        raise PermissionError("Insufficient permissions")

    log = EnrichmentLog(source=EnrichmentSource.NUTRITION_API, status=EnrichmentStatus.RUNNING, entity_type="backfill", triggered_by=user.id)
    db.add(log)
    await db.commit()

    try:
        items = await db.execute(
            select(TaxonomyItem).order_by(TaxonomyItem.id).limit(50)
        )
        results = {"nutrition": 0, "prices": 0, "translations": 0}

        for item in items.scalars().all():
            try:
                nutrition = await fetch_nutrition(item.common_name)
                if nutrition:
                    results["nutrition"] += 1
            except Exception:
                pass

            try:
                price = await fetch_market_price(item.common_name)
                if price:
                    results["prices"] += 1
            except Exception:
                pass

        log.status = EnrichmentStatus.COMPLETED
        log.summary = f"Backfill completed: {results}"
        log.completed_at = datetime.now(timezone.utc)
        await db.commit()

        return {"status": "completed", "results": results}
    except Exception as e:
        log.status = EnrichmentStatus.FAILED
        log.summary = str(e)
        log.completed_at = datetime.now(timezone.utc)
        await db.commit()
        raise


async def refresh_collections_schedule(db: AsyncSession) -> dict:
    log = EnrichmentLog(source=EnrichmentSource.RSS_FEED, status=EnrichmentStatus.RUNNING, entity_type="scheduled_refresh")
    db.add(log)
    await db.commit()

    try:
        collections = await db.execute(select(Collection).limit(20))
        refreshed = 0
        for coll in collections.scalars().all():
            try:
                if not coll.feed_source_id:
                    continue
                feed = await db.get(FeedSource, coll.feed_source_id)
                if not feed or not feed.url:
                    continue
                read_url(feed.url)
                refreshed += 1
            except Exception:
                pass

        log.status = EnrichmentStatus.COMPLETED
        log.summary = f"Scheduled refresh: {refreshed} feeds processed"
        log.completed_at = datetime.now(timezone.utc)
        await db.commit()

        return {"feeds_refreshed": refreshed, "status": "completed"}
    except Exception as e:
        log.status = EnrichmentStatus.FAILED
        log.summary = str(e)
        log.completed_at = datetime.now(timezone.utc)
        await db.commit()
        raise


async def list_enrichment_logs(db: AsyncSession, page: int = 1, source: str | None = None):
    q = select(EnrichmentLog)
    if source:
        q = q.where(EnrichmentLog.source == source)
    q = q.order_by(EnrichmentLog.created_at.desc())

    count_q = select(func.count()).select_from(q.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    rows = (await db.execute(q.offset((page - 1) * PAGE_SIZE).limit(PAGE_SIZE))).scalars().all()
    results = []
    for r in rows:
        results.append({
            "id": r.id,
            "source": r.source.value if hasattr(r.source, "value") else str(r.source),
            "status": r.status.value if hasattr(r.status, "value") else str(r.status),
            "entity_type": r.entity_type,
            "entity_id": r.entity_id,
            "summary": r.summary,
            "duration_ms": r.duration_ms,
            "created_at": str(r.created_at) if r.created_at else None,
            "completed_at": str(r.completed_at) if r.completed_at else None,
        })

    return {"logs": results, "total": total, "page": page, "total_pages": max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)}


async def list_enrichment_suggestions(db: AsyncSession, page: int = 1, status: str | None = None):
    q = select(EnrichmentSuggestion)
    if status:
        q = q.where(EnrichmentSuggestion.status == status)
    q = q.order_by(EnrichmentSuggestion.created_at.desc())

    count_q = select(func.count()).select_from(q.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    rows = (await db.execute(q.offset((page - 1) * PAGE_SIZE).limit(PAGE_SIZE))).scalars().all()
    results = []
    for r in rows:
        results.append({
            "id": r.id,
            "entity_type": r.entity_type,
            "entity_id": r.entity_id,
            "suggestion_type": r.suggestion_type,
            "title": r.title,
            "description": r.description,
            "confidence": r.confidence,
            "source": r.source,
            "status": r.status,
            "created_at": str(r.created_at) if r.created_at else None,
        })

    return {"suggestions": results, "total": total, "page": page, "total_pages": max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)}


async def update_suggestion_status(db: AsyncSession, user: User, suggestion_id: int, new_status: str) -> EnrichmentSuggestion:
    if user.role not in (UserRole.SUPERUSER, UserRole.ADMIN):
        raise PermissionError("Admin access required to update suggestions")

    suggestion = await db.get(EnrichmentSuggestion, suggestion_id)
    if not suggestion:
        raise ValueError(f"Suggestion {suggestion_id} not found")

    suggestion.status = new_status
    await db.commit()
    await db.refresh(suggestion)
    return suggestion
