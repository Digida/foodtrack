from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.services.retention_service import create_archive_policy, list_archive_policies, run_archival
from app.utils.dependencies import get_current_user

router = APIRouter(prefix="/retention", tags=["retention"])


@router.post("/policies")
async def api_create_policy(
    entity_type: str = Query(...),
    retention_days: int = Query(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        policy = await create_archive_policy(db, user, entity_type, retention_days)
        return {"id": policy.id, "entity_type": policy.entity_type, "retention_days": policy.retention_days}
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.get("/policies")
async def api_list_policies(
    db: AsyncSession = Depends(get_db),
):
    return {"policies": await list_archive_policies(db)}


@router.post("/run")
async def api_run_archival(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await run_archival(db, user)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
