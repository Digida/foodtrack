import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, func

from app.models.taxonomy import Taxonomy, TaxonomyNode, TaxonomyItem, ItemName, ItemAttribute


# ─── Taxonomy ───────────────────────────────────────────────

async def list_taxonomies(db: AsyncSession) -> list[Taxonomy]:
    result = await db.execute(select(Taxonomy).where(Taxonomy.is_active == True).order_by(Taxonomy.name))
    return list(result.scalars().all())


async def get_taxonomy(db: AsyncSession, taxonomy_id: int) -> Taxonomy | None:
    return await db.get(Taxonomy, taxonomy_id)


async def create_taxonomy(db: AsyncSession, name: str, description: str | None = None, icon: str | None = None) -> Taxonomy:
    t = Taxonomy(name=name, description=description, icon=icon)
    db.add(t)
    await db.commit()
    await db.refresh(t)
    return t


async def update_taxonomy(db: AsyncSession, taxonomy_id: int, data: dict) -> Taxonomy | None:
    t = await db.get(Taxonomy, taxonomy_id)
    if not t:
        return None
    for k, v in data.items():
        if hasattr(t, k):
            setattr(t, k, v)
    t.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(t)
    return t


async def delete_taxonomy(db: AsyncSession, taxonomy_id: int) -> bool:
    t = await db.get(Taxonomy, taxonomy_id)
    if not t:
        return False
    t.is_active = False
    await db.commit()
    return True


# ─── TaxonomyNode ───────────────────────────────────────────

async def get_taxonomy_tree(db: AsyncSession, taxonomy_id: int) -> list[dict]:
    result = await db.execute(
        select(TaxonomyNode).where(TaxonomyNode.taxonomy_id == taxonomy_id, TaxonomyNode.is_active == True)
        .order_by(TaxonomyNode.sort_order, TaxonomyNode.name)
    )
    nodes = list(result.scalars().all())
    tree = []
    node_map = {}
    for n in nodes:
        node_map[n.id] = {"id": n.id, "parent_id": n.parent_id, "code": n.code, "name": n.name,
                          "description": n.description, "sort_order": n.sort_order, "children": []}
    for n_id, node in node_map.items():
        if node["parent_id"] and node["parent_id"] in node_map:
            node_map[node["parent_id"]]["children"].append(node)
        else:
            tree.append(node)
    return tree


async def create_node(db: AsyncSession, taxonomy_id: int, code: str, name: str,
                       parent_id: int | None = None, description: str | None = None,
                       sort_order: int = 0) -> TaxonomyNode:
    n = TaxonomyNode(taxonomy_id=taxonomy_id, parent_id=parent_id, code=code,
                     name=name, description=description, sort_order=sort_order)
    db.add(n)
    await db.commit()
    await db.refresh(n)
    return n


async def update_node(db: AsyncSession, node_id: int, data: dict) -> TaxonomyNode | None:
    n = await db.get(TaxonomyNode, node_id)
    if not n:
        return None
    for k, v in data.items():
        if hasattr(n, k):
            setattr(n, k, v)
    await db.commit()
    await db.refresh(n)
    return n


async def delete_node(db: AsyncSession, node_id: int) -> bool:
    n = await db.get(TaxonomyNode, node_id)
    if not n:
        return False
    n.is_active = False
    await db.commit()
    return True


# ─── TaxonomyItem ───────────────────────────────────────────

async def list_items(db: AsyncSession, node_id: int | None = None, search: str | None = None) -> list[TaxonomyItem]:
    q = select(TaxonomyItem).where(TaxonomyItem.is_active == True)
    if node_id:
        q = q.where(TaxonomyItem.node_id == node_id)
    if search:
        term = f"%{search}%"
        q = q.where(
            or_(
                TaxonomyItem.common_name.ilike(term),
                TaxonomyItem.scientific_name.ilike(term),
                TaxonomyItem.genre.ilike(term),
                TaxonomyItem.phylum.ilike(term),
                TaxonomyItem.tax_class.ilike(term),
                TaxonomyItem.order_name.ilike(term),
                TaxonomyItem.family.ilike(term),
                TaxonomyItem.local_uses.ilike(term),
                TaxonomyItem.code.ilike(term),
            )
        )
    q = q.order_by(TaxonomyItem.common_name)
    result = await db.execute(q)
    return list(result.scalars().all())


async def get_item(db: AsyncSession, item_id: int) -> TaxonomyItem | None:
    return await db.get(TaxonomyItem, item_id)


async def get_item_by_code(db: AsyncSession, code: str) -> TaxonomyItem | None:
    result = await db.execute(select(TaxonomyItem).where(TaxonomyItem.code == code))
    return result.scalar_one_or_none()


async def create_item(db: AsyncSession, node_id: int, code: str, common_name: str,
                       scientific_name: str | None = None, genre: str | None = None,
                       description: str | None = None, image_url: str | None = None) -> TaxonomyItem:
    item = TaxonomyItem(node_id=node_id, code=code, common_name=common_name,
                        scientific_name=scientific_name, genre=genre,
                        description=description, image_url=image_url)
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


async def update_item(db: AsyncSession, item_id: int, data: dict) -> TaxonomyItem | None:
    item = await db.get(TaxonomyItem, item_id)
    if not item:
        return None
    for k, v in data.items():
        if hasattr(item, k):
            setattr(item, k, v)
    item.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(item)
    return item


