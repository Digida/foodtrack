import uuid
from datetime import datetime, timezone
import re

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.tracking import Collection, CollectionItem, FeedSource
from app.models.taxonomy import TaxonomyItem
from app.models.user import User, UserRole


PAGE_SIZE = 20


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_]+', '-', text)
    return text


async def list_collections(db: AsyncSession, page: int = 1):
    q = select(Collection).where(Collection.is_active == True)
    count_q = select(func.count()).select_from(q.subquery())
    total = (await db.execute(count_q)).scalar() or 0
    items = (await db.execute(q.offset((page - 1) * PAGE_SIZE).limit(PAGE_SIZE).order_by(Collection.sort_order, Collection.name))).scalars().all()
    result = []
    for c in items:
        item_count = await db.execute(
            select(func.count()).select_from(CollectionItem).where(CollectionItem.collection_id == c.id)
        )
        result.append({
            "id": c.id, "name": c.name, "slug": c.slug,
            "description": c.description, "image_url": c.image_url,
            "is_ai_generated": c.is_ai_generated,
            "item_count": (await item_count).scalar() or 0,
            "created_at": str(c.created_at) if c.created_at else None,
        })
    return {"collections": result, "total": total, "page": page, "total_pages": max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)}


async def get_collection(db: AsyncSession, collection_id: int):
    c = await db.get(Collection, collection_id)
    if not c or not c.is_active:
        return None
    items_result = await db.execute(
        select(CollectionItem, TaxonomyItem).join(TaxonomyItem, CollectionItem.item_id == TaxonomyItem.id)
        .where(CollectionItem.collection_id == c.id)
        .order_by(CollectionItem.sort_order)
    )
    items_list = []
    for ci, ti in items_result.all():
        items_list.append({
            "id": ti.id, "code": ti.code, "common_name": ti.common_name,
            "scientific_name": ti.scientific_name,
            "image_url": ti.image_url, "sort_order": ci.sort_order,
        })
    return {
        "id": c.id, "name": c.name, "slug": c.slug,
        "description": c.description, "image_url": c.image_url,
        "is_ai_generated": c.is_ai_generated,
        "feed_source_id": c.feed_source_id,
        "items": items_list,
        "created_at": str(c.created_at) if c.created_at else None,
        "updated_at": str(c.updated_at) if c.updated_at else None,
    }


async def create_collection(db: AsyncSession, user: User, name: str,
                            description: str | None = None, image_url: str | None = None,
                            is_ai_generated: bool = False, feed_source_id: int | None = None):
    if user is not None and user.role not in (UserRole.ADMIN, UserRole.ENTERPRISE):
        raise PermissionError("Insufficient permissions")
    slug = slugify(name)
    existing = await db.execute(select(Collection).where(Collection.slug == slug))
    if existing.scalar_one_or_none():
        slug = f"{slug}-{uuid.uuid4().hex[:6]}"
    c = Collection(
        name=name, slug=slug, description=description, image_url=image_url,
        is_ai_generated=is_ai_generated, feed_source_id=feed_source_id,
    )
    db.add(c)
    await db.commit()
    await db.refresh(c)
    return c


async def update_collection(db: AsyncSession, user: User, collection_id: int, data: dict):
    if user is not None and user.role not in (UserRole.ADMIN, UserRole.ENTERPRISE):
        raise PermissionError("Insufficient permissions")
    c = await db.get(Collection, collection_id)
    if not c:
        raise ValueError("Collection not found")
    for k, v in data.items():
        if v is not None and hasattr(c, k):
            if k == "name":
                c.slug = slugify(v)
            setattr(c, k, v)
    await db.commit()
    await db.refresh(c)
    return c


async def delete_collection(db: AsyncSession, user: User, collection_id: int):
    if user is not None and user.role != UserRole.ADMIN:
        raise PermissionError("Admin only")
    c = await db.get(Collection, collection_id)
    if not c:
        raise ValueError("Collection not found")
    c.is_active = False
    await db.commit()


async def add_item_to_collection(db: AsyncSession, user: User, collection_id: int,
                                  item_id: int, sort_order: int = 0, notes: str | None = None):
    if user is not None and user.role not in (UserRole.ADMIN, UserRole.ENTERPRISE):
        raise PermissionError("Insufficient permissions")
    c = await db.get(Collection, collection_id)
    if not c or not c.is_active:
        raise ValueError("Collection not found")
    ti = await db.get(TaxonomyItem, item_id)
    if not ti:
        raise ValueError("Taxonomy item not found")
    existing = await db.execute(
        select(CollectionItem).where(
            CollectionItem.collection_id == collection_id,
            CollectionItem.item_id == item_id,
        )
    )
    if existing.scalar_one_or_none():
        raise ValueError("Item already in collection")
    ci = CollectionItem(collection_id=collection_id, item_id=item_id,
                        sort_order=sort_order, notes=notes)
    db.add(ci)
    await db.commit()
    return ci


