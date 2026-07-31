from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.services.collection_service import (
    list_collections, get_collection, create_collection, update_collection,
    delete_collection, add_item_to_collection, remove_item_from_collection,
    list_feed_sources, create_feed_source, delete_feed_source, run_ai_feed,
)
from app.utils.dependencies import get_current_user_or_guest

router = APIRouter(prefix="/collections", tags=["collections"])


class CollectionCreate(BaseModel):
    name: str
    description: str | None = None
    image_url: str | None = None
    is_ai_generated: bool = False
    feed_source_id: int | None = None


class CollectionUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    image_url: str | None = None
    is_active: bool | None = None


class AddItemRequest(BaseModel):
    item_id: int
    sort_order: int = 0
    notes: str | None = None


class FeedSourceCreate(BaseModel):
    name: str
    url: str
    feed_type: str = "rss"
    taxonomy_target_id: int | None = None
    node_target_id: int | None = None
    schedule_minutes: int = 1440


@router.get("")
async def api_list_collections(
    page: int = Query(1, ge=1),
    db: AsyncSession = Depends(get_db),
):
    return await list_collections(db, page)


@router.get("/{collection_id}")
async def api_get_collection(
    collection_id: int,
    db: AsyncSession = Depends(get_db),
):
    c = await get_collection(db, collection_id)
    if not c:
        raise HTTPException(status_code=404, detail="Collection not found")
    return c


@router.post("")
async def api_create_collection(
    req: CollectionCreate,
    user: User = Depends(get_current_user_or_guest),
    db: AsyncSession = Depends(get_db),
):
    try:
        c = await create_collection(
            db, user, req.name, req.description,
            req.image_url, req.is_ai_generated, req.feed_source_id,
        )
        return await get_collection(db, c.id)
    except (ValueError, PermissionError) as e:
        raise HTTPException(status_code=400 if isinstance(e, ValueError) else 403, detail=str(e))


@router.put("/{collection_id}")
async def api_update_collection(
    collection_id: int, req: CollectionUpdate,
    user: User = Depends(get_current_user_or_guest),
    db: AsyncSession = Depends(get_db),
):
    try:
        c = await update_collection(db, user, collection_id, req.model_dump(exclude_unset=True))
        return await get_collection(db, c.id)
    except (ValueError, PermissionError) as e:
        raise HTTPException(status_code=404 if isinstance(e, ValueError) else 403, detail=str(e))


@router.delete("/{collection_id}")
async def api_delete_collection(
    collection_id: int,
    user: User = Depends(get_current_user_or_guest),
    db: AsyncSession = Depends(get_db),
):
    try:
        await delete_collection(db, user, collection_id)
        return {"deleted": True}
    except (ValueError, PermissionError) as e:
        raise HTTPException(status_code=404 if isinstance(e, ValueError) else 403, detail=str(e))


@router.post("/{collection_id}/items")
async def api_add_item(
    collection_id: int, req: AddItemRequest,
    user: User = Depends(get_current_user_or_guest),
    db: AsyncSession = Depends(get_db),
):
    try:
        ci = await add_item_to_collection(db, user, collection_id, req.item_id, req.sort_order, req.notes)
        return {"id": ci.id, "item_id": ci.item_id}
    except (ValueError, PermissionError) as e:
        raise HTTPException(status_code=400 if isinstance(e, ValueError) else 403, detail=str(e))


@router.delete("/items/{collection_item_id}")
async def api_remove_item(
    collection_item_id: int,
    user: User = Depends(get_current_user_or_guest),
    db: AsyncSession = Depends(get_db),
):
    try:
        await remove_item_from_collection(db, user, collection_item_id)
        return {"deleted": True}
    except (ValueError, PermissionError) as e:
        raise HTTPException(status_code=404 if isinstance(e, ValueError) else 403, detail=str(e))


@router.get("/feeds/list")
async def api_list_feeds(
    db: AsyncSession = Depends(get_db),
):
    return {"feeds": await list_feed_sources(db)}


@router.post("/feeds")
async def api_create_feed(
    req: FeedSourceCreate,
    user: User = Depends(get_current_user_or_guest),
    db: AsyncSession = Depends(get_db),
):
    try:
        fs = await create_feed_source(
            db, user, req.name, req.url, req.feed_type,
            req.taxonomy_target_id, req.node_target_id, req.schedule_minutes,
        )
        return {"id": fs.id, "name": fs.name}
    except (ValueError, PermissionError) as e:
        raise HTTPException(status_code=400 if isinstance(e, ValueError) else 403, detail=str(e))


@router.post("/feeds/{feed_id}/run")
async def api_run_feed(
    feed_id: int,
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await run_ai_feed(db, feed_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/feeds/{feed_id}")
async def api_delete_feed(
    feed_id: int,
    user: User = Depends(get_current_user_or_guest),
    db: AsyncSession = Depends(get_db),
):
    try:
        await delete_feed_source(db, user, feed_id)
        return {"deleted": True}
    except (ValueError, PermissionError) as e:
        raise HTTPException(status_code=404 if isinstance(e, ValueError) else 403, detail=str(e))

