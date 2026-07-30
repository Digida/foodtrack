import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.tracking import Batch, BatchStatus, WarehouseItem, Warehouse
from app.models.product import Product
from app.models.taxonomy import TaxonomyItem
from app.models.user import User, UserRole


PAGE_SIZE = 20


async def list_batches(db: AsyncSession, page: int = 1, status: str | None = None, product_id: int | None = None):
    q = select(Batch)
    if status:
        q = q.where(Batch.status == status)
    if product_id:
        q = q.where(Batch.product_id == product_id)
    count_q = select(func.count()).select_from(q.subquery())
    total = (await db.execute(count_q)).scalar() or 0
    items = (await db.execute(q.offset((page - 1) * PAGE_SIZE).limit(PAGE_SIZE).order_by(Batch.created_at.desc()))).scalars().all()
    result = []
    for b in items:
        prod = await db.get(Product, b.product_id)
        wh_items = await db.execute(select(WarehouseItem).where(WarehouseItem.batch_id == b.id))
        locations = []
        for wi in wh_items.scalars().all():
            wh = await db.get(Warehouse, wi.warehouse_id)
            locations.append({
                "warehouse_id": wh.id if wh else None,
                "warehouse_name": wh.name if wh else "",
                "quantity": wi.quantity,
                "zone": wi.location_zone,
                "rack": wi.location_rack,
            })
        result.append({
            "id": b.id, "batch_number": b.batch_number,
            "product_id": b.product_id, "product_name": prod.name if prod else "",
            "product_sku": prod.sku if prod else "",
            "quantity": b.quantity, "status": b.status.value if hasattr(b.status, 'value') else str(b.status),
            "serial_number": b.serial_number,
            "manufacturer_part_number": b.manufacturer_part_number,
            "production_date": str(b.production_date) if b.production_date else None,
            "expiry_date": str(b.expiry_date) if b.expiry_date else None,
            "notes": b.notes,
            "locations": locations,
            "created_at": str(b.created_at) if b.created_at else None,
        })
    return {"batches": result, "total": total, "page": page, "total_pages": max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)}


async def get_batch(db: AsyncSession, batch_id: int):
    b = await db.get(Batch, batch_id)
    if not b:
        return None
    prod = await db.get(Product, b.product_id)
    wh_items = await db.execute(select(WarehouseItem).where(WarehouseItem.batch_id == b.id))
    locations = []
    for wi in wh_items.scalars().all():
        wh = await db.get(Warehouse, wi.warehouse_id)
        locations.append({
            "warehouse_id": wh.id if wh else None,
            "warehouse_name": wh.name if wh else "",
            "quantity": wi.quantity,
            "zone": wi.location_zone,
            "rack": wi.location_rack,
            "bin": wi.location_bin,
        })
    taxonomy_info = None
    if prod:
        pass
    return {
        "id": b.id, "batch_number": b.batch_number,
        "product_id": b.product_id, "product_name": prod.name if prod else "",
        "product_sku": prod.sku if prod else "",
        "quantity": b.quantity, "status": b.status.value if hasattr(b.status, 'value') else str(b.status),
        "serial_number": b.serial_number,
        "manufacturer_part_number": b.manufacturer_part_number,
        "production_date": str(b.production_date) if b.production_date else None,
        "expiry_date": str(b.expiry_date) if b.expiry_date else None,
        "notes": b.notes,
        "locations": locations,
        "created_at": str(b.created_at) if b.created_at else None,
        "updated_at": str(b.updated_at) if b.updated_at else None,
    }


async def create_batch(db: AsyncSession, user: User, batch_number: str, product_id: int,
                       quantity: int = 0, serial_number: str | None = None,
                       manufacturer_part_number: str | None = None,
                       production_date: str | None = None,
                       expiry_date: str | None = None, notes: str | None = None):
    if user.role not in (UserRole.ADMIN, UserRole.ENTERPRISE):
        raise PermissionError("Insufficient permissions")
    prod = await db.get(Product, product_id)
    if not prod:
        raise ValueError("Product not found")
    existing = await db.execute(select(Batch).where(Batch.batch_number == batch_number))
    if existing.scalar_one_or_none():
        raise ValueError("Batch number already exists")
    b = Batch(
        batch_number=batch_number, product_id=product_id,
        quantity=quantity, serial_number=serial_number,
        manufacturer_part_number=manufacturer_part_number,
        status=BatchStatus.ACTIVE,
        created_by=user.id, notes=notes,
    )
    if production_date:
        b.production_date = datetime.fromisoformat(production_date.replace("Z", "+00:00"))
    if expiry_date:
        b.expiry_date = datetime.fromisoformat(expiry_date.replace("Z", "+00:00"))
    db.add(b)
    await db.commit()
    await db.refresh(b)
    return b


async def update_batch(db: AsyncSession, user: User, batch_id: int, data: dict):
    if user.role not in (UserRole.ADMIN, UserRole.ENTERPRISE):
        raise PermissionError("Insufficient permissions")
    b = await db.get(Batch, batch_id)
    if not b:
        raise ValueError("Batch not found")
    for k, v in data.items():
        if v is not None and hasattr(b, k):
            if k in ("production_date", "expiry_date") and isinstance(v, str):
                v = datetime.fromisoformat(v.replace("Z", "+00:00"))
            setattr(b, k, v)
    await db.commit()
    await db.refresh(b)
    return b


async def delete_batch(db: AsyncSession, user: User, batch_id: int):
    if user.role != UserRole.ADMIN:
        raise PermissionError("Admin only")
    b = await db.get(Batch, batch_id)
    if not b:
        raise ValueError("Batch not found")
    b.status = BatchStatus.RECALLED
    await db.commit()
