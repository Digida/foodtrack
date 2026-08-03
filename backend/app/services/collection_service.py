import uuid
from datetime import datetime, timezone
import re

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.tracking import Collection, CollectionItem, FeedSource
from app.models.taxonomy import Taxonomy, TaxonomyNode, TaxonomyItem
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
        item_count = (await db.execute(
            select(func.count()).select_from(CollectionItem).where(CollectionItem.collection_id == c.id)
        )).scalar() or 0
        result.append({
            "id": c.id, "name": c.name, "slug": c.slug,
            "description": c.description, "image_url": c.image_url,
            "is_ai_generated": c.is_ai_generated,
            "item_count": item_count,
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
            "phylum": ti.phylum, "family": ti.family,
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
    if user is not None and user.role not in (UserRole.SUPERUSER, UserRole.ADMIN, UserRole.ENTERPRISE):
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
    if user is not None and user.role not in (UserRole.SUPERUSER, UserRole.ADMIN, UserRole.ENTERPRISE):
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
    if user is not None and user.role not in (UserRole.SUPERUSER, UserRole.ADMIN):
        raise PermissionError("Admin only")
    c = await db.get(Collection, collection_id)
    if not c:
        raise ValueError("Collection not found")
    c.is_active = False
    await db.commit()


async def add_item_to_collection(db: AsyncSession, user: User, collection_id: int,
                                  item_id: int, sort_order: int = 0, notes: str | None = None):
    if user is not None and user.role not in (UserRole.SUPERUSER, UserRole.ADMIN, UserRole.ENTERPRISE):
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
    if user is not None and user.role not in (UserRole.SUPERUSER, UserRole.ADMIN):
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


# Each category aims for this many collections.  Categories with fewer
# items than this are considered exhausted and get as many collections as
# their item count supports (never fewer than one).
TARGET_COLLECTIONS = 10
# A themed / assortment collection must contain at least this many items.
MIN_COLLECTION_ITEMS = 3


# Facet themes — each produces one overlapping, thematically coherent subset
# per category based on the item's taxonomy (phylum) and its local_uses text.
_FACET_THEMES = [
    ("Plant-Derived", re.compile(r"(?i)plant|leaf|flower|seed|fruit|root|tuber|vegetable|grain|cereal|alga|seaweed"), None),
    ("Animal-Derived", None, {"Chordata", "Mollusca", "Arthropoda"}),
    ("Fungi & Fermented Cultures", None, {"Basidiomycota", "Ascomycota"}),
    ("Beverage & Drink", re.compile(r"(?i)juice|drink|beverage|tea|wine|beer|spirit|sake|cider|rum|vodka|whisky|gin|tequila|brandy|champagne|kombucha|kvass"), None),
    ("Dairy & Milk", re.compile(r"(?i)milk|dairy|cheese|butter|yogurt|cream|ghee|whey|kefir"), None),
    ("Meat & Poultry", re.compile(r"(?i)meat|beef|pork|lamb|poultry|chicken|steak|duck|turkey|goose|rabbit|venison|goat|mince"), None),
    ("Seafood & Marine", re.compile(r"(?i)fish|shrimp|tuna|salmon|oyster|mussel|clam|scallop|lobster|squid|octopus|crab|crayfish|anchovy|sardine|seaweed|nori|kelp|seafood|abalone|eel"), None),
    ("Baking & Bakery", re.compile(r"(?i)bread|bak|pastry|flour|dough|bagel|cracker|biscuit|loaf|tortilla|naan|pita|muffin|croissant|ciabatta|brioche|focaccia|baguette|sourdough|crumpet|semolina"), None),
    ("Snack & Confection", re.compile(r"(?i)snack|candy|confection|chip|bar|sweet|popcorn|pretzel|fudge|toffee|caramel|nougat|halva|gummy|licorice|marshmallow|chocolate"), None),
    ("Sauce, Condiment & Seasoning", re.compile(r"(?i)sauce|condiment|season|spice|paste|dressing|ketchup|mustard|mayonnaise|pesto|harissa|salsa|tahini|vinegar|soy sauce|fish sauce|oyster sauce|worcestershire"), None),
    ("Sweeteners & Syrups", re.compile(r"(?i)sweetener|syrup|sugar|jaggery|molasses|honey|stevia|agave|fructose"), None),
    ("Fermented & Cultured", re.compile(r"(?i)fermented|cultured|sauerkraut|kimchi|miso|tempeh|koji|gochujang|doubanjiang|sourdough|pickle|natto|kombucha|probiotic"), None),
    ("Whole Grain & Staple", re.compile(r"(?i)staple|grain|cereal|porridge|rice|wheat|maize|millet|sorghum|tuber|root|yam|cassava|potato|starch|pulse|bean|lentil"), None),
    ("Plant Milks & Alternatives", re.compile(r"(?i)oat milk|soy milk|almond milk|coconut milk|cashew milk|plant milk|plant-based|vegan|alternative"), None),
]


def _theme_match(item, pattern, phyla) -> bool:
    if phyla and item.phylum in phyla:
        return True
    if pattern and item.local_uses and pattern.search(item.local_uses):
        return True
    return False


def _assortment_subsets(item_ids, slots: int) -> list[list[int]]:
    """Produce up to `slots` selection subsets that fill the remaining slots."""
    if slots <= 0:
        return []
    items = sorted(item_ids)
    n = len(items)
    if n == 0:
        return []
    if n >= MIN_COLLECTION_ITEMS * slots:
        return [items[i * MIN_COLLECTION_ITEMS:(i + 1) * MIN_COLLECTION_ITEMS] for i in range(slots)]
    subset_size = min(MIN_COLLECTION_ITEMS, n)
    return [
        [items[(start + j) % n] for j in range(subset_size)]
        for start in range(slots)
    ]


async def seed_collections_from_taxonomy(
    db: AsyncSession,
    taxonomy_id: int | None = None,
) -> dict:
    """
    Idempotent, incremental collection seed.

    For every top-level taxonomy node (category) it generates up to
    ``TARGET_COLLECTIONS`` collections: a complete base collection, a set of
    overlapping facet collections derived from the item's taxonomy and usage
    keywords, and — when needed to reach the target — curated "selection"
    collections.  Categories with fewer items than ``TARGET_COLLECTIONS`` are
    considered exhausted and receive as many collections as their item count
    supports.

    Safe to re-run: existing collections are reused (by slug) and only
    missing items are linked.
    """
    if taxonomy_id is not None:
        tax = await db.get(Taxonomy, taxonomy_id)
    else:
        tax = (await db.execute(
            select(Taxonomy).where(Taxonomy.is_active == True)
            .order_by(Taxonomy.name).limit(1)
        )).scalar_one_or_none()
    if not tax:
        return {"nodes": 0, "collections": 0, "items": 0}

    nodes = (await db.execute(
        select(TaxonomyNode).where(
            TaxonomyNode.taxonomy_id == tax.id,
            TaxonomyNode.parent_id.is_(None),
            TaxonomyNode.is_active == True,
        ).order_by(TaxonomyNode.sort_order, TaxonomyNode.name)
    )).scalars().all()

    existing = (await db.execute(
        select(Collection.id, Collection.slug, Collection.name, Collection.is_active)
    )).all()
    by_slug = {slug: (cid, name, active) for cid, slug, name, active in existing}

    membership: dict[int, set[int]] = {}
    existing_items = (await db.execute(
        select(CollectionItem.collection_id, CollectionItem.item_id)
    )).all()
    for cid, item_id in existing_items:
        membership.setdefault(cid, set()).add(item_id)

    collections_created = 0
    items_linked = 0

    for node in nodes:
        items = await _subtree_items(db, node.id)
        item_ids = [item.id for item in items]
        n = len(item_ids)
        if n == 0:
            continue

        target = min(TARGET_COLLECTIONS, max(1, n))

        # 1) Complete base collection
        planned: list[tuple[str, str, list[int]]] = [
            (node.name, f"All {node.name} items catalogued in {tax.name}.", item_ids),
        ]

        # 2) Facet collections (overlapping, thematically coherent subsets)
        for theme_name, pattern, phyla in _FACET_THEMES:
            if len(planned) >= target:
                break
            subset = [item.id for item in items if _theme_match(item, pattern, phyla)]
            if len(subset) >= MIN_COLLECTION_ITEMS:
                planned.append((
                    f"{node.name} — {theme_name}",
                    f"{theme_name} items in {node.name} ({tax.name}).",
                    subset,
                ))

        # 3) Curated selection collections to reach the target
        slots = target - len(planned)
        for idx, subset in enumerate(_assortment_subsets(item_ids, slots), start=1):
            planned.append((
                f"{node.name} — Selection {idx}",
                f"Curated selection of {node.name} items from {tax.name}.",
                subset,
            ))

        for name, description, subset_ids in planned:
            slug = slugify(name)
            cid, cname, active = by_slug.get(slug, (None, None, True))
            if cid is not None and (cname != name or not active):
                slug = f"{slug}-{uuid.uuid4().hex[:6]}"
                cid, cname, active = by_slug.get(slug, (None, None, True))

            if cid is None:
                c = Collection(
                    name=name,
                    slug=slug,
                    description=description,
                    is_active=True,
                    sort_order=node.sort_order,
                )
                db.add(c)
                await db.flush()
                cid = c.id
                by_slug[slug] = (cid, name, True)
                membership.setdefault(cid, set())
                collections_created += 1
            else:
                membership.setdefault(cid, set())

            new_items = sorted(set(subset_ids) - membership[cid])
            for item_id in new_items:
                db.add(CollectionItem(collection_id=cid, item_id=item_id, sort_order=0))
                items_linked += 1
            membership[cid].update(new_items)

    await db.commit()
    return {"nodes": len(nodes), "collections": collections_created, "items": items_linked}


async def _descendant_node_ids(db: AsyncSession, root_id: int) -> set[int]:
    """Return all active descendant node ids of a node (excludes the root)."""
    ids: set[int] = set()
    stack = [root_id]
    while stack:
        parent = stack.pop()
        rows = await db.execute(
            select(TaxonomyNode.id).where(
                TaxonomyNode.parent_id == parent,
                TaxonomyNode.is_active == True,
            )
        )
        for (child_id,) in rows.all():
            if child_id not in ids:
                ids.add(child_id)
                stack.append(child_id)
    return ids


async def _subtree_items(db: AsyncSession, root_id: int) -> list:
    """Return active item rows across a node and all its descendants."""
    node_ids = await _descendant_node_ids(db, root_id)
    node_ids.add(root_id)
    rows = await db.execute(
        select(TaxonomyItem).where(
            TaxonomyItem.node_id.in_(node_ids),
            TaxonomyItem.is_active == True,
        )
    )
    return list(rows.scalars().all())


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
    if user is not None and user.role not in (UserRole.SUPERUSER, UserRole.ADMIN):
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
    if user is not None and user.role not in (UserRole.SUPERUSER, UserRole.ADMIN):
        raise PermissionError("Admin only")
    fs = await db.get(FeedSource, feed_id)
    if not fs:
        raise ValueError("Feed source not found")
    await db.delete(fs)
    await db.commit()

