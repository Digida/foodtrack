from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.services.rate_service import get_rates_for_item, calculate_shipping_cost, compare_rates
from app.utils.dependencies import get_current_user

router = APIRouter(prefix="/rates", tags=["rates"])


@router.get("/items/{item_id}")
async def api_get_rates(
    item_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await get_rates_for_item(db, item_id)
    if not result:
        raise HTTPException(status_code=404, detail="Item not found")
    return result


@router.get("/items/{item_id}/cost")
async def api_calculate_cost(
    item_id: int,
    origin: str = Query(..., description="Origin region"),
    destination: str = Query(..., description="Destination region"),
    weight: float = Query(..., gt=0, description="Weight in kg"),
    mode: str | None = Query(None, description="Mode filter (courier, ferry, truck, air, rail)"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await calculate_shipping_cost(db, item_id, origin, destination, weight, mode)
    if not result:
        raise HTTPException(status_code=404, detail="Item not found")
    return result


@router.get("/items/{item_id}/compare")
async def api_compare_rates(
    item_id: int,
    origin: str = Query(..., description="Origin region"),
    destination: str = Query(..., description="Destination region"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await compare_rates(db, item_id, origin, destination)
    if not result:
        raise HTTPException(status_code=404, detail="Item not found")
    return result
