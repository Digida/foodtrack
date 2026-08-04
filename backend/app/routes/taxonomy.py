from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.taxonomy import Taxonomy, TaxonomyNode, TaxonomyItem, ItemName, ItemAttribute
from app.models.user import User
from app.services.taxonomy_service import (
    list_taxonomies, get_taxonomy, get_taxonomy_tree,
    create_taxonomy, update_taxonomy, delete_taxonomy,
    create_node, update_node, delete_node,
    create_item, update_item, list_items, serialize_taxonomy,
)
from app.services.search_service import get_taxonomy_item_detail, get_taxonomy_item_by_code
from app.utils.dependencies import require_admin

router = APIRouter(prefix="/taxonomy", tags=["taxonomy"])

# ─── Food Items grouped by category (must be before /{taxonomy_id}) ─

@router.get("/items/grouped/by-category")
async def api_get_food_items_grouped(
    db: AsyncSession = Depends(get_db),
):
    """Return taxonomy items grouped by their category node name for Food Items browser."""
    from app.models.taxonomy import TaxonomyNode

    nodes_q = select(TaxonomyNode).where(
        TaxonomyNode.taxonomy_id == 1,
        TaxonomyNode.parent_id.is_(None),
        TaxonomyNode.is_active == True,
    ).order_by(TaxonomyNode.sort_order)
    nodes = (await db.execute(nodes_q)).scalars().all()

    result = []
    for node in nodes:
        items = await list_items(db, node.id)
        total = len(items)
        item_list = [{
            "id": i.id,
            "code": i.code,
            "common_name": i.common_name,
            "scientific_name": i.scientific_name,
            "genre": i.genre,
            "phylum": i.phylum,
            "family": i.family,
            "image_url": i.image_url,
            "description": (i.description or "")[:120],
        } for i in items]
        result.append({
            "category_id": node.id,
            "category_name": node.name,
            "category_code": node.code,
            "description": node.description,
            "total": total,
            "items": item_list,
        })

    return {"categories": result, "total_categories": len(result), "total_items": sum(c["total"] for c in result)}


# ─── Pydantic schemas ──────────────────────────────────────────

class TaxonomyCreate(BaseModel):
    name: str
    description: str | None = None
    icon: str | None = None


class TaxonomyUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    icon: str | None = None


class NodeCreate(BaseModel):
    code: str
    name: str
    parent_id: int | None = None
    description: str | None = None
    sort_order: int = 0


class NodeUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    sort_order: int | None = None
    is_active: bool | None = None


class ItemCreate(BaseModel):
    node_id: int
    code: str
    common_name: str
    scientific_name: str | None = None
    genre: str | None = None
    phylum: str | None = None
    tax_class: str | None = None
    order_name: str | None = None
    family: str | None = None
    gestation_period: str | None = None
    gestation_unit: str | None = None
    local_uses: str | None = None
    description: str | None = None
    image_url: str | None = None
    supply_band: str | None = None


class ItemUpdate(BaseModel):
    common_name: str | None = None
    scientific_name: str | None = None
    genre: str | None = None
    phylum: str | None = None
    tax_class: str | None = None
    order_name: str | None = None
    family: str | None = None
    gestation_period: str | None = None
    gestation_unit: str | None = None
    local_uses: str | None = None
    description: str | None = None
    image_url: str | None = None
    is_active: bool | None = None
    supply_band: str | None = None


class NameCreate(BaseModel):
    language: str
    name: str
    is_primary: bool = False


class AttributeCreate(BaseModel):
    key: str
    value: str | None = None
    unit: str | None = None


# ─── Taxonomy CRUD ──────────────────────────────────────────────

@router.get("")
async def api_list_taxonomies(
    db: AsyncSession = Depends(get_db),
):
    taxonomies = await list_taxonomies(db)
    return {"taxonomies": [serialize_taxonomy(t) for t in taxonomies]}


@router.get("/{taxonomy_id}")
async def api_get_taxonomy(
    taxonomy_id: int,
    db: AsyncSession = Depends(get_db),
):
    t = await get_taxonomy(db, taxonomy_id)
    if not t:
        raise HTTPException(status_code=404, detail="Taxonomy not found")
    return t


@router.get("/{taxonomy_id}/tree")
async def api_get_tree(
    taxonomy_id: int,
    db: AsyncSession = Depends(get_db),
):
    tree = await get_taxonomy_tree(db, taxonomy_id)
    return {"tree": tree}


