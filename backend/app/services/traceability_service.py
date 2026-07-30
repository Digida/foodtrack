"""Traceability service: supply chain event chain, timeline, scanner integration."""

import uuid
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.traceability import TraceabilityEvent, EventType
from app.models.product import Product
from app.models.user import User, UserRole


async def create_trace_event(db: AsyncSession, user: User, product_id: int, event_type: EventType,
                              location_name: str | None = None, country: str | None = None,
                              city: str | None = None, handler_name: str | None = None,
                              handler_organization: str | None = None,
                              temperature_celsius: float | None = None,
                              humidity_percent: float | None = None,
                              notes: str | None = None,
                              event_timestamp: str | None = None,
                              location_lat: float | None = None,
                              location_lng: float | None = None) -> TraceabilityEvent:
    if user.role == UserRole.VIEWER:
        raise PermissionError("Insufficient permissions")
    prod_result = await db.execute(select(Product).where(Product.id == product_id))
    product = prod_result.scalar_one_or_none()
    if not product:
        raise ValueError("Product not found")
    timestamp = None
    if event_timestamp:
        timestamp = datetime.fromisoformat(event_timestamp.replace("Z", "+00:00"))
    else:
        timestamp = datetime.now(timezone.utc)
    event = TraceabilityEvent(
        event_id=f"evt-{uuid.uuid4().hex[:12]}",
        product_id=product_id, event_type=event_type,
        location_name=location_name, location_lat=location_lat, location_lng=location_lng,
        country=country, city=city,
        handler_id=user.id, handler_name=handler_name or user.full_name,
        handler_organization=handler_organization or user.company,
        temperature_celsius=temperature_celsius, humidity_percent=humidity_percent,
        notes=notes, event_timestamp=timestamp,
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return event


async def get_product_trace(db: AsyncSession, product_id: int) -> list[TraceabilityEvent]:
    result = await db.execute(
        select(TraceabilityEvent)
        .where(TraceabilityEvent.product_id == product_id)
        .order_by(TraceabilityEvent.event_timestamp.asc())
    )
    return list(result.scalars().all())


async def scan_trace(db: AsyncSession, query: str) -> dict | None:
    import json as j
    sku = query
    try:
        decoded = j.loads(query)
        sku = decoded.get("sku", query)
    except (j.JSONDecodeError, TypeError):
        pass
    result = await db.execute(select(Product).where(Product.sku == sku))
    product = result.scalar_one_or_none()
    if not product:
        return None
    events = await get_product_trace(db, product.id)
    return {
        "product": {"id": product.id, "sku": product.sku, "name": product.name,
                    "producer_name": product.producer_name},
        "events": [{"event_type": e.event_type.value, "location_name": e.location_name,
                    "country": e.country, "handler_name": e.handler_name,
                    "handler_organization": e.handler_organization,
                    "temperature_celsius": e.temperature_celsius,
                    "humidity_percent": e.humidity_percent,
                    "event_timestamp": str(e.event_timestamp)}
                   for e in events],
    }


def serialize_event(event: TraceabilityEvent) -> dict:
    return {
        "event_id": event.event_id, "event_type": event.event_type.value,
        "location_name": event.location_name, "country": event.country,
        "city": event.city, "handler_name": event.handler_name,
        "handler_organization": event.handler_organization,
        "temperature_celsius": event.temperature_celsius,
        "humidity_percent": event.humidity_percent,
        "notes": event.notes, "event_timestamp": str(event.event_timestamp),
    }
