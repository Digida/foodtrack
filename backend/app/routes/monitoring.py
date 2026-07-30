from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User, UserRole
from app.schemas import HealthResponse, MetricsResponse, SLAResponse
from app.services.monitoring_service import get_health, get_metrics, get_sla
from app.utils.dependencies import get_current_user

router = APIRouter(tags=["monitoring"])


@router.get("/health", response_model=HealthResponse)
async def api_health(db: AsyncSession = Depends(get_db)):
    """Public health check — returns DB connectivity status."""
    return await get_health(db)


@router.get("/metrics", response_model=MetricsResponse)
async def api_metrics(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Internal metrics — requires admin or enterprise role."""
    if user.role not in (UserRole.ADMIN, UserRole.ENTERPRISE):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    return await get_metrics(db)


@router.get("/sla", response_model=SLAResponse)
async def api_sla(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """SLA dashboard — requires admin or enterprise role."""
    if user.role not in (UserRole.ADMIN, UserRole.ENTERPRISE):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    return await get_sla(db)
