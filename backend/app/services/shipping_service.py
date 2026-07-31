import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.tracking import (
    Shipment, ShipmentStatus, ShipmentMode, ShipmentBatch,
    ShipmentTrackingEvent, Batch, Warehouse,
)
from app.models.user import User, UserRole
from app.models.product import Product


PAGE_SIZE = 20


async def list_shipments(db: AsyncSession, page: int = 1, status: str | None = None, mode: str | None = None):
    q = select(Shipment)
    if status:
        q = q.where(Shipment.status == status)
    if mode:
        q = q.where(Shipment.mode == mode)
    count_q = select(func.count()).select_from(q.subquery())
    total = (await db.execute(count_q)).scalar() or 0
    items = (await db.execute(q.offset((page - 1) * PAGE_SIZE).limit(PAGE_SIZE).order_by(Shipment.created_at.desc()))).scalars().all()
    result = []
    for s in items:
        origin = await db.get(Warehouse, s.origin_id) if s.origin_id else None
        dest = await db.get(Warehouse, s.destination_id) if s.destination_id else None
        batch_count = await db.execute(
            select(func.count()).select_from(ShipmentBatch).where(ShipmentBatch.shipment_id == s.id)
        )
        tracking_count = await db.execute(
            select(func.count()).select_from(ShipmentTrackingEvent).where(ShipmentTrackingEvent.shipment_id == s.id)
        )
        result.append({
            "id": s.id, "shipment_number": s.shipment_number,
            "mode": s.mode.value if hasattr(s.mode, 'value') else str(s.mode),
            "status": s.status.value if hasattr(s.status, 'value') else str(s.status),
            "origin_name": origin.name if origin else None,
            "destination_name": dest.name if dest else None,
            "carrier_name": s.carrier_name,
            "courier_tracking_code": s.courier_tracking_code,
            "vessel_name": s.vessel_name,
            "ferry_route": s.ferry_route,
            "estimated_departure": str(s.estimated_departure) if s.estimated_departure else None,
            "estimated_arrival": str(s.estimated_arrival) if s.estimated_arrival else None,
            "actual_departure": str(s.actual_departure) if s.actual_departure else None,
            "actual_arrival": str(s.actual_arrival) if s.actual_arrival else None,
            "batch_count": (await batch_count).scalar() or 0,
            "tracking_count": (await tracking_count).scalar() or 0,
            "created_at": str(s.created_at) if s.created_at else None,
        })
    return {"shipments": result, "total": total, "page": page, "total_pages": max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)}


async def get_shipment(db: AsyncSession, shipment_id: int):
    s = await db.get(Shipment, shipment_id)
    if not s:
        return None
    origin = await db.get(Warehouse, s.origin_id) if s.origin_id else None
    dest = await db.get(Warehouse, s.destination_id) if s.destination_id else None
    batches_result = await db.execute(
        select(ShipmentBatch, Batch).join(Batch, ShipmentBatch.batch_id == Batch.id)
        .where(ShipmentBatch.shipment_id == s.id)
    )
    batches_list = []
    for sb, b in batches_result.all():
        batches_list.append({
            "id": sb.id, "batch_id": b.id, "batch_number": b.batch_number,
            "quantity": sb.quantity,
        })
    tracking_result = await db.execute(
        select(ShipmentTrackingEvent).where(ShipmentTrackingEvent.shipment_id == s.id)
        .order_by(ShipmentTrackingEvent.event_timestamp.asc())
    )
    tracking_list = []
    for te in tracking_result.scalars().all():
        tracking_list.append({
            "id": te.id, "status": te.status, "location_name": te.location_name,
            "lat": te.lat, "lng": te.lng, "message": te.message,
            "carrier_status": te.carrier_status,
            "event_timestamp": str(te.event_timestamp) if te.event_timestamp else None,
        })
    return {
        "id": s.id, "shipment_number": s.shipment_number,
        "mode": s.mode.value if hasattr(s.mode, 'value') else str(s.mode),
        "status": s.status.value if hasattr(s.status, 'value') else str(s.status),
        "origin": {"id": origin.id, "name": origin.name, "city": origin.city} if origin else None,
        "destination": {"id": dest.id, "name": dest.name, "city": dest.city} if dest else None,
        "carrier_name": s.carrier_name, "carrier_ref": s.carrier_ref,
        "vessel_name": s.vessel_name, "ferry_route": s.ferry_route,
        "courier_tracking_code": s.courier_tracking_code,
        "courier_url": s.courier_url,
        "estimated_departure": str(s.estimated_departure) if s.estimated_departure else None,
        "estimated_arrival": str(s.estimated_arrival) if s.estimated_arrival else None,
        "actual_departure": str(s.actual_departure) if s.actual_departure else None,
        "actual_arrival": str(s.actual_arrival) if s.actual_arrival else None,
        "total_weight_kg": s.total_weight_kg,
        "total_volume_m3": s.total_volume_m3,
        "notes": s.notes,
        "batches": batches_list,
        "tracking_events": tracking_list,
        "created_at": str(s.created_at) if s.created_at else None,
    }


