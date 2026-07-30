from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.services.gov_integration_service import (
    check_dubai_trade_requirements,
    check_moccae_requirements,
    check_dubai_municipality_requirements,
    check_esma_standards,
    get_comprehensive_compliance,
)
from app.utils.dependencies import get_current_user

router = APIRouter(prefix="/gov", tags=["government"])


@router.get("/dubai-trade")
async def api_dubai_trade(
    hs_code: str = Query(..., description="HS Code for the cargo"),
    user: User = Depends(get_current_user),
):
    try:
        return await check_dubai_trade_requirements({"hs_code": hs_code})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/moccae")
async def api_moccae(
    item_name: str = Query(..., description="Food item name"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await check_moccae_requirements(item_name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dubai-municipality")
async def api_dubai_municipality(
    item_name: str = Query(...),
    user: User = Depends(get_current_user),
):
    try:
        return await check_dubai_municipality_requirements(item_name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/esma")
async def api_esma(
    item_name: str = Query(...),
    user: User = Depends(get_current_user),
):
    try:
        return await check_esma_standards(item_name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/comprehensive-compliance")
async def api_comprehensive(
    item_name: str = Query(...),
    hs_code: str | None = Query(None),
    user: User = Depends(get_current_user),
):
    try:
        return await get_comprehensive_compliance(item_name, hs_code)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