@router.post("")
async def api_create_taxonomy(
    req: TaxonomyCreate,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    try:
        t = await create_taxonomy(db, req.name, req.description, req.icon)
        return {"id": t.id, "name": t.name, "icon": t.icon, "description": t.description}
    except (ValueError, PermissionError) as e:
        raise HTTPException(status_code=400 if isinstance(e, ValueError) else 403, detail=str(e))


@router.put("/{taxonomy_id}")
async def api_update_taxonomy(
    taxonomy_id: int, req: TaxonomyUpdate,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    try:
        t = await update_taxonomy(db, taxonomy_id, req.model_dump(exclude_unset=True))
        return {"id": t.id, "name": t.name}
    except (ValueError, PermissionError) as e:
        raise HTTPException(status_code=404 if isinstance(e, ValueError) else 403, detail=str(e))


@router.delete("/{taxonomy_id}")
async def api_delete_taxonomy(
    taxonomy_id: int,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    try:
        await delete_taxonomy(db, taxonomy_id)
        return {"deleted": True}
    except (ValueError, PermissionError) as e:
        raise HTTPException(status_code=404 if isinstance(e, ValueError) else 403, detail=str(e))


# ─── Nodes ─────────────────────────────────────────────────────

@router.post("/{taxonomy_id}/nodes")
async def api_create_node(
    taxonomy_id: int, req: NodeCreate,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    try:
        n = await create_node(db, taxonomy_id, req.code, req.name, req.parent_id, req.description, req.sort_order)
        return {"id": n.id, "code": n.code, "name": n.name}
    except (ValueError, PermissionError) as e:
        raise HTTPException(status_code=400 if isinstance(e, ValueError) else 403, detail=str(e))


@router.put("/nodes/{node_id}")
async def api_update_node(
    node_id: int, req: NodeUpdate,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    try:
        n = await update_node(db, node_id, req.model_dump(exclude_unset=True))
        return {"id": n.id, "name": n.name}
    except (ValueError, PermissionError) as e:
        raise HTTPException(status_code=404 if isinstance(e, ValueError) else 403, detail=str(e))


@router.delete("/nodes/{node_id}")
async def api_delete_node(
    node_id: int,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    try:
        await delete_node(db, node_id)
        return {"deleted": True}
    except (ValueError, PermissionError) as e:
        raise HTTPException(status_code=404 if isinstance(e, ValueError) else 403, detail=str(e))


# ─── Items ─────────────────────────────────────────────────────

@router.get("/nodes/{node_id}/items")
async def api_get_node_items(
    node_id: int,
    db: AsyncSession = Depends(get_db),
):
    items = await list_items(db, node_id)
    return {"items": [{"id": i.id, "node_id": i.node_id, "code": i.code, "common_name": i.common_name, "scientific_name": i.scientific_name, "genre": i.genre, "description": i.description, "image_url": i.image_url} for i in items]}


@router.post("/items")
async def api_create_item(
    req: ItemCreate,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    try:
        item = await create_item(
            db, req.node_id, req.code, req.common_name,
            req.scientific_name, req.genre, req.description, req.image_url,
            req.supply_band,
        )
        return {"id": item.id, "code": item.code, "common_name": item.common_name}
    except (ValueError, PermissionError) as e:
        raise HTTPException(status_code=400 if isinstance(e, ValueError) else 403, detail=str(e))


@router.get("/items/{item_id}")
async def api_get_item(
    item_id: int,
    db: AsyncSession = Depends(get_db),
):
    item = await get_taxonomy_item_detail(db, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Taxonomy item not found")
    return item


@router.get("/by-code/{code}")
async def api_get_item_by_code(
    code: str,
    db: AsyncSession = Depends(get_db),
):
    item = await get_taxonomy_item_by_code(db, code)
    if not item:
        raise HTTPException(status_code=404, detail="Taxonomy item not found")
    return item


@router.put("/items/{item_id}")
async def api_update_item(
    item_id: int, req: ItemUpdate,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    try:
        item = await update_item(db, item_id, req.model_dump(exclude_unset=True))
        return {"id": item.id}
    except (ValueError, PermissionError) as e:
        raise HTTPException(status_code=404 if isinstance(e, ValueError) else 403, detail=str(e))


# ─── Names ─────────────────────────────────────────────────────

@router.post("/items/{item_id}/names")
async def api_add_name(
    item_id: int, req: NameCreate,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    item = await db.get(TaxonomyItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    n = ItemName(item_id=item_id, language=req.language, name=req.name, is_primary=req.is_primary)
    db.add(n)
    await db.commit()
    await db.refresh(n)
    return {"id": n.id, "language": n.language, "name": n.name}


# ─── Attributes ────────────────────────────────────────────────

@router.post("/items/{item_id}/attributes")
async def api_add_attribute(
    item_id: int, req: AttributeCreate,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    item = await db.get(TaxonomyItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    a = ItemAttribute(item_id=item_id, key=req.key, value=req.value, unit=req.unit)
    db.add(a)
    await db.commit()
    await db.refresh(a)
    return {"id": a.id, "key": a.key}
