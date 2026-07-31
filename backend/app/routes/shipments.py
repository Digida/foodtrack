from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_

from app.database import get_db
from app.models.user import User
from app.models.tracking import (
    ShipmentMode, Shipment, ShipmentStatus, ShipmentBatch, Batch, Warehouse,
    ShipmentTrackingEvent, ItemShipmentStatus,
)
from app.models.product import Product
from app.services.shipping_service import (
    list_shipments, get_shipment, create_shipment, update_shipment,
    add_batch_to_shipment, add_shipment_tracking_event, delete_shipment,
    _enrich_shipment,
)
from app.utils.dependencies import get_current_user, get_current_user_or_guest

router = APIRouter(prefix="/shipments", tags=["shipments"])


@router.get("/search")
async def api_search_shipments(
    q: str | None = Query(None, description="Free text search across shipment number, carrier, vessel, port"),
    source: str | None = Query(None, description="Origin city or warehouse name"),
    destination: str | None = Query(None, description="Destination city or warehouse name"),
    port: str | None = Query(None, description="Port name (searched in origin/destination/carrier/notes)"),
    carrier: str | None = Query(None, description="Carrier name"),
    vessel: str | None = Query(None, description="Vessel or ferry name"),
    ferry_route: str | None = Query(None, description="Ferry route name"),
    mode: str | None = Query(None, description="Shipment mode: courier, ferry, truck, air, rail, multimodal"),
    status: str | None = Query(None, description="Status filter"),
    arrival_date_from: str | None = Query(None, alias="arrival_from"),
    arrival_date_to: str | None = Query(None, alias="arrival_to"),
    departure_date_from: str | None = Query(None, alias="departure_from"),
    departure_date_to: str | None = Query(None, alias="departure_to"),
    page: int = Query(1, ge=1),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Advanced cargo tracking search with multiple filters."""
    PAGE_SIZE = 20
    q_obj = select(Shipment)
    joins_needed = False

    if q:
        q_obj = q_obj.where(
            or_(
                Shipment.shipment_number.ilike(f"%{q}%"),
                Shipment.carrier_name.ilike(f"%{q}%"),
                Shipment.vessel_name.ilike(f"%{q}%"),
                Shipment.ferry_route.ilike(f"%{q}%"),
                Shipment.courier_tracking_code.ilike(f"%{q}%"),
                Shipment.notes.ilike(f"%{q}%"),
            )
        )

    if source:
        joins_needed = True
        q_obj = q_obj.join(Warehouse, Shipment.origin_id == Warehouse.id, isouter=True)
        q_obj = q_obj.where(Warehouse.name.ilike(f"%{source}%"))
    if destination:
        joins_needed = True
        q_obj = q_obj.join(Warehouse, Shipment.destination_id == Warehouse.id, isouter=True)
        q_obj = q_obj.where(Warehouse.name.ilike(f"%{destination}%"))
    if port:
        q_obj = q_obj.where(
            or_(
                Shipment.ferry_route.ilike(f"%{port}%"),
                Shipment.notes.ilike(f"%{port}%"),
                Shipment.carrier_name.ilike(f"%{port}%"),
            )
        )
    if carrier:
        q_obj = q_obj.where(Shipment.carrier_name.ilike(f"%{carrier}%"))
    if vessel:
        q_obj = q_obj.where(Shipment.vessel_name.ilike(f"%{vessel}%"))
    if ferry_route:
        q_obj = q_obj.where(Shipment.ferry_route.ilike(f"%{ferry_route}%"))
    if mode:
        q_obj = q_obj.where(Shipment.mode == mode)
    if status:
        q_obj = q_obj.where(Shipment.status == status)
    if arrival_date_from:
        q_obj = q_obj.where(Shipment.estimated_arrival >= arrival_date_from)
    if arrival_date_to:
        q_obj = q_obj.where(Shipment.estimated_arrival <= arrival_date_to)
    if departure_date_from:
        q_obj = q_obj.where(Shipment.estimated_departure >= departure_date_from)
    if departure_date_to:
        q_obj = q_obj.where(Shipment.estimated_departure <= departure_date_to)

    count_q = select(func.count()).select_from(q_obj.subquery())
    total = (await db.execute(count_q)).scalar() or 0
    items = (await db.execute(
        q_obj.offset((page - 1) * PAGE_SIZE).limit(PAGE_SIZE).order_by(Shipment.created_at.desc())
    )).scalars().all()

    result = []
    for s in items:
        result.append(await _enrich_shipment(db, s))

    return {
        "shipments": result,
        "total": total,
        "page": page,
        "page_size": PAGE_SIZE,
        "total_pages": max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE),
    }


class ShipmentCreate(BaseModel):
    shipment_number: str
    mode: ShipmentMode
    origin_id: int | None = None
    destination_id: int | None = None
    carrier_name: str | None = None
    carrier_ref: str | None = None
    vessel_name: str | None = None
    ferry_route: str | None = None
    courier_tracking_code: str | None = None
    courier_url: str | None = None
    estimated_departure: str | None = None
    estimated_arrival: str | None = None
    total_weight_kg: float | None = None
    total_volume_m3: float | None = None
    notes: str | None = None


class ShipmentUpdate(BaseModel):
    status: str | None = None
    carrier_name: str | None = None
    carrier_ref: str | None = None
    vessel_name: str | None = None
    ferry_route: str | None = None
    courier_tracking_code: str | None = None
    courier_url: str | None = None
    estimated_departure: str | None = None
    estimated_arrival: str | None = None
    actual_departure: str | None = None
    actual_arrival: str | None = None
    total_weight_kg: float | None = None
    total_volume_m3: float | None = None
    notes: str | None = None


class AddBatchRequest(BaseModel):
    batch_id: int
    quantity: int


class TrackingEventCreate(BaseModel):
    status: str
    location_name: str | None = None
    lat: float | None = None
    lng: float | None = None
    message: str | None = None
    carrier_status: str | None = None
    event_timestamp: str | None = None


@router.get("")
async def api_list_shipments(
    page: int = Query(1, ge=1),
    status: str | None = None,
    mode: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    return await list_shipments(db, page, status, mode)


@router.get("/{shipment_id}")
async def api_get_shipment(
    shipment_id: int,
    db: AsyncSession = Depends(get_db),
):
    s = await get_shipment(db, shipment_id)
    if not s:
        raise HTTPException(status_code=404, detail="Shipment not found")
    return s


@router.post("")
async def api_create_shipment(
    req: ShipmentCreate,
    user: User = Depends(get_current_user_or_guest),
    db: AsyncSession = Depends(get_db),
):
    try:
        s = await create_shipment(
            db, user, req.shipment_number, req.mode,
            req.origin_id, req.destination_id,
            req.carrier_name, req.carrier_ref,
            req.vessel_name, req.ferry_route,
            req.courier_tracking_code, req.courier_url,
            req.estimated_departure, req.estimated_arrival,
            req.total_weight_kg, req.total_volume_m3,
            req.notes,
        )
        return await get_shipment(db, s.id)
    except (ValueError, PermissionError) as e:
        raise HTTPException(status_code=400 if isinstance(e, ValueError) else 403, detail=str(e))


@router.put("/{shipment_id}")
async def api_update_shipment(
    shipment_id: int, req: ShipmentUpdate,
    user: User = Depends(get_current_user_or_guest),
    db: AsyncSession = Depends(get_db),
):
    try:
        s = await update_shipment(db, user, shipment_id, req.model_dump(exclude_unset=True))
        return await get_shipment(db, s.id)
    except (ValueError, PermissionError) as e:
        raise HTTPException(status_code=404 if isinstance(e, ValueError) else 403, detail=str(e))


@router.post("/{shipment_id}/batches")
async def api_add_batch_to_shipment(
    shipment_id: int, req: AddBatchRequest,
    user: User = Depends(get_current_user_or_guest),
    db: AsyncSession = Depends(get_db),
):
    try:
        sb = await add_batch_to_shipment(db, user, shipment_id, req.batch_id, req.quantity)
        return {"id": sb.id, "batch_id": sb.batch_id, "quantity": sb.quantity}
    except (ValueError, PermissionError) as e:
        raise HTTPException(status_code=400 if isinstance(e, ValueError) else 403, detail=str(e))


@router.post("/{shipment_id}/tracking")
async def api_add_tracking_event(
    shipment_id: int, req: TrackingEventCreate,
    user: User = Depends(get_current_user_or_guest),
    db: AsyncSession = Depends(get_db),
):
    try:
        te = await add_shipment_tracking_event(
            db, user, shipment_id, req.status, req.location_name,
            req.lat, req.lng, req.message, req.carrier_status,
            req.event_timestamp,
        )
        return {"id": te.id, "status": te.status, "event_timestamp": str(te.event_timestamp)}
    except (ValueError, PermissionError) as e:
        raise HTTPException(status_code=400 if isinstance(e, ValueError) else 403, detail=str(e))


class ItemShipmentStatusUpdate(BaseModel):
    batch_id: int
    status: ItemShipmentStatus


@router.delete("/{shipment_id}")
async def api_delete_shipment(
    shipment_id: int,
    user: User = Depends(get_current_user_or_guest),
    db: AsyncSession = Depends(get_db),
):
    try:
        await delete_shipment(db, user, shipment_id)
        return {"deleted": True}
    except (ValueError, PermissionError) as e:
        raise HTTPException(status_code=404 if isinstance(e, ValueError) else 403, detail=str(e))


@router.patch("/{shipment_id}/item-status")
async def api_update_item_shipment_status(
    shipment_id: int,
    req: ItemShipmentStatusUpdate,
    user: User = Depends(get_current_user_or_guest),
    db: AsyncSession = Depends(get_db),
):
    sb = await db.execute(
        select(ShipmentBatch).where(
            ShipmentBatch.shipment_id == shipment_id,
            ShipmentBatch.batch_id == req.batch_id,
        )
    )
    sb_row = sb.scalar_one_or_none()
    if not sb_row:
        raise HTTPException(status_code=404, detail="Shipment-batch link not found")
    sb_row.item_shipment_status = req.status
    await db.commit()
    await db.refresh(sb_row)
    return {
        "shipment_id": shipment_id,
        "batch_id": req.batch_id,
        "item_shipment_status": sb_row.item_shipment_status.value if hasattr(sb_row.item_shipment_status, 'value') else str(sb_row.item_shipment_status),
    }

