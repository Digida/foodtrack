from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.insurance import ClaimStatus
from app.services.insurance_service import (
    create_policy,
    list_policies,
    file_claim,
    list_claims,
    update_claim_status,
)
from app.utils.dependencies import get_current_user

router = APIRouter(prefix="/insurance", tags=["insurance"])


class PolicyCreateRequest(BaseModel):
    item_id: int
    policy_number: str = Field(..., min_length=1, max_length=100)
    coverage_amount: float = Field(..., gt=0)
    carrier: str | None = None
    premium: float | None = Field(None, gt=0)
    currency: str = Field("USD", min_length=3, max_length=3)
    valid_from: str | None = None
    valid_until: str | None = None


class ClaimFileRequest(BaseModel):
    policy_id: int
    incident_type: str = Field(..., min_length=1, max_length=100)
    claim_amount: float = Field(..., gt=0)
    description: str | None = None
    currency: str = Field("USD", min_length=3, max_length=3)
    documents: list[str] | None = None


class ClaimStatusUpdateRequest(BaseModel):
    status: ClaimStatus


@router.post("/policies")
async def api_create_policy(
    req: PolicyCreateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        policy = await create_policy(
            db, user, req.item_id, req.policy_number, req.coverage_amount,
            req.carrier, req.premium, req.currency,
            datetime.fromisoformat(req.valid_from) if req.valid_from else None,
            datetime.fromisoformat(req.valid_until) if req.valid_until else None,
        )
        return {"id": policy.id, "policy_number": policy.policy_number}
    except (ValueError, PermissionError) as e:
        raise HTTPException(status_code=400 if isinstance(e, ValueError) else 403, detail=str(e))


@router.get("/policies")
async def api_list_policies(
    item_id: int | None = Query(None),
    page: int = Query(1, ge=1),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await list_policies(db, page, item_id)


@router.post("/claims")
async def api_file_claim(
    req: ClaimFileRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        claim = await file_claim(
            db, user, req.policy_id, req.incident_type,
            req.claim_amount, req.description, req.currency, req.documents,
        )
        return {"id": claim.id, "status": claim.status.value}
    except (ValueError, PermissionError) as e:
        raise HTTPException(status_code=400 if isinstance(e, ValueError) else 403, detail=str(e))


@router.get("/claims")
async def api_list_claims(
    page: int = Query(1, ge=1),
    status: str | None = Query(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await list_claims(db, page, status)


@router.patch("/claims/{claim_id}/status")
async def api_update_claim(
    claim_id: int,
    req: ClaimStatusUpdateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        claim = await update_claim_status(db, user, claim_id, req.status)
        return {"id": claim.id, "status": claim.status.value}
    except (ValueError, PermissionError) as e:
        raise HTTPException(status_code=400 if isinstance(e, ValueError) else 403, detail=str(e))
