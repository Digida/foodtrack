from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from app.models.inventory import ItemInventory, InventoryMovement, MovementType, MovementReference
from app.models.taxonomy import TaxonomyItem
from app.models.tracking import Warehouse, WarehouseItem, Batch
from app.models.user import User, UserRole


PAGE_SIZE = 20


async def get_item_inventory(db: AsyncSession, item_id: int):
    item = await db.get(TaxonomyItem, item_id)
    if not item:
        return None

    warehouses = await db.execute(
        select(ItemInventory).where(
            ItemInventory.item_id == item_id,
            ItemInventory.total_quantity > 0,
        ).order_by(ItemInventory.total_quantity.desc())
    )
    warehouse_list = []
    total_all = 0
    total_available = 0
    total_reserved = 0
    for inv in warehouses.scalars().all():
        wh = await db.get(Warehouse, inv.warehouse_id)
        warehouse_list.append({
            "warehouse_id": inv.warehouse_id,
            "warehouse_name": wh.name if wh else "Unknown",
            "warehouse_city": wh.city if wh else None,
            "warehouse_country": wh.country if wh else None,
            "total_quantity": inv.total_quantity,
            "available_quantity": inv.available_quantity,
            "reserved_quantity": inv.reserved_quantity,
            "avg_temperature_celsius": inv.avg_temperature_celsius,
            "avg_humidity_percent": inv.avg_humidity_percent,
            "last_stocked_at": str(inv.last_stocked_at) if inv.last_stocked_at else None,
            "last_counted_at": str(inv.last_counted_at) if inv.last_counted_at else None,
        })
        total_all += inv.total_quantity
        total_available += inv.available_quantity
        total_reserved += inv.reserved_quantity

    return {
        "item_id": item_id,
        "item_name": item.common_name,
        "item_code": item.code,
        "total_quantity": total_all,
        "total_available": total_available,
        "total_reserved": total_reserved,
        "warehouse_count": len(warehouse_list),
        "warehouses": warehouse_list,
    }


async def get_item_warehouse_detail(db: AsyncSession, item_id: int, warehouse_id: int):
    inv = await db.execute(
        select(ItemInventory).where(
            ItemInventory.item_id == item_id,
            ItemInventory.warehouse_id == warehouse_id,
        )
    )
    inv = inv.scalar_one_or_none()
    if not inv:
        return None

    wh = await db.get(Warehouse, warehouse_id)

    batches = await db.execute(
        select(WarehouseItem, Batch).join(Batch, WarehouseItem.batch_id == Batch.id)
        .where(
            WarehouseItem.warehouse_id == warehouse_id,
            WarehouseItem.item_id == item_id,
            WarehouseItem.quantity > 0,
        )
        .order_by(WarehouseItem.created_at.desc())
    )
    batch_list = []
    for wi, b in batches.all():
        batch_list.append({
            "batch_id": b.id,
            "batch_number": b.batch_number,
            "quantity": wi.quantity,
            "zone": wi.location_zone,
            "rack": wi.location_rack,
            "bin": wi.location_bin,
            "last_counted_at": str(wi.last_counted_at) if wi.last_counted_at else None,
        })

    return {
        "item_id": item_id,
        "warehouse_id": warehouse_id,
        "warehouse_name": wh.name if wh else "Unknown",
        "total_quantity": inv.total_quantity,
        "available_quantity": inv.available_quantity,
        "reserved_quantity": inv.reserved_quantity,
        "avg_temperature_celsius": inv.avg_temperature_celsius,
        "avg_humidity_percent": inv.avg_humidity_percent,
        "last_stocked_at": str(inv.last_stocked_at) if inv.last_stocked_at else None,
        "last_counted_at": str(inv.last_counted_at) if inv.last_counted_at else None,
        "batches": batch_list,
    }


