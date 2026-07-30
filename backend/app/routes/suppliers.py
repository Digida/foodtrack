from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.services.supplier_service import (
    create_supplier,
    get_supplier_detail,
    list_suppliers,
    create_scorecard,
    get_supplier_ranking,
)
from app.utils.dependencies import get_current_user

router = APIRouter(prefix="/suppliers", tags=["suppliers"])


@router.post("")
async def api_create_supplier(
    name: str = Query(...),
    contact_name: str | None = Query(None),
    contact_email: str | None = Query(None),
    contact_phone: str | None = Query(None),
    address: str | None = Query(None),
    regions: str | None = Query(None),
    certifications: str | None = Query(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        supplier = await create_supplier(db, user, name, contact_name, contact_email, contact_phone, address, regions, certifications)
        return {"id": supplier.id, "name": supplier.name}
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.get("")
async def api_list_suppliers(
    page: int = Query(1, ge=1),
    db: AsyncSession = Depends(get_db),
):
    return await list_suppliers(db, page)


@router.get("/{supplier_id}")
async def api_get_supplier(
    supplier_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await get_supplier_detail(db, supplier_id)
    if not result:
        raise HTTPException(status_code=404, detail="Supplier not found")
    return result


@router.post("/{supplier_id}/scorecards")
async def api_create_scorecard(
    supplier_id: int,
    period: str = Query(...),
    on_time_delivery_pct: float | None = Query(None),
    quality_score: float | None = Query(None),
    cert_compliance_pct: float | None = Query(None),
    audit_result: str | None = Query(None),
    notes: str | None = Query(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        sc = await create_scorecard(db, user, supplier_id, period, on_time_delivery_pct, quality_score, cert_compliance_pct, audit_result, notes)
        return {"id": sc.id, "overall_score": sc.overall_score}
    except (ValueError, PermissionError) as e:
        raise HTTPException(status_code=400 if isinstance(e, ValueError) else 403, detail=str(e))


@router.get("/ranking/top")
async def api_supplier_ranking(
    db: AsyncSession = Depends(get_db),
):
    return await get_supplier_ranking(db)
