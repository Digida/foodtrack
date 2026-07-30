from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.services.code_service import (
    generate_item_qr, generate_item_barcode, register_nfc_tag, resolve_scan,
)
from app.utils.dependencies import get_current_user

router = APIRouter(tags=["codes"])


@router.post("/api/v1/items/{item_id}/generate-qr")
async def api_generate_item_qr(
    item_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await generate_item_qr(db, item_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/api/v1/items/{item_id}/generate-barcode")
async def api_generate_item_barcode(
    item_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await generate_item_barcode(db, item_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/api/v1/items/{item_id}/register-nfc")
async def api_register_nfc_tag(
    item_id: int,
    nfc_uid: str = Query(..., description="NFC tag UID to register"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await register_nfc_tag(db, item_id, nfc_uid, user.id)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("/api/v1/scan/{code:path}")
async def api_resolve_scan(
    code: str,
    db: AsyncSession = Depends(get_db),
):
    result = await resolve_scan(db, code)
    return result