async def create_shipment(db: AsyncSession, user: User, shipment_number: str, mode: ShipmentMode,
                          origin_id: int | None = None, destination_id: int | None = None,
                          carrier_name: str | None = None, carrier_ref: str | None = None,
                          vessel_name: str | None = None, ferry_route: str | None = None,
                          courier_tracking_code: str | None = None, courier_url: str | None = None,
                          estimated_departure: str | None = None,
                          estimated_arrival: str | None = None,
                          total_weight_kg: float | None = None,
                          total_volume_m3: float | None = None,
                          notes: str | None = None):
    if user.role not in (UserRole.SUPERUSER, UserRole.ADMIN, UserRole.ENTERPRISE):
        raise PermissionError("Insufficient permissions")
    existing = await db.execute(select(Shipment).where(Shipment.shipment_number == shipment_number))
    if existing.scalar_one_or_none():
        raise ValueError("Shipment number already exists")
    s = Shipment(
        shipment_number=shipment_number, mode=mode, status=ShipmentStatus.CREATED,
        origin_id=origin_id, destination_id=destination_id,
        carrier_name=carrier_name, carrier_ref=carrier_ref,
        vessel_name=vessel_name, ferry_route=ferry_route,
        courier_tracking_code=courier_tracking_code, courier_url=courier_url,
        total_weight_kg=total_weight_kg, total_volume_m3=total_volume_m3,
        notes=notes, created_by=user.id,
    )
    if estimated_departure:
        s.estimated_departure = datetime.fromisoformat(estimated_departure.replace("Z", "+00:00"))
    if estimated_arrival:
        s.estimated_arrival = datetime.fromisoformat(estimated_arrival.replace("Z", "+00:00"))
    db.add(s)
    await db.commit()
    await db.refresh(s)
    return s


async def update_shipment(db: AsyncSession, user: User, shipment_id: int, data: dict):
    if user.role not in (UserRole.SUPERUSER, UserRole.ADMIN, UserRole.ENTERPRISE):
        raise PermissionError("Insufficient permissions")
    s = await db.get(Shipment, shipment_id)
    if not s:
        raise ValueError("Shipment not found")
    for k, v in data.items():
        if v is not None and hasattr(s, k):
            if k in ("estimated_departure", "estimated_arrival", "actual_departure", "actual_arrival") and isinstance(v, str):
                v = datetime.fromisoformat(v.replace("Z", "+00:00"))
            setattr(s, k, v)
    await db.commit()
    await db.refresh(s)
    return s


async def add_batch_to_shipment(db: AsyncSession, user: User, shipment_id: int, batch_id: int, quantity: int):
    if user.role not in (UserRole.SUPERUSER, UserRole.ADMIN, UserRole.ENTERPRISE):
        raise PermissionError("Insufficient permissions")
    s = await db.get(Shipment, shipment_id)
    if not s:
        raise ValueError("Shipment not found")
    b = await db.get(Batch, batch_id)
    if not b:
        raise ValueError("Batch not found")
    sb = ShipmentBatch(shipment_id=shipment_id, batch_id=batch_id, quantity=quantity)
    db.add(sb)
    await db.commit()
    return sb


