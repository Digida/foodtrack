from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
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


@router.post("/policies")
async def api_create_policy(
    item_id: int = Query(...),
    policy_number: str = Query(...),
    coverage_amount: float = Query(...),
    carrier: str | None = Query(None),
    premium: float | None = Query(None),
    currency: str = Query("USD"),
    valid_from: str | None = Query(None),
    valid_until: str | None = Query(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        policy = await create_policy(db, user, item_id, policy_number, coverage_amount, carrier, premium, currency, datetime.fromisoformat(valid_from) if valid_from else None, datetime.fromisoformat(valid_until) if valid_until else None)
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
    policy_id: int = Query(...),
    incident_type: str = Query(...),
    claim_amount: float = Query(...),
    description: str | None = Query(None),
    currency: str = Query("USD"),
    documents: str | None = Query(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        doc_list = documents.split(",") if documents else None
        claim = await file_claim(db, user, policy_id, incident_type, claim_amount, description, currency, doc_list)
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
    status: str = Query(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        claim = await update_claim_status(db, user, claim_id, ClaimStatus(status))
        return {"id": claim.id, "status": claim.status.value}
    except (ValueError, PermissionError) as e:
        raise HTTPException(status_code=400 if isinstance(e, ValueError) else 403, detail=str(e))
