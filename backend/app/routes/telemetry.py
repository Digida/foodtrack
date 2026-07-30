from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.services.telemetry_service import (
    ingest_telemetry,
    list_telemetry,
    list_alerts,
    acknowledge_alert,
)
from app.utils.dependencies import get_current_user

router = APIRouter(prefix="/telemetry", tags=["telemetry"])


class TelemetryIngestRequest(BaseModel):
    device_id: str
    telemetry_type: str
    value: float
    unit: str | None = None
    item_id: int | None = None
    batch_id: int | None = None
    location_lat: float | None = None
    location_lng: float | None = None
    recorded_at: str | None = None


@router.post("/ingest")
async def api_ingest_telemetry(
    req: TelemetryIngestRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rec = await ingest_telemetry(
        db, req.device_id, req.telemetry_type, req.value, req.unit,
        req.item_id, req.batch_id, req.location_lat, req.location_lng,
        recorded_at=datetime.fromisoformat(req.recorded_at) if req.recorded_at else None,
    )
    return {
        "id": rec.id,
        "device_id": rec.device_id,
        "telemetry_type": rec.telemetry_type,
        "value": rec.value_float or rec.value_str,
    }


@router.get("/readings")
async def api_list_telemetry(
    device_id: str | None = Query(None),
    telemetry_type: str | None = Query(None),
    item_id: int | None = Query(None),
    page: int = Query(1, ge=1),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await list_telemetry(db, device_id, telemetry_type, item_id, page)


@router.get("/alerts")
async def api_list_alerts(
    acknowledged: bool | None = Query(None),
    page: int = Query(1, ge=1),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await list_alerts(db, acknowledged, page)


@router.patch("/alerts/{alert_id}/acknowledge")
async def api_acknowledge_alert(
    alert_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        alert = await acknowledge_alert(db, user, alert_id)
        return {"id": alert.id, "acknowledged": True}
    except (ValueError, PermissionError) as e:
        raise HTTPException(status_code=400 if isinstance(e, ValueError) else 403, detail=str(e))
