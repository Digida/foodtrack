from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.monitoring_service import get_health

router = APIRouter(tags=["health"])


@router.get("/api/v1/health")
async def api_health(db: AsyncSession = Depends(get_db)):
    return await get_health(db)
