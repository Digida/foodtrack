from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.monitoring_service import get_health, get_metrics, get_sla

router = APIRouter(tags=["monitoring"])


@router.get("/health")
async def api_health(
    db: AsyncSession = Depends(get_db),
):
    return await get_health(db)


@router.get("/metrics")
async def api_metrics(
    db: AsyncSession = Depends(get_db),
):
    return await get_metrics(db)


@router.get("/sla")
async def api_sla(
    db: AsyncSession = Depends(get_db),
):
    return await get_sla(db)
