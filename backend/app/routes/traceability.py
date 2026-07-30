from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.database import get_db
from app.models.user import User
from app.models.traceability import EventType
from app.services.traceability_service import (
    create_trace_event, get_product_trace, scan_trace, serialize_event,
)
from app.utils.dependencies import get_current_user

router = APIRouter(prefix="/traceability", tags=["traceability"])


class TraceEventCreateRequest(BaseModel):
    product_id: int
    event_type: EventType
    location_name: str | None = None
    location_lat: float | None = None
    location_lng: float | None = None
    country: str | None = None
    city: str | None = None
    handler_name: str | None = None
    handler_organization: str | None = None
    temperature_celsius: float | None = None
    humidity_percent: float | None = None
    notes: str | None = None
    event_timestamp: str | None = None


@router.post("")
async def api_create_event(req: TraceEventCreateRequest, user: User = Depends(get_current_user),
                            db: AsyncSession = Depends(get_db)):
    try:
        event = await create_trace_event(
            db, user, req.product_id, req.event_type, req.location_name,
            req.country, req.city, req.handler_name, req.handler_organization,
            req.temperature_celsius, req.humidity_percent, req.notes,
            req.event_timestamp, req.location_lat, req.location_lng,
        )
        return {"event": serialize_event(event)}
    except (ValueError, PermissionError) as e:
        raise HTTPException(status_code=404 if isinstance(e, ValueError) else 403, detail=str(e))


@router.get("/product/{product_id}")
async def api_get_product_trace(product_id: int, user: User = Depends(get_current_user),
                                 db: AsyncSession = Depends(get_db)):
    events = await get_product_trace(db, product_id)
    return {"product_id": product_id, "events": [serialize_event(e) for e in events]}


@router.get("/scan/{query:path}")
async def api_scan_trace(query: str, db: AsyncSession = Depends(get_db)):
    result = await scan_trace(db, query)
    if not result:
        raise HTTPException(status_code=404, detail="Product not found")
    return result