async def get_movement_history(db: AsyncSession, item_id: int, page: int = 1, days: int | None = None):
    q = select(InventoryMovement).where(InventoryMovement.item_id == item_id)
    if days:
        cutoff = datetime.now(timezone.utc)
        q = q.where(InventoryMovement.moved_at >= cutoff)

    count_q = select(func.count()).select_from(q.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    q = q.order_by(InventoryMovement.moved_at.desc())
    q = q.offset((page - 1) * PAGE_SIZE).limit(PAGE_SIZE)
    movements = (await db.execute(q)).scalars().all()

    results = []
    for m in movements:
        wh = await db.get(Warehouse, m.warehouse_id) if m.warehouse_id else None
        results.append({
            "id": m.id,
            "movement_type": m.movement_type.value if hasattr(m.movement_type, 'value') else str(m.movement_type),
            "quantity": m.quantity,
            "warehouse_name": wh.name if wh else None,
            "reference_type": m.reference_type.value if m.reference_type and hasattr(m.reference_type, 'value') else m.reference_type,
            "reference_id": m.reference_id,
            "notes": m.notes,
            "batch_id": m.batch_id,
            "moved_at": str(m.moved_at) if m.moved_at else None,
        })

    return {
        "movements": results,
        "total": total,
        "page": page,
        "total_pages": max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE),
    }


async def record_movement(db: AsyncSession, user: User | None, item_id: int,
                          movement_type: MovementType, quantity: int,
                          warehouse_id: int | None = None, batch_id: int | None = None,
                          reference_type: MovementReference | None = None,
                          reference_id: int | None = None, notes: str | None = None):
    if user and user.role not in (UserRole.ADMIN, UserRole.ENTERPRISE):
        raise PermissionError("Insufficient permissions")

    movement = InventoryMovement(
        item_id=item_id, batch_id=batch_id, warehouse_id=warehouse_id,
        movement_type=movement_type, quantity=quantity,
        reference_type=reference_type, reference_id=reference_id,
        notes=notes, moved_by=user.id if user else None,
    )
    db.add(movement)

    if warehouse_id:
        inv = await db.execute(
            select(ItemInventory).where(
                ItemInventory.item_id == item_id,
                ItemInventory.warehouse_id == warehouse_id,
            )
        )
        inv = inv.scalar_one_or_none()
        if not inv:
            inv = ItemInventory(
                item_id=item_id, warehouse_id=warehouse_id,
                total_quantity=0, available_quantity=0, reserved_quantity=0,
            )
            db.add(inv)

        if movement_type == MovementType.INBOUND:
            inv.total_quantity += quantity
            inv.available_quantity += quantity
            inv.last_stocked_at = datetime.now(timezone.utc)
        elif movement_type == MovementType.OUTBOUND:
            inv.total_quantity = max(0, inv.total_quantity - quantity)
            inv.available_quantity = max(0, inv.available_quantity - quantity)
        elif movement_type == MovementType.TRANSFER:
            pass
        elif movement_type == MovementType.ADJUSTMENT:
            inv.total_quantity = max(0, inv.total_quantity + quantity)
            inv.available_quantity = max(0, inv.available_quantity + quantity)
        elif movement_type == MovementType.WRITE_OFF:
            inv.total_quantity = max(0, inv.total_quantity - quantity)
            inv.available_quantity = max(0, inv.available_quantity - quantity)

    await db.commit()
    await db.refresh(movement)
    return movement


async def reconcile_from_warehouse_items(db: AsyncSession, item_id: int, warehouse_id: int):
    result = await db.execute(
        select(func.coalesce(func.sum(WarehouseItem.quantity), 0))
        .where(
            WarehouseItem.item_id == item_id,
            WarehouseItem.warehouse_id == warehouse_id,
        )
    )
    actual_qty = result.scalar() or 0

    inv = await db.execute(
        select(ItemInventory).where(
            ItemInventory.item_id == item_id,
            ItemInventory.warehouse_id == warehouse_id,
        )
    )
    inv = inv.scalar_one_or_none()
    if inv:
        diff = actual_qty - inv.total_quantity
        inv.total_quantity = actual_qty
        inv.available_quantity = actual_qty - inv.reserved_quantity
        if diff != 0:
            adj = InventoryMovement(
                item_id=item_id, warehouse_id=warehouse_id,
                movement_type=MovementType.ADJUSTMENT, quantity=diff,
                reference_type=MovementReference.AUDIT,
                notes=f"Reconciled: WarehouseItem sum = {actual_qty} (was {inv.total_quantity - diff})",
            )
            db.add(adj)
    else:
        inv = ItemInventory(
            item_id=item_id, warehouse_id=warehouse_id,
            total_quantity=actual_qty, available_quantity=actual_qty, reserved_quantity=0,
        )
        db.add(inv)

    await db.commit()
    return inv


