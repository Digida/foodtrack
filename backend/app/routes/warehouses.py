from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.services.warehouse_service import (
    list_warehouses, get_warehouse, create_warehouse, update_warehouse,
    delete_warehouse, add_warehouse_item, update_warehouse_item, remove_warehouse_item,
)
from app.utils.dependencies import get_current_user_or_guest

router = APIRouter(prefix="/warehouses", tags=["warehouses"])


class WarehouseCreate(BaseModel):
    code: str
    name: str
    address: str | None = None
    city: str | None = None
    country: str | None = None
    lat: float | None = None
    lng: float | None = None
    contact_name: str | None = None
    contact_phone: str | None = None
    capacity_items: int | None = None
    temperature_celsius: float | None = None
    humidity_percent: float | None = None


class WarehouseUpdate(BaseModel):
    name: str | None = None
    address: str | None = None
    city: str | None = None
    country: str | None = None
    lat: float | None = None
    lng: float | None = None
    contact_name: str | None = None
    contact_phone: str | None = None
    capacity_items: int | None = None
    temperature_celsius: float | None = None
    humidity_percent: float | None = None
    is_active: bool | None = None


class WarehouseItemCreate(BaseModel):
    batch_id: int
    quantity: int
    zone: str | None = None
    rack: str | None = None
    bin: str | None = None


class WarehouseItemUpdate(BaseModel):
    quantity: int | None = None
    zone: str | None = None
    rack: str | None = None
    bin: str | None = None


@router.get("")
async def api_list_warehouses(
    page: int = Query(1, ge=1),
    db: AsyncSession = Depends(get_db),
):
    return await list_warehouses(db, page)


@router.get("/{warehouse_id}")
async def api_get_warehouse(
    warehouse_id: int,
    db: AsyncSession = Depends(get_db),
):
    w = await get_warehouse(db, warehouse_id)
    if not w:
        raise HTTPException(status_code=404, detail="Warehouse not found")
    return w


@router.post("")
async def api_create_warehouse(
    req: WarehouseCreate,
    user: User = Depends(get_current_user_or_guest),
    db: AsyncSession = Depends(get_db),
):
    try:
        w = await create_warehouse(
            db, user, req.code, req.name, req.address, req.city, req.country,
            req.lat, req.lng, req.contact_name, req.contact_phone,
            req.capacity_items, req.temperature_celsius, req.humidity_percent,
        )
        return await get_warehouse(db, w.id)
    except (ValueError, PermissionError) as e:
        raise HTTPException(status_code=400 if isinstance(e, ValueError) else 403, detail=str(e))


@router.put("/{warehouse_id}")
async def api_update_warehouse(
    warehouse_id: int, req: WarehouseUpdate,
    user: User = Depends(get_current_user_or_guest),
    db: AsyncSession = Depends(get_db),
):
    try:
        w = await update_warehouse(db, user, warehouse_id, req.model_dump(exclude_unset=True))
        return await get_warehouse(db, w.id)
    except (ValueError, PermissionError) as e:
        raise HTTPException(status_code=404 if isinstance(e, ValueError) else 403, detail=str(e))


@router.delete("/{warehouse_id}")
async def api_delete_warehouse(
    warehouse_id: int,
    user: User = Depends(get_current_user_or_guest),
    db: AsyncSession = Depends(get_db),
):
    try:
        await delete_warehouse(db, user, warehouse_id)
        return {"deleted": True}
    except (ValueError, PermissionError) as e:
        raise HTTPException(status_code=404 if isinstance(e, ValueError) else 403, detail=str(e))


@router.post("/{warehouse_id}/items")
async def api_add_warehouse_item(
    warehouse_id: int, req: WarehouseItemCreate,
    user: User = Depends(get_current_user_or_guest),
    db: AsyncSession = Depends(get_db),
):
    try:
        item = await add_warehouse_item(
            db, user, warehouse_id, req.batch_id, req.quantity,
            req.zone, req.rack, req.bin,
        )
        return {"id": item.id, "batch_id": item.batch_id, "quantity": item.quantity}
    except (ValueError, PermissionError) as e:
        raise HTTPException(status_code=400 if isinstance(e, ValueError) else 403, detail=str(e))


@router.put("/items/{item_id}")
async def api_update_warehouse_item(
    item_id: int, req: WarehouseItemUpdate,
    user: User = Depends(get_current_user_or_guest),
    db: AsyncSession = Depends(get_db),
):
    try:
        item = await update_warehouse_item(db, user, item_id, req.model_dump(exclude_unset=True))
        return {"id": item.id, "batch_id": item.batch_id, "quantity": item.quantity}
    except (ValueError, PermissionError) as e:
        raise HTTPException(status_code=404 if isinstance(e, ValueError) else 403, detail=str(e))


@router.delete("/items/{item_id}")
async def api_remove_warehouse_item(
    item_id: int,
    user: User = Depends(get_current_user_or_guest),
    db: AsyncSession = Depends(get_db),
):
    try:
        await remove_warehouse_item(db, user, item_id)
        return {"deleted": True}
    except (ValueError, PermissionError) as e:
        raise HTTPException(status_code=404 if isinstance(e, ValueError) else 403, detail=str(e))

