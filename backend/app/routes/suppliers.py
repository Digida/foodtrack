import re

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, field_validator
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

# Period must match YYYY-QN (e.g. 2024-Q1) or YYYY-MM (e.g. 2024-01)
_PERIOD_RE = re.compile(r"^\d{4}-(Q[1-4]|\d{2})$")


class SupplierCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    contact_name: str | None = None
    contact_email: str | None = None
    contact_phone: str | None = None
    address: str | None = None
    regions: str | None = None
    certifications: str | None = None


class ScorecardCreateRequest(BaseModel):
    period: str = Field(..., description="Format: YYYY-Q1..Q4 or YYYY-MM, e.g. 2024-Q3")
    on_time_delivery_pct: float | None = Field(None, ge=0, le=100)
    quality_score: float | None = Field(None, ge=0, le=100)
    cert_compliance_pct: float | None = Field(None, ge=0, le=100)
    audit_result: str | None = None
    notes: str | None = None

    @field_validator("period")
    @classmethod
    def validate_period(cls, v: str) -> str:
        if not _PERIOD_RE.match(v):
            raise ValueError("period must be in format YYYY-Q1..Q4 (e.g. 2024-Q1) or YYYY-MM (e.g. 2024-01)")
        return v


@router.post("")
async def api_create_supplier(
    req: SupplierCreateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        supplier = await create_supplier(
            db, user, req.name, req.contact_name, req.contact_email,
            req.contact_phone, req.address, req.regions, req.certifications,
        )
        return {"id": supplier.id, "name": supplier.name}
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.get("")
async def api_list_suppliers(
    page: int = Query(1, ge=1),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await list_suppliers(db, page, tenant_id=user.tenant_id)


@router.get("/{supplier_id}")
async def api_get_supplier(
    supplier_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await get_supplier_detail(db, supplier_id)
    if not result:
        raise HTTPException(status_code=404, detail="Supplier not found")
    return result


@router.post("/{supplier_id}/scorecards")
async def api_create_scorecard(
    supplier_id: int,
    req: ScorecardCreateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        sc = await create_scorecard(
            db, user, supplier_id, req.period,
            req.on_time_delivery_pct, req.quality_score,
            req.cert_compliance_pct, req.audit_result, req.notes,
        )
        return {"id": sc.id, "overall_score": sc.overall_score}
    except (ValueError, PermissionError) as e:
        raise HTTPException(status_code=400 if isinstance(e, ValueError) else 403, detail=str(e))


@router.get("/ranking/top")
async def api_supplier_ranking(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_supplier_ranking(db)
