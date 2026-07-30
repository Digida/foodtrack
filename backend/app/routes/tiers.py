from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.tenant import Tenant
from app.models.user import User, UserRole
from app.utils.dependencies import get_current_user

router = APIRouter(prefix="/tiers", tags=["tiers"])

TIER_FEATURES = {
    "free": {"max_items": 10, "max_users": 3, "features": ["view_only", "basic_tracking"]},
    "growth": {"max_items": 1000, "max_users": 25, "features": ["view_only", "basic_tracking", "certificates", "analytics"]},
    "enterprise": {"max_items": None, "max_users": None, "features": ["view_only", "basic_tracking", "certificates", "analytics", "ai_enrichment", "telemetry", "webhooks", "recalls", "suppliers", "insurance"]},
    "government": {"max_items": None, "max_users": None, "features": ["view_only", "basic_tracking", "certificates", "analytics", "ai_enrichment", "telemetry", "webhooks", "recalls", "suppliers", "insurance", "compliance", "gov_integration"]},
}


@router.get("")
async def api_list_tiers():
    return {"tiers": TIER_FEATURES}


@router.get("/tenant")
async def api_tenant_tier(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant = None
    if user.tenant_id:
        tenant = await db.get(Tenant, user.tenant_id)
    current_tier = tenant.tier if tenant else "free"
    features = TIER_FEATURES.get(current_tier, TIER_FEATURES["free"])
    return {"tenant_id": user.tenant_id, "tier": current_tier, "features": features}


@router.patch("/tenant")
async def api_update_tenant_tier(
    tier: str = Query(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    if tier not in TIER_FEATURES:
        raise HTTPException(status_code=400, detail=f"Invalid tier: {tier}")

    if not user.tenant_id:
        raise HTTPException(status_code=400, detail="User has no tenant")

    tenant = await db.get(Tenant, user.tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    tenant.tier = tier
    await db.commit()
    return {"tenant_id": tenant.id, "tier": tier}


def require_tier(minimum_tier: str):
    tier_order = ["free", "growth", "enterprise", "government"]
    min_idx = tier_order.index(minimum_tier)

    async def _check(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> bool:
        if user.role == UserRole.ADMIN:
            return True
        if not user.tenant_id:
            raise HTTPException(status_code=403, detail="No tenant assigned")
        tenant = await db.get(Tenant, user.tenant_id)
        current_tier = tenant.tier if tenant and tenant.tier else "free"
        current_idx = tier_order.index(current_tier) if current_tier in tier_order else 0
        if current_idx < min_idx:
            raise HTTPException(status_code=403, detail=f"Requires {minimum_tier} tier or above")
        return True

    return _check
