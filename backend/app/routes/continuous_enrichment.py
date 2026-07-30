from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.services.enrichment_service import (
    enrich_collection_from_feed,
    enrich_taxonomy_from_web,
    suggest_taxonomy_nodes,
    auto_categorize_collection,
    suggest_collection_items,
    backfill_item_data,
    refresh_collections_schedule,
    list_enrichment_logs,
    list_enrichment_suggestions,
    update_suggestion_status,
)
from app.utils.dependencies import get_current_user

router = APIRouter(prefix="/continuous-enrichment", tags=["continuous-enrichment"])


@router.post("/collections/{collection_id}/feed")
async def api_enrich_collection_feed(
    collection_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await enrich_collection_from_feed(db, user, collection_id)
    except (ValueError, PermissionError) as e:
        raise HTTPException(status_code=400 if isinstance(e, ValueError) else 403, detail=str(e))


@router.post("/taxonomy/explore-web")
async def api_enrich_taxonomy(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await enrich_taxonomy_from_web(db, user)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.post("/items/{item_id}/suggest-classification")
async def api_suggest_classification(
    item_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await suggest_taxonomy_nodes(db, user, item_id)
    except (ValueError, PermissionError) as e:
        raise HTTPException(status_code=400 if isinstance(e, ValueError) else 403, detail=str(e))


@router.post("/collections/{collection_id}/auto-categorize")
async def api_auto_categorize(
    collection_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await auto_categorize_collection(db, user, collection_id)
    except (ValueError, PermissionError) as e:
        raise HTTPException(status_code=400 if isinstance(e, ValueError) else 403, detail=str(e))


@router.post("/collections/{collection_id}/suggest-items")
async def api_suggest_items(
    collection_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await suggest_collection_items(db, user, collection_id)
    except (ValueError, PermissionError) as e:
        raise HTTPException(status_code=400 if isinstance(e, ValueError) else 403, detail=str(e))


@router.post("/backfill-item-data")
async def api_backfill(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await backfill_item_data(db, user)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.post("/schedule-refresh")
async def api_schedule_refresh(
    db: AsyncSession = Depends(get_db),
):
    return await refresh_collections_schedule(db)


@router.get("/logs")
async def api_list_logs(
    page: int = Query(1, ge=1),
    source: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    return await list_enrichment_logs(db, page, source)


@router.get("/suggestions")
async def api_list_suggestions(
    page: int = Query(1, ge=1),
    status: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    return await list_enrichment_suggestions(db, page, status)


@router.patch("/suggestions/{suggestion_id}/status")
async def api_update_suggestion(
    suggestion_id: int,
    status: str = Query(..., description="New status (open, accepted, rejected)"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        sug = await update_suggestion_status(db, user, suggestion_id, status)
        return {"id": sug.id, "status": sug.status}
    except (ValueError, PermissionError) as e:
        raise HTTPException(status_code=400 if isinstance(e, ValueError) else 403, detail=str(e))