async def transfer_between_warehouses(db: AsyncSession, user: User,
                                       item_id: int, from_warehouse_id: int,
                                       to_warehouse_id: int, quantity: int):
    if user.role not in (UserRole.ADMIN, UserRole.ENTERPRISE):
        raise PermissionError("Insufficient permissions")

    from_inv = await db.execute(
        select(ItemInventory).where(
            ItemInventory.item_id == item_id,
            ItemInventory.warehouse_id == from_warehouse_id,
        )
    )
    from_inv = from_inv.scalar_one_or_none()
    if not from_inv or from_inv.available_quantity < quantity:
        raise ValueError(f"Insufficient stock at source warehouse")

    from_inv.total_quantity -= quantity
    from_inv.available_quantity -= quantity

    to_inv = await db.execute(
        select(ItemInventory).where(
            ItemInventory.item_id == item_id,
            ItemInventory.warehouse_id == to_warehouse_id,
        )
    )
    to_inv = to_inv.scalar_one_or_none()
    if not to_inv:
        to_inv = ItemInventory(
            item_id=item_id, warehouse_id=to_warehouse_id,
            total_quantity=0, available_quantity=0, reserved_quantity=0,
        )
        db.add(to_inv)
    to_inv.total_quantity += quantity
    to_inv.available_quantity += quantity

    out_mvm = InventoryMovement(
        item_id=item_id, warehouse_id=from_warehouse_id,
        movement_type=MovementType.OUTBOUND, quantity=quantity,
        reference_type=MovementReference.TRANSFER_ORDER,
        notes=f"Transfer to warehouse {to_warehouse_id}",
        moved_by=user.id,
    )
    db.add(out_mvm)
    in_mvm = InventoryMovement(
        item_id=item_id, warehouse_id=to_warehouse_id,
        movement_type=MovementType.INBOUND, quantity=quantity,
        reference_type=MovementReference.TRANSFER_ORDER,
        notes=f"Transfer from warehouse {from_warehouse_id}",
        moved_by=user.id,
    )
    db.add(in_mvm)

    await db.commit()
    return {"from_warehouse": from_warehouse_id, "to_warehouse": to_warehouse_id, "quantity": quantity}


async def get_warehouse_items(db: AsyncSession, warehouse_id: int, page: int = 1):
    q = select(ItemInventory).where(
        ItemInventory.warehouse_id == warehouse_id,
        ItemInventory.total_quantity > 0,
    )
    count_q = select(func.count()).select_from(q.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    items = (await db.execute(
        q.order_by(ItemInventory.total_quantity.desc())
        .offset((page - 1) * PAGE_SIZE).limit(PAGE_SIZE)
    )).scalars().all()

    result = []
    for inv in items:
        item = await db.get(TaxonomyItem, inv.item_id)
        result.append({
            "item_id": inv.item_id,
            "item_name": item.common_name if item else "Unknown",
            "item_code": item.code if item else "",
            "total_quantity": inv.total_quantity,
            "available_quantity": inv.available_quantity,
            "reserved_quantity": inv.reserved_quantity,
            "last_stocked_at": str(inv.last_stocked_at) if inv.last_stocked_at else None,
        })

    return {"items": result, "total": total, "page": page, "total_pages": max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)}


async def get_inventory_summary(db: AsyncSession):
    total_items = await db.execute(select(func.count()).select_from(
        select(ItemInventory.item_id).distinct().subquery()
    ))
    total_items = total_items.scalar() or 0

    total_warehouses = await db.execute(select(func.count()).select_from(
        select(ItemInventory.warehouse_id).distinct().subquery()
    ))
    total_warehouses = total_warehouses.scalar() or 0

    total_qty = await db.execute(
        select(func.coalesce(func.sum(ItemInventory.total_quantity), 0))
    )
    total_qty = total_qty.scalar() or 0

    total_available = await db.execute(
        select(func.coalesce(func.sum(ItemInventory.available_quantity), 0))
    )
    total_available = total_available.scalar() or 0

    return {
        "total_items": total_items,
        "total_warehouses": total_warehouses,
        "total_quantity": total_qty,
        "total_available": total_available,
        "utilization_pct": round((1 - total_available / max(total_qty, 1)) * 100, 1),
    }
