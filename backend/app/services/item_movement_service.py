from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.taxonomy import TaxonomyItem
from app.models.tracking import (
    Shipment, ShipmentBatch, ShipmentTrackingEvent, ShipmentStatus,
    Batch, Warehouse,
)
from app.models.product import Product
from app.models.user import User, UserRole


PAGE_SIZE = 20


async def get_item_shipments(db: AsyncSession, item_id: int, page: int = 1):
    item = await db.get(TaxonomyItem, item_id)
    if not item:
        return None

    q = select(Shipment).distinct().join(ShipmentBatch).where(
        ShipmentBatch.item_id == item_id
    )
    count_q = select(func.count()).select_from(q.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    shipments = (await db.execute(
        q.order_by(Shipment.created_at.desc())
        .offset((page - 1) * PAGE_SIZE).limit(PAGE_SIZE)
    )).scalars().all()

    results = []
    for s in shipments:
        origin = await db.get(Warehouse, s.origin_id) if s.origin_id else None
        dest = await db.get(Warehouse, s.destination_id) if s.destination_id else None

        sb = await db.execute(
            select(func.coalesce(func.sum(ShipmentBatch.quantity), 0))
            .where(
                ShipmentBatch.shipment_id == s.id,
                ShipmentBatch.item_id == item_id,
            )
        )
        item_qty = sb.scalar() or 0

        results.append({
            "shipment_id": s.id,
            "shipment_number": s.shipment_number,
            "mode": s.mode.value if hasattr(s.mode, 'value') else str(s.mode),
            "status": s.status.value if hasattr(s.status, 'value') else str(s.status),
            "carrier_name": s.carrier_name,
            "vessel_name": s.vessel_name,
            "ferry_route": s.ferry_route,
            "origin": {"name": origin.name, "city": origin.city} if origin else None,
            "destination": {"name": dest.name, "city": dest.city} if dest else None,
            "item_quantity": item_qty,
            "estimated_departure": str(s.estimated_departure) if s.estimated_departure else None,
            "estimated_arrival": str(s.estimated_arrival) if s.estimated_arrival else None,
            "created_at": str(s.created_at) if s.created_at else None,
        })

    return {
        "item_id": item_id,
        "item_name": item.common_name,
        "shipments": results,
        "total": total,
        "page": page,
        "total_pages": max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE),
    }


async def get_item_tracking(db: AsyncSession, item_id: int):
    item = await db.get(TaxonomyItem, item_id)
    if not item:
        return None

    active_shipments = await db.execute(
        select(Shipment).distinct().join(ShipmentBatch).where(
            ShipmentBatch.item_id == item_id,
            Shipment.status.in_(["picked_up", "in_transit", "at_ferry", "on_ferry",
                                  "arrived_port", "out_for_delivery"]),
        )
        .order_by(Shipment.estimated_arrival.asc())
    )

    tracking_list = []
    for s in active_shipments.scalars().all():
        origin = await db.get(Warehouse, s.origin_id) if s.origin_id else None
        dest = await db.get(Warehouse, s.destination_id) if s.destination_id else None

        sb = await db.execute(
            select(func.coalesce(func.sum(ShipmentBatch.quantity), 0))
            .where(ShipmentBatch.shipment_id == s.id, ShipmentBatch.item_id == item_id)
        )
        item_qty = sb.scalar() or 0

        last_event = await db.execute(
            select(ShipmentTrackingEvent).where(
                ShipmentTrackingEvent.shipment_id == s.id
            )
            .order_by(ShipmentTrackingEvent.event_timestamp.desc()).limit(1)
        )
        le = last_event.scalar_one_or_none()

        tracking_list.append({
            "shipment_number": s.shipment_number,
            "status": s.status.value if hasattr(s.status, 'value') else str(s.status),
            "carrier_name": s.carrier_name,
            "origin": origin.name if origin else None,
            "destination": dest.name if dest else None,
            "item_quantity": item_qty,
            "estimated_arrival": str(s.estimated_arrival) if s.estimated_arrival else None,
            "last_event": le.message if le else None,
            "last_event_timestamp": str(le.event_timestamp) if le and le.event_timestamp else None,
        })

    return {
        "item_id": item_id,
        "item_name": item.common_name,
        "in_transit_count": len(tracking_list),
        "tracking": tracking_list,
    }


async def get_item_transit_summary(db: AsyncSession, item_id: int):
    item = await db.get(TaxonomyItem, item_id)
    if not item:
        return None

    in_transit = await db.execute(
        select(func.coalesce(func.sum(ShipmentBatch.quantity), 0))
        .select_from(ShipmentBatch)
        .join(Shipment, ShipmentBatch.shipment_id == Shipment.id)
        .where(
            ShipmentBatch.item_id == item_id,
            Shipment.status.in_(["picked_up", "in_transit", "at_ferry", "on_ferry",
                                  "arrived_port", "out_for_delivery"]),
        )
    )

    delivered = await db.execute(
        select(func.coalesce(func.sum(ShipmentBatch.quantity), 0))
        .select_from(ShipmentBatch)
        .join(Shipment, ShipmentBatch.shipment_id == Shipment.id)
        .where(
            ShipmentBatch.item_id == item_id,
            Shipment.status == "delivered",
        )
    )

    delayed = await db.execute(
        select(func.count(Shipment.id.distinct()))
        .select_from(ShipmentBatch)
        .join(Shipment, ShipmentBatch.shipment_id == Shipment.id)
        .where(
            ShipmentBatch.item_id == item_id,
            Shipment.status == "exception",
        )
    )

    return {
        "item_id": item_id,
        "item_name": item.common_name,
        "in_transit_quantity": in_transit.scalar() or 0,
        "delivered_quantity": delivered.scalar() or 0,
        "delayed_shipments": delayed.scalar() or 0,
    }


async def predict_item_eta(db: AsyncSession, item_id: int, destination_id: int):
    item = await db.get(TaxonomyItem, item_id)
    if not item:
        return None

    historical = await db.execute(
        select(Shipment).distinct().join(ShipmentBatch).where(
            ShipmentBatch.item_id == item_id,
            Shipment.destination_id == destination_id,
            Shipment.actual_arrival.isnot(None),
            Shipment.estimated_departure.isnot(None),
        )
        .order_by(Shipment.actual_arrival.desc()).limit(20)
    )

    durations = []
    for s in historical.scalars().all():
        if s.estimated_departure and s.actual_arrival:
            delta = (s.actual_arrival - s.estimated_departure).total_seconds() / 3600
            if delta > 0:
                durations.append(delta)

    if not durations:
        return {
            "item_id": item_id,
            "item_name": item.common_name,
            "destination_id": destination_id,
            "predicted_hours": None,
            "confidence": "low",
            "note": "Insufficient historical data for prediction",
        }

    avg_duration = sum(durations) / len(durations)
    variance = sum((d - avg_duration) ** 2 for d in durations) / len(durations)
    std_dev = variance ** 0.5

    if len(durations) >= 10:
        confidence = "high"
    elif len(durations) >= 3:
        confidence = "medium"
    else:
        confidence = "low"

    return {
        "item_id": item_id,
        "item_name": item.common_name,
        "destination_id": destination_id,
        "predicted_hours": round(avg_duration, 1),
        "predicted_days": round(avg_duration / 24, 1),
        "std_dev_hours": round(std_dev, 1),
        "confidence": confidence,
        "sample_size": len(durations),
    }
