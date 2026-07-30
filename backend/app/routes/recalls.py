from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.recall import RecallSeverity, RecallStatus
from app.services.recall_service import (
    initiate_recall,
    get_recall_detail,
    update_recall_status,
    trace_recall,
    list_recalls,
)
from app.utils.dependencies import get_current_user

router = APIRouter(prefix="/recalls", tags=["recalls"])


@router.post("")
async def api_initiate_recall(
    batch_id: int = Query(...),
    reason: str = Query(...),
    severity: str = Query("medium"),
    affected_region: str | None = Query(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        recall = await initiate_recall(db, user, batch_id, reason, RecallSeverity(severity), affected_region)
        return {"id": recall.id, "status": recall.status.value}
    except (ValueError, PermissionError) as e:
        raise HTTPException(status_code=400 if isinstance(e, ValueError) else 403, detail=str(e))


@router.get("")
async def api_list_recalls(
    page: int = Query(1, ge=1),
    status: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    return await list_recalls(db, page, status)


@router.get("/{recall_id}")
async def api_get_recall(
    recall_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await get_recall_detail(db, recall_id)
    if not result:
        raise HTTPException(status_code=404, detail="Recall not found")
    return result


@router.patch("/{recall_id}/status")
async def api_update_recall_status(
    recall_id: int,
    status: str = Query(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        recall = await update_recall_status(db, user, recall_id, RecallStatus(status))
        return {"id": recall.id, "status": recall.status.value}
    except (ValueError, PermissionError) as e:
        raise HTTPException(status_code=400 if isinstance(e, ValueError) else 403, detail=str(e))


@router.get("/{recall_id}/trace")
async def api_trace_recall(
    recall_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await trace_recall(db, recall_id)
    if not result:
        raise HTTPException(status_code=404, detail="Recall not found")
    return result