async def remove_item_from_collection(db: AsyncSession, user: User, collection_item_id: int):
    if user is not None and user.role != UserRole.ADMIN:
        raise PermissionError("Admin only")
    ci = await db.get(CollectionItem, collection_item_id)
    if not ci:
        raise ValueError("Collection item not found")
    await db.delete(ci)
    await db.commit()


async def run_ai_feed(db: AsyncSession, feed_source_id: int):
    fs = await db.get(FeedSource, feed_source_id)
    if not fs or not fs.is_active:
        raise ValueError("Feed source not found or inactive")
    import json
    try:
        import httpx
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(fs.url)
            resp.raise_for_status()
            data = resp.text
    except Exception as e:
        raise ValueError(f"Failed to fetch feed: {e}")

    import xml.etree.ElementTree as ET
    try:
        root = ET.fromstring(data)
        ns = {"atom": "http://www.w3.org/2005/Atom",
              "rss": "http://purl.org/rss/1.0/",
              "dc": "http://purl.org/dc/elements/1.1/"}
        entries = []
        for entry in root.findall(".//item") or root.findall(".//atom:entry", ns):
            title = entry.findtext("title", "") or entry.findtext("atom:title", "", ns)
            desc = entry.findtext("description", "") or entry.findtext("atom:summary", "", ns)
            link = entry.findtext("link", "") or ""
            if link.startswith("<"):
                import re as _re
                m = _re.search(r'href="([^"]+)"', link)
                if m:
                    link = m.group(1)
            entries.append({"title": title, "description": desc, "link": link})

        collection_name = f"{fs.name} - {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}"
        c = await create_collection(db, None, collection_name,
                                     description=f"Auto-generated from feed: {fs.name}",
                                     is_ai_generated=True, feed_source_id=fs.id)

        for entry in entries[:20]:
            ti = await db.execute(
                select(TaxonomyItem).where(
                    TaxonomyItem.common_name.ilike(f"%{entry['title']}%")
                ).limit(1)
            )
            item = ti.scalar_one_or_none()
            if item:
                await add_item_to_collection(db, None, c.id, item.id)

        fs.last_fetched_at = datetime.now(timezone.utc)
        await db.commit()
        return {"collection_id": c.id, "collection_name": c.name, "items_added": len(entries)}
    except ET.ParseError as e:
        raise ValueError(f"Failed to parse feed XML: {e}")


async def list_feed_sources(db: AsyncSession):
    result = await db.execute(select(FeedSource).order_by(FeedSource.name))
    feeds = []
    for fs in result.scalars().all():
        feeds.append({
            "id": fs.id, "name": fs.name, "url": fs.url,
            "feed_type": fs.feed_type,
            "taxonomy_target_id": fs.taxonomy_target_id,
            "node_target_id": fs.node_target_id,
            "schedule_minutes": fs.schedule_minutes,
            "last_fetched_at": str(fs.last_fetched_at) if fs.last_fetched_at else None,
            "is_active": fs.is_active,
            "created_at": str(fs.created_at) if fs.created_at else None,
        })
    return feeds


async def create_feed_source(db: AsyncSession, user: User, name: str, url: str,
                              feed_type: str = "rss",
                              taxonomy_target_id: int | None = None,
                              node_target_id: int | None = None,
                              schedule_minutes: int = 1440):
    if user is not None and user.role != UserRole.ADMIN:
        raise PermissionError("Admin only")
    fs = FeedSource(
        name=name, url=url, feed_type=feed_type,
        taxonomy_target_id=taxonomy_target_id,
        node_target_id=node_target_id,
        schedule_minutes=schedule_minutes,
    )
    db.add(fs)
    await db.commit()
    await db.refresh(fs)
    return fs


async def delete_feed_source(db: AsyncSession, user: User, feed_id: int):
    if user is not None and user.role != UserRole.ADMIN:
        raise PermissionError("Admin only")
    fs = await db.get(FeedSource, feed_id)
    if not fs:
        raise ValueError("Feed source not found")
    await db.delete(fs)
    await db.commit()

