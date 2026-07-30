from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.services.batch_service import (
    list_batches, get_batch, create_batch, update_batch, delete_batch,
)
from app.utils.dependencies import get_current_user

router = APIRouter(prefix="/batches", tags=["batches"])


class BatchCreate(BaseModel):
    batch_number: str
    product_id: int
    quantity: int = 0
    serial_number: str | None = None
    manufacturer_part_number: str | None = None
    production_date: str | None = None
    expiry_date: str | None = None
    notes: str | None = None


class BatchUpdate(BaseModel):
    quantity: int | None = None
    status: str | None = None
    serial_number: str | None = None
    manufacturer_part_number: str | None = None
    production_date: str | None = None
    expiry_date: str | None = None
    notes: str | None = None


@router.get("")
async def api_list_batches(
    page: int = Query(1, ge=1),
    status: str | None = None,
    product_id: int | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await list_batches(db, page, status, product_id)


@router.get("/{batch_id}")
async def api_get_batch(
    batch_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    b = await get_batch(db, batch_id)
    if not b:
        raise HTTPException(status_code=404, detail="Batch not found")
    return b


@router.post("")
async def api_create_batch(
    req: BatchCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        b = await create_batch(
            db, user, req.batch_number, req.product_id, req.quantity,
            req.serial_number, req.manufacturer_part_number,
            req.production_date, req.expiry_date, req.notes,
        )
        return await get_batch(db, b.id)
    except (ValueError, PermissionError) as e:
        raise HTTPException(status_code=400 if isinstance(e, ValueError) else 403, detail=str(e))


@router.put("/{batch_id}")
async def api_update_batch(
    batch_id: int, req: BatchUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        b = await update_batch(db, user, batch_id, req.model_dump(exclude_unset=True))
        return await get_batch(db, b.id)
    except (ValueError, PermissionError) as e:
        raise HTTPException(status_code=404 if isinstance(e, ValueError) else 403, detail=str(e))


@router.delete("/{batch_id}")
async def api_delete_batch(
    batch_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        await delete_batch(db, user, batch_id)
        return {"deleted": True}
    except (ValueError, PermissionError) as e:
        raise HTTPException(status_code=404 if isinstance(e, ValueError) else 403, detail=str(e))
