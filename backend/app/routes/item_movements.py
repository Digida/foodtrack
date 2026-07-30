from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.taxonomy import TaxonomyItem
from app.services.item_detail_service import get_item_detail, get_item_timeline, get_item_provenance
from app.services.item_movement_service import (
    get_item_shipments, get_item_tracking,
    get_item_transit_summary, predict_item_eta,
)
from app.services.inventory_service import get_item_inventory, get_movement_history
from app.services.cargo_service import list_cargo_for_item

router = APIRouter(prefix="/items", tags=["items"])


@router.get("/{item_id}/detail")
async def api_item_detail(
    item_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await get_item_detail(db, item_id)
    if not result:
        raise HTTPException(status_code=404, detail="Item not found")
    return result


@router.get("/{item_id}/timeline")
async def api_item_timeline(
    item_id: int,
    db: AsyncSession = Depends(get_db),
):
    item = await db.get(TaxonomyItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return await get_item_timeline(db, item_id)


@router.get("/{item_id}/provenance")
async def api_item_provenance(
    item_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await get_item_provenance(db, item_id)
    if not result:
        raise HTTPException(status_code=404, detail="Item not found")
    return result


@router.get("/{item_id}/shipments")
async def api_item_shipments(
    item_id: int,
    page: int = Query(1, ge=1),
    db: AsyncSession = Depends(get_db),
):
    result = await get_item_shipments(db, item_id, page)
    if not result:
        raise HTTPException(status_code=404, detail="Item not found")
    return result


@router.get("/{item_id}/tracking")
async def api_item_tracking(
    item_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await get_item_tracking(db, item_id)
    if not result:
        raise HTTPException(status_code=404, detail="Item not found")
    return result


@router.get("/{item_id}/transit-summary")
async def api_item_transit_summary(
    item_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await get_item_transit_summary(db, item_id)
    if not result:
        raise HTTPException(status_code=404, detail="Item not found")
    return result


@router.get("/{item_id}/eta")
async def api_item_eta(
    item_id: int,
    destination_id: int = Query(..., description="Destination warehouse ID"),
    db: AsyncSession = Depends(get_db),
):
    result = await predict_item_eta(db, item_id, destination_id)
    if not result:
        raise HTTPException(status_code=404, detail="Item not found")
    return result


@router.get("/{item_id}/storage")
async def api_item_storage(
    item_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await get_item_inventory(db, item_id)
    if not result:
        raise HTTPException(status_code=404, detail="Item not found")
    return result


@router.get("/{item_id}/movements")
async def api_item_movements(
    item_id: int,
    page: int = Query(1, ge=1),
    days: int | None = Query(None, description="Filter by last N days"),
    db: AsyncSession = Depends(get_db),
):
    result = await get_movement_history(db, item_id, page, days)
    if not result:
        raise HTTPException(status_code=404, detail="Item not found")
    return result


@router.get("/{item_id}/cargo")
async def api_item_cargo(
    item_id: int,
    page: int = Query(1, ge=1),
    db: AsyncSession = Depends(get_db),
):
    return await list_cargo_for_item(db, item_id, page)
