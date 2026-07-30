from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.cargo import CargoStatus
from app.services.cargo_service import (
    register_cargo, get_cargo_detail, list_cargo_for_item,
    update_cargo_status, get_cargo_certification_status,
)
from app.utils.dependencies import get_current_user

router = APIRouter(prefix="/cargo", tags=["cargo"])


class CargoRegisterRequest(BaseModel):
    item_id: int
    quantity: int
    unit: str | None = None
    origin_location: str | None = None
    destination_location: str | None = None
    mode: str | None = None
    carrier_name: str | None = None
    carrier_ref: str | None = None
    tracking_number: str | None = None
    estimated_departure: datetime | None = None
    estimated_arrival: datetime | None = None
    weight_kg: float | None = None
    volume_m3: float | None = None
    notes: str | None = None


class CargoStatusUpdate(BaseModel):
    status: CargoStatus


@router.post("/register")
async def api_register_cargo(
    req: CargoRegisterRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        cargo = await register_cargo(
            db, user, req.item_id, req.quantity,
            origin_location=req.origin_location,
            destination_location=req.destination_location,
            mode=req.mode, unit=req.unit,
            carrier_name=req.carrier_name, carrier_ref=req.carrier_ref,
            tracking_number=req.tracking_number,
            estimated_departure=req.estimated_departure,
            estimated_arrival=req.estimated_arrival,
            weight_kg=req.weight_kg, volume_m3=req.volume_m3,
            notes=req.notes,
        )
        return {"id": cargo.id, "status": cargo.status.value}
    except (ValueError, PermissionError) as e:
        raise HTTPException(status_code=400 if isinstance(e, ValueError) else 403, detail=str(e))


@router.get("/{cargo_id}")
async def api_get_cargo(
    cargo_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await get_cargo_detail(db, cargo_id)
    if not result:
        raise HTTPException(status_code=404, detail="Cargo not found")
    return result


@router.get("/by-item/{item_id}")
async def api_cargo_by_item(
    item_id: int,
    page: int = Query(1, ge=1),
    db: AsyncSession = Depends(get_db),
):
    return await list_cargo_for_item(db, item_id, page)


@router.patch("/{cargo_id}/status")
async def api_update_cargo_status(
    cargo_id: int,
    req: CargoStatusUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        cargo = await update_cargo_status(db, user, cargo_id, req.status)
        return {"id": cargo.id, "status": cargo.status.value}
    except (ValueError, PermissionError) as e:
        raise HTTPException(status_code=400 if isinstance(e, ValueError) else 403, detail=str(e))


@router.get("/{cargo_id}/certification-status")
async def api_cargo_certification_status(
    cargo_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await get_cargo_certification_status(db, cargo_id)
    if not result:
        raise HTTPException(status_code=404, detail="Cargo not found")
    return result
