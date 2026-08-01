from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.services.analytics_service import (
    get_dashboard_stats, get_products_by_category,
    get_events_by_type, get_certificates_by_status,
    get_top_moved_items, get_top_stored_items,
    get_item_delay_rates, get_low_stock_items,
    get_certification_gaps,
)
from app.utils.dependencies import get_current_user

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/dashboard")
async def api_dashboard(user: User = Depends(get_current_user),
                        db: AsyncSession = Depends(get_db)):
    return await get_dashboard_stats(db)


@router.get("/products-by-category")
async def api_products_by_category(user: User = Depends(get_current_user),
                                   db: AsyncSession = Depends(get_db)):
    return {"categories": await get_products_by_category(db)}


@router.get("/events-by-type")
async def api_events_by_type(user: User = Depends(get_current_user),
                             db: AsyncSession = Depends(get_db)):
    return {"event_types": await get_events_by_type(db)}


@router.get("/certificates-by-status")
async def api_certificates_by_status(user: User = Depends(get_current_user),
                                     db: AsyncSession = Depends(get_db)):
    return {"statuses": await get_certificates_by_status(db)}


@router.get("/items/top-moved")
async def api_top_moved_items(
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return {"items": await get_top_moved_items(db, limit)}


@router.get("/items/top-stored")
async def api_top_stored_items(
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return {"items": await get_top_stored_items(db, limit)}


@router.get("/items/delay-rates")
async def api_item_delay_rates(
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return {"items": await get_item_delay_rates(db, limit)}


@router.get("/items/low-stock")
async def api_low_stock_items(
    threshold: int = Query(50, ge=1),
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return {"items": await get_low_stock_items(db, threshold, limit)}


@router.get("/items/certification-gaps")
async def api_certification_gaps(
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return {"items": await get_certification_gaps(db, limit)}
