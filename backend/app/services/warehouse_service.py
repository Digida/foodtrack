import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.tracking import Warehouse, WarehouseItem, Batch
from app.models.user import User, UserRole


PAGE_SIZE = 20


async def list_warehouses(db: AsyncSession, page: int = 1):
    q = select(Warehouse).where(Warehouse.is_active == True)
    count_q = select(func.count()).select_from(q.subquery())
    total = (await db.execute(count_q)).scalar() or 0
    items = (await db.execute(q.offset((page - 1) * PAGE_SIZE).limit(PAGE_SIZE).order_by(Warehouse.name))).scalars().all()
    result = []
    for w in items:
        item_count = await db.execute(select(func.count()).select_from(WarehouseItem).where(WarehouseItem.warehouse_id == w.id))
        result.append({
            "id": w.id, "code": w.code, "name": w.name,
            "address": w.address, "city": w.city, "country": w.country,
            "capacity_items": w.capacity_items,
            "temperature_celsius": w.temperature_celsius,
            "humidity_percent": w.humidity_percent,
            "contact_name": w.contact_name, "contact_phone": w.contact_phone,
            "lat": w.lat, "lng": w.lng,
            "item_count": (await db.execute(item_count)).scalar() or 0,
            "created_at": str(w.created_at) if w.created_at else None,
        })
    return {"warehouses": result, "total": total, "page": page, "total_pages": max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)}


async def get_warehouse(db: AsyncSession, warehouse_id: int):
    w = await db.get(Warehouse, warehouse_id)
    if not w or not w.is_active:
        return None
    items_result = await db.execute(
        select(WarehouseItem, Batch).join(Batch, WarehouseItem.batch_id == Batch.id)
        .where(WarehouseItem.warehouse_id == warehouse_id)
    )
    items_list = []
    for wi, b in items_result.all():
        items_list.append({
            "id": wi.id, "batch_id": b.id, "batch_number": b.batch_number,
            "quantity": wi.quantity,
            "zone": wi.location_zone, "rack": wi.location_rack, "bin": wi.location_bin,
            "last_counted_at": str(wi.last_counted_at) if wi.last_counted_at else None,
        })
    return {
        "id": w.id, "code": w.code, "name": w.name,
        "address": w.address, "city": w.city, "country": w.country,
        "lat": w.lat, "lng": w.lng,
        "contact_name": w.contact_name, "contact_phone": w.contact_phone,
        "capacity_items": w.capacity_items,
        "temperature_celsius": w.temperature_celsius,
        "humidity_percent": w.humidity_percent,
        "items": items_list,
        "created_at": str(w.created_at) if w.created_at else None,
    }


async def create_warehouse(db: AsyncSession, user: User, code: str, name: str,
                           address: str | None = None, city: str | None = None,
                           country: str | None = None, lat: float | None = None,
                           lng: float | None = None, contact_name: str | None = None,
                           contact_phone: str | None = None, capacity_items: int | None = None,
                           temperature_celsius: float | None = None,
                           humidity_percent: float | None = None):
    if user.role not in (UserRole.SUPERUSER, UserRole.ADMIN, UserRole.ENTERPRISE):
        raise PermissionError("Insufficient permissions")
    existing = await db.execute(select(Warehouse).where(Warehouse.code == code))
    if existing.scalar_one_or_none():
        raise ValueError("Warehouse code already exists")
    w = Warehouse(
        code=code, name=name, address=address, city=city, country=country,
        lat=lat, lng=lng, contact_name=contact_name, contact_phone=contact_phone,
        capacity_items=capacity_items, temperature_celsius=temperature_celsius,
        humidity_percent=humidity_percent,
    )
    db.add(w)
    await db.commit()
    await db.refresh(w)
    return w


async def update_warehouse(db: AsyncSession, user: User, warehouse_id: int, data: dict):
    if user.role not in (UserRole.SUPERUSER, UserRole.ADMIN, UserRole.ENTERPRISE):
        raise PermissionError("Insufficient permissions")
    w = await db.get(Warehouse, warehouse_id)
    if not w:
        raise ValueError("Warehouse not found")
    for k, v in data.items():
        if v is not None and hasattr(w, k):
            setattr(w, k, v)
    await db.commit()
    await db.refresh(w)
    return w


async def delete_warehouse(db: AsyncSession, user: User, warehouse_id: int):
    if user.role not in (UserRole.SUPERUSER, UserRole.ADMIN):
        raise PermissionError("Admin only")
    w = await db.get(Warehouse, warehouse_id)
    if not w:
        raise ValueError("Warehouse not found")
    w.is_active = False
    await db.commit()


async def add_warehouse_item(db: AsyncSession, user: User, warehouse_id: int,
                              batch_id: int, quantity: int, zone: str | None = None,
                              rack: str | None = None, bin: str | None = None):
    if user.role not in (UserRole.SUPERUSER, UserRole.ADMIN, UserRole.ENTERPRISE):
        raise PermissionError("Insufficient permissions")
    wh = await db.get(Warehouse, warehouse_id)
    if not wh or not wh.is_active:
        raise ValueError("Warehouse not found")
    b = await db.get(Batch, batch_id)
    if not b:
        raise ValueError("Batch not found")
    existing = await db.execute(
        select(WarehouseItem).where(
            WarehouseItem.warehouse_id == warehouse_id,
            WarehouseItem.batch_id == batch_id,
            WarehouseItem.location_zone == zone,
            WarehouseItem.location_rack == rack,
        )
    )
    item = existing.scalar_one_or_none()
    if item:
        item.quantity += quantity
    else:
        item = WarehouseItem(warehouse_id=warehouse_id, batch_id=batch_id,
                             quantity=quantity, location_zone=zone,
                             location_rack=rack, location_bin=bin)
        db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


async def update_warehouse_item(db: AsyncSession, user: User, item_id: int, data: dict):
    if user.role not in (UserRole.SUPERUSER, UserRole.ADMIN, UserRole.ENTERPRISE):
        raise PermissionError("Insufficient permissions")
    item = await db.get(WarehouseItem, item_id)
    if not item:
        raise ValueError("Warehouse item not found")
    for k, v in data.items():
        if v is not None and hasattr(item, k):
            setattr(item, k, v)
    await db.commit()
    await db.refresh(item)
    return item


async def remove_warehouse_item(db: AsyncSession, user: User, item_id: int):
    if user.role not in (UserRole.SUPERUSER, UserRole.ADMIN):
        raise PermissionError("Admin only")
    item = await db.get(WarehouseItem, item_id)
    if not item:
        raise ValueError("Warehouse item not found")
    await db.delete(item)
    await db.commit()