async def add_shipment_tracking_event(db: AsyncSession, user: User, shipment_id: int,
                                       status: str, location_name: str | None = None,
                                       lat: float | None = None, lng: float | None = None,
                                       message: str | None = None,
                                       carrier_status: str | None = None,
                                       event_timestamp: str | None = None):
    if user.role == UserRole.VIEWER:
        raise PermissionError("Insufficient permissions")
    s = await db.get(Shipment, shipment_id)
    if not s:
        raise ValueError("Shipment not found")
    ts = datetime.fromisoformat(event_timestamp.replace("Z", "+00:00")) if event_timestamp else datetime.now(timezone.utc)
    te = ShipmentTrackingEvent(
        shipment_id=shipment_id, status=status, location_name=location_name,
        lat=lat, lng=lng, message=message, carrier_status=carrier_status,
        event_timestamp=ts,
    )
    db.add(te)
    s.status = status
    await db.commit()
    await db.refresh(te)
    return te


async def delete_shipment(db: AsyncSession, user: User, shipment_id: int):
    if user.role not in (UserRole.SUPERUSER, UserRole.ADMIN):
        raise PermissionError("Admin only")
    s = await db.get(Shipment, shipment_id)
    if not s:
        raise ValueError("Shipment not found")
    await db.delete(s)
    await db.commit()


async def _enrich_shipment(db: AsyncSession, s: Shipment) -> dict:
    """Enrich a shipment for search results — lightweight version of get_shipment."""
    origin = await db.get(Warehouse, s.origin_id) if s.origin_id else None
    dest = await db.get(Warehouse, s.destination_id) if s.destination_id else None
    batches_result = await db.execute(
        select(ShipmentBatch, Batch).join(Batch, ShipmentBatch.batch_id == Batch.id)
        .where(ShipmentBatch.shipment_id == s.id)
    )
    batches_list = []
    for sb, b in batches_result.all():
        batches_list.append({
            "id": sb.id, "batch_id": b.id, "batch_number": b.batch_number,
            "quantity": sb.quantity,
        })
    tracking_result = await db.execute(
        select(ShipmentTrackingEvent).where(ShipmentTrackingEvent.shipment_id == s.id)
        .order_by(ShipmentTrackingEvent.event_timestamp.asc())
    )
    tracking_list = []
    for te in tracking_result.scalars().all():
        tracking_list.append({
            "id": te.id, "status": te.status, "location_name": te.location_name,
            "lat": te.lat, "lng": te.lng, "message": te.message,
            "carrier_status": te.carrier_status,
            "event_timestamp": str(te.event_timestamp) if te.event_timestamp else None,
        })

    # Get product info from batches
    products_list = []
    for sb in batches_list:
        b = await db.get(Batch, sb["batch_id"])
        if b:
            prod = await db.get(Product, b.product_id)
            if prod:
                products_list.append({
                    "batch_id": b.id,
                    "batch_number": b.batch_number,
                    "product_id": prod.id,
                    "product_name": prod.name,
                    "product_sku": prod.sku,
                })

    status_emoji = s.status.value if hasattr(s.status, 'value') else str(s.status)
    return {
        "id": s.id, "shipment_number": s.shipment_number,
        "mode": s.mode.value if hasattr(s.mode, 'value') else str(s.mode),
        "status": status_emoji,
        "status_label": status_emoji.replace("_", " ").title(),
        "origin": {"id": origin.id, "name": origin.name, "city": origin.city, "country": origin.country} if origin else None,
        "destination": {"id": dest.id, "name": dest.name, "city": dest.city, "country": dest.country} if dest else None,
        "carrier_name": s.carrier_name, "carrier_ref": s.carrier_ref,
        "vessel_name": s.vessel_name, "ferry_route": s.ferry_route,
        "courier_tracking_code": s.courier_tracking_code,
        "courier_url": s.courier_url,
        "estimated_departure": str(s.estimated_departure) if s.estimated_departure else None,
        "estimated_arrival": str(s.estimated_arrival) if s.estimated_arrival else None,
        "actual_departure": str(s.actual_departure) if s.actual_departure else None,
        "actual_arrival": str(s.actual_arrival) if s.actual_arrival else None,
        "total_weight_kg": s.total_weight_kg,
        "total_volume_m3": s.total_volume_m3,
        "notes": s.notes,
        "products": products_list,
        "batches": batches_list,
        "tracking_events": tracking_list,
        "batch_count": len(batches_list),
        "tracking_count": len(tracking_list),
        "created_at": str(s.created_at) if s.created_at else None,
    }
