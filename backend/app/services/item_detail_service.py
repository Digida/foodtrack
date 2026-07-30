from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.taxonomy import TaxonomyItem, TaxonomyNode, ItemName, ItemAttribute
from app.models.product import Product
from app.models.tracking import Batch, WarehouseItem, ShipmentBatch, Shipment
from app.models.certificate import Certificate
from app.models.traceability import TraceabilityEvent
from app.models.inventory import ItemInventory
from app.models.user import User


async def get_item_detail(db: AsyncSession, item_id: int) -> dict | None:
    item = await db.get(TaxonomyItem, item_id)
    if not item:
        return None

    node = await db.get(TaxonomyNode, item.node_id) if item.node_id else None

    names = await db.execute(
        select(ItemName).where(ItemName.item_id == item_id)
    )
    names_list = [{"id": n.id, "language": n.language, "name": n.name, "is_primary": n.is_primary}
                  for n in names.scalars().all()]

    attrs = await db.execute(
        select(ItemAttribute).where(ItemAttribute.item_id == item_id)
    )
    attrs_list = [{"id": a.id, "key": a.key, "value": a.value, "unit": a.unit}
                  for a in attrs.scalars().all()]

    products = await db.execute(
        select(Product).where(Product.item_id == item_id, Product.is_active == True)
    )
    products_list = [{"id": p.id, "sku": p.sku, "name": p.name, "producer_name": p.producer_name}
                     for p in products.scalars().all()]

    certificates = await db.execute(
        select(Certificate).where(Certificate.item_id == item_id)
        .order_by(Certificate.issued_date.desc()).limit(10)
    )
    certs_list = [{"id": c.id, "certificate_id": c.certificate_id,
                   "type": c.type.value if hasattr(c.type, 'value') else str(c.type),
                   "status": c.status.value if hasattr(c.status, 'value') else str(c.status),
                   "issuer_name": c.issuer_name, "issued_date": str(c.issued_date) if c.issued_date else None,
                   "expiry_date": str(c.expiry_date) if c.expiry_date else None}
                  for c in certificates.scalars().all()]

    storage = await db.execute(
        select(ItemInventory).where(
            ItemInventory.item_id == item_id,
            ItemInventory.total_quantity > 0,
        )
    )
    storage_list = []
    total_stock = 0
    for inv in storage.scalars().all():
        storage_list.append({
            "warehouse_id": inv.warehouse_id,
            "total_quantity": inv.total_quantity,
            "available_quantity": inv.available_quantity,
        })
        total_stock += inv.total_quantity

    in_transit = await db.execute(
        select(func.coalesce(func.sum(ShipmentBatch.quantity), 0))
        .select_from(ShipmentBatch)
        .join(Shipment, ShipmentBatch.shipment_id == Shipment.id)
        .where(
            ShipmentBatch.item_id == item_id,
            Shipment.status.in_(["in_transit", "picked_up", "out_for_delivery"]),
        )
    )
    in_transit_qty = in_transit.scalar() or 0

    trace_events = await db.execute(
        select(TraceabilityEvent).where(TraceabilityEvent.item_id == item_id)
        .order_by(TraceabilityEvent.event_timestamp.desc()).limit(10)
    )
    trace_list = [{"id": e.id, "event_type": e.event_type.value if hasattr(e.event_type, 'value') else str(e.event_type),
                   "location_name": e.location_name, "country": e.country,
                   "handler_name": e.handler_name, "temperature_celsius": e.temperature_celsius,
                   "event_timestamp": str(e.event_timestamp) if e.event_timestamp else None}
                  for e in trace_events.scalars().all()]

    return {
        "id": item.id,
        "code": item.code,
        "common_name": item.common_name,
        "scientific_name": item.scientific_name,
        "genre": item.genre,
        "phylum": item.phylum,
        "tax_class": item.tax_class,
        "order_name": item.order_name,
        "family": item.family,
        "gestation_period": item.gestation_period,
        "gestation_unit": item.gestation_unit,
        "local_uses": item.local_uses,
        "description": item.description,
        "image_url": item.image_url,
        "is_active": item.is_active,
        "category": {"id": node.id, "name": node.name, "code": node.code} if node else None,
        "names": names_list,
        "attributes": attrs_list,
        "products": products_list,
        "certificates": certs_list,
        "storage": {
            "total_quantity": total_stock,
            "in_transit_quantity": in_transit_qty,
            "warehouses": storage_list,
        },
        "traceability_events": trace_list,
        "created_at": str(item.created_at) if item.created_at else None,
    }


