from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
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


@router.post("/ingest")
async def api_ingest_telemetry(
    device_id: str = Query(...),
    telemetry_type: str = Query(...),
    value: float = Query(...),
    unit: str | None = Query(None),
    item_id: int | None = Query(None),
    batch_id: int | None = Query(None),
    location_lat: float | None = Query(None),
    location_lng: float | None = Query(None),
    recorded_at: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    rec = await ingest_telemetry(
        db, device_id, telemetry_type, value, unit,
        item_id, batch_id, location_lat, location_lng,
        recorded_at=datetime.fromisoformat(recorded_at) if recorded_at else None,
    )
    return {"id": rec.id, "device_id": rec.device_id, "telemetry_type": rec.telemetry_type, "value": rec.value_float or rec.value_str}


@router.get("/readings")
async def api_list_telemetry(
    device_id: str | None = Query(None),
    telemetry_type: str | None = Query(None),
    item_id: int | None = Query(None),
    page: int = Query(1, ge=1),
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