async def delete_item(db: AsyncSession, item_id: int) -> bool:
    item = await db.get(TaxonomyItem, item_id)
    if not item:
        return False
    item.is_active = False
    await db.commit()
    return True


# ─── ItemName ───────────────────────────────────────────────

async def add_item_name(db: AsyncSession, item_id: int, language: str, name: str, is_primary: bool = False) -> ItemName:
    n = ItemName(item_id=item_id, language=language, name=name, is_primary=is_primary)
    db.add(n)
    await db.commit()
    await db.refresh(n)
    return n


async def list_item_names(db: AsyncSession, item_id: int) -> list[ItemName]:
    result = await db.execute(select(ItemName).where(ItemName.item_id == item_id))
    return list(result.scalars().all())


# ─── ItemAttribute ──────────────────────────────────────────

async def add_item_attribute(db: AsyncSession, item_id: int, key: str, value: str | None = None, unit: str | None = None) -> ItemAttribute:
    a = ItemAttribute(item_id=item_id, key=key, value=value, unit=unit)
    db.add(a)
    await db.commit()
    await db.refresh(a)
    return a


async def list_item_attributes(db: AsyncSession, item_id: int) -> list[ItemAttribute]:
    result = await db.execute(select(ItemAttribute).where(ItemAttribute.item_id == item_id))
    return list(result.scalars().all())


# ─── Search ─────────────────────────────────────────────────

async def search_taxonomy(db: AsyncSession, query: str, limit: int = 20) -> list[dict]:
    term = f"%{query}%"
    items_q = select(TaxonomyItem).where(
        TaxonomyItem.is_active == True,
        or_(
            TaxonomyItem.common_name.ilike(term),
            TaxonomyItem.scientific_name.ilike(term),
            TaxonomyItem.genre.ilike(term),
            TaxonomyItem.phylum.ilike(term),
            TaxonomyItem.tax_class.ilike(term),
            TaxonomyItem.order_name.ilike(term),
            TaxonomyItem.family.ilike(term),
            TaxonomyItem.local_uses.ilike(term),
            TaxonomyItem.code.ilike(term),
        )
    ).limit(limit)
    items = (await db.execute(items_q)).scalars().all()

    names_q = select(ItemName).join(TaxonomyItem).where(
        TaxonomyItem.is_active == True,
        ItemName.name.ilike(term)
    ).limit(limit)
    name_results = (await db.execute(names_q)).scalars().all()
    name_item_ids = {n.item_id for n in name_results}
    name_items = []
    for nid in name_item_ids:
        r = await db.execute(select(TaxonomyItem).where(TaxonomyItem.id == nid))
        item = r.scalar_one_or_none()
        if item and item.id not in {i.id for i in items}:
            name_items.append(item)

    results = []
    for item in list(items) + name_items:
        names_result = await db.execute(select(ItemName).where(ItemName.item_id == item.id))
        names = [{"language": n.language, "name": n.name, "is_primary": n.is_primary} for n in names_result.scalars().all()]
        results.append({
            "id": item.id,
            "code": item.code,
            "common_name": item.common_name,
            "scientific_name": item.scientific_name,
            "genre": item.genre,
            "names": names,
        })
    return results


# ─── AI Suggestions ─────────────────────────────────────────

async def suggest_taxonomy_changes(db: AsyncSession, item_id: int, suggestion_data: dict) -> dict:
    item = await db.get(TaxonomyItem, item_id)
    if not item:
        return {"error": "Item not found"}
    return {
        "item_id": item_id,
        "current": {
            "common_name": item.common_name,
            "scientific_name": item.scientific_name,
            "genre": item.genre,
            "phylum": item.phylum,
            "tax_class": item.tax_class,
            "order_name": item.order_name,
            "family": item.family,
            "gestation_period": item.gestation_period,
            "gestation_unit": item.gestation_unit,
            "local_uses": item.local_uses,
            "description": item.description,
        },
        "suggested": suggestion_data,
        "status": "pending_review",
    }


# ─── Serialization ──────────────────────────────────────────

def serialize_taxonomy(t: Taxonomy) -> dict:
    return {
        "id": t.id, "name": t.name, "description": t.description,
        "icon": t.icon, "is_active": t.is_active,
        "created_at": t.created_at.isoformat() if t.created_at else None,
    }


def serialize_item(item: TaxonomyItem) -> dict:
    return {
        "id": item.id, "node_id": item.node_id, "code": item.code,
        "common_name": item.common_name, "scientific_name": item.scientific_name,
        "genre": item.genre, "phylum": item.phylum,
        "tax_class": item.tax_class, "order_name": item.order_name,
        "family": item.family,
        "gestation_period": item.gestation_period,
        "gestation_unit": item.gestation_unit,
        "local_uses": item.local_uses,
        "description": item.description,
        "image_url": item.image_url, "is_active": item.is_active,
    }


def serialize_item_detail(item: TaxonomyItem) -> dict:
    base = serialize_item(item)
    base["names"] = [{"id": n.id, "language": n.language, "name": n.name, "is_primary": n.is_primary}
                     for n in item.names] if item.names else []
    base["attributes"] = [{"id": a.id, "key": a.key, "value": a.value, "unit": a.unit}
                          for a in item.attributes] if item.attributes else []
    return base