async def get_item_timeline(db: AsyncSession, item_id: int) -> list:
    events = []

    certs = await db.execute(
        select(Certificate).where(Certificate.item_id == item_id)
        .order_by(Certificate.issued_date.asc())
    )
    for c in certs.scalars().all():
        events.append({
            "timestamp": str(c.issued_date) if c.issued_date else None,
            "type": "certificate_issued",
            "title": f"Certificate: {c.type.value if hasattr(c.type, 'value') else c.type}",
            "subtitle": c.issuer_name,
            "status": c.status.value if hasattr(c.status, 'value') else str(c.status),
            "reference_id": c.id,
        })

    traces = await db.execute(
        select(TraceabilityEvent).where(TraceabilityEvent.item_id == item_id)
        .order_by(TraceabilityEvent.event_timestamp.asc())
    )
    for t in traces.scalars().all():
        events.append({
            "timestamp": str(t.event_timestamp) if t.event_timestamp else None,
            "type": "traceability",
            "title": f"{t.event_type.value if hasattr(t.event_type, 'value') else t.event_type}",
            "subtitle": f"{t.location_name or ''} — {t.handler_name}",
            "temperature_celsius": t.temperature_celsius,
            "reference_id": t.id,
        })

    movements = await db.execute(
        select(ShipmentBatch, Shipment).join(Shipment, ShipmentBatch.shipment_id == Shipment.id)
        .where(ShipmentBatch.item_id == item_id)
        .order_by(Shipment.created_at.asc())
    )
    for sb, s in movements.all():
        events.append({
            "timestamp": str(s.created_at) if s.created_at else None,
            "type": "shipment",
            "title": f"Shipment: {s.shipment_number} ({s.mode.value if hasattr(s.mode, 'value') else s.mode})",
            "subtitle": f"{s.carrier_name or ''} — {s.status.value if hasattr(s.status, 'value') else s.status}",
            "quantity": sb.quantity,
            "reference_id": s.id,
        })

    inv_movements = await db.execute(
        select(ItemInventory).where(
            ItemInventory.item_id == item_id,
            ItemInventory.total_quantity > 0,
        )
    )
    for inv in inv_movements.scalars().all():
        events.append({
            "timestamp": str(inv.last_stocked_at) if inv.last_stocked_at else None,
            "type": "inventory",
            "title": f"Stock at warehouse {inv.warehouse_id}",
            "subtitle": f"{inv.total_quantity} units ({inv.available_quantity} available)",
            "reference_id": inv.id,
        })

    events.sort(key=lambda e: e.get("timestamp") or "")
    return events


async def get_item_provenance(db: AsyncSession, item_id: int) -> dict | None:
    item = await db.get(TaxonomyItem, item_id)
    if not item:
        return None

    origins = await db.execute(
        select(TraceabilityEvent).where(
            TraceabilityEvent.item_id == item_id,
            TraceabilityEvent.event_type.in_(["harvest", "import_clearance"]),
        )
        .order_by(TraceabilityEvent.event_timestamp.asc())
    )
    origin_events = [{
        "event_type": e.event_type.value if hasattr(e.event_type, 'value') else str(e.event_type),
        "country": e.country, "city": e.city, "location_name": e.location_name,
        "handler_name": e.handler_name, "handler_organization": e.handler_organization,
        "event_timestamp": str(e.event_timestamp) if e.event_timestamp else None,
    } for e in origins.scalars().all()]

    products = await db.execute(
        select(Product).where(Product.item_id == item_id, Product.is_active == True)
    )
    producers = list(set(
        (p.producer_name, p.origin_country, p.origin_region)
        for p in products.scalars().all() if p.producer_name
    ))

    return {
        "item_id": item_id,
        "item_name": item.common_name,
        "origin_events": origin_events,
        "producers": [{"name": p[0], "country": p[1], "region": p[2]} for p in producers],
        "producer_count": len(producers),
    }
