from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.inventory import MovementType, MovementReference
from app.services.inventory_service import (
    get_item_inventory, get_item_warehouse_detail, get_movement_history,
    record_movement, transfer_between_warehouses, get_warehouse_items,
    get_inventory_summary, reconcile_from_warehouse_items,
)
from app.utils.dependencies import get_current_user

router = APIRouter(prefix="/inventory", tags=["inventory"])


class MovementCreate(BaseModel):
    item_id: int
    movement_type: MovementType
    quantity: int
    warehouse_id: int
    batch_id: int | None = None
    reference_type: MovementReference | None = None
    reference_id: int | None = None
    notes: str | None = None


class TransferCreate(BaseModel):
    item_id: int
    from_warehouse_id: int
    to_warehouse_id: int
    quantity: int


@router.get("/summary")
async def api_inventory_summary(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_inventory_summary(db)


@router.get("/items/{item_id}")
async def api_get_item_inventory(
    item_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await get_item_inventory(db, item_id)
    if not result:
        raise HTTPException(status_code=404, detail="Item not found")
    return result


@router.get("/items/{item_id}/warehouses/{warehouse_id}")
async def api_get_item_warehouse_detail(
    item_id: int, warehouse_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await get_item_warehouse_detail(db, item_id, warehouse_id)
    if not result:
        raise HTTPException(status_code=404, detail="No inventory record found")
    return result


@router.get("/items/{item_id}/movements")
async def api_get_movement_history(
    item_id: int,
    page: int = Query(1, ge=1),
    days: int | None = Query(None, description="Filter by last N days"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_movement_history(db, item_id, page, days)


@router.post("/movements")
async def api_record_movement(
    req: MovementCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        m = await record_movement(
            db, user, req.item_id, req.movement_type, req.quantity,
            req.warehouse_id, req.batch_id,
            req.reference_type, req.reference_id, req.notes,
        )
        return {"id": m.id, "movement_type": m.movement_type.value if hasattr(m.movement_type, 'value') else str(m.movement_type)}
    except (ValueError, PermissionError) as e:
        raise HTTPException(status_code=400 if isinstance(e, ValueError) else 403, detail=str(e))


@router.post("/transfer")
async def api_transfer_inventory(
    req: TransferCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await transfer_between_warehouses(
            db, user, req.item_id, req.from_warehouse_id,
            req.to_warehouse_id, req.quantity,
        )
        return result
    except (ValueError, PermissionError) as e:
        raise HTTPException(status_code=400 if isinstance(e, ValueError) else 403, detail=str(e))


@router.get("/warehouses/{warehouse_id}/items")
async def api_get_warehouse_items(
    warehouse_id: int,
    page: int = Query(1, ge=1),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_warehouse_items(db, warehouse_id, page)


@router.post("/reconcile/{item_id}/{warehouse_id}")
async def api_reconcile_inventory(
    item_id: int, warehouse_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        inv = await reconcile_from_warehouse_items(db, item_id, warehouse_id)
        return {"item_id": item_id, "warehouse_id": warehouse_id, "total_quantity": inv.total_quantity}
    except (ValueError, PermissionError) as e:
        raise HTTPException(status_code=403, detail=str(e))
