from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.services.item_enrichment_service import (
    enrich_from_web,
    suggest_item_classification,
    detect_anomalies,
)
from app.utils.dependencies import get_current_user

router = APIRouter(prefix="/enrichment", tags=["enrichment"])


@router.post("/items/{item_id}/enrich")
async def api_enrich_item(
    item_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await enrich_from_web(db, user, item_id)
        return result
    except (PermissionError, ValueError) as e:
        raise HTTPException(status_code=403 if isinstance(e, PermissionError) else 400, detail=str(e))


@router.get("/suggest-classification")
async def api_suggest_classification(
    name: str = Query(..., description="Item name to classify"),
    db: AsyncSession = Depends(get_db),
):
    return await suggest_item_classification(db, name)


@router.get("/items/{item_id}/anomalies")
async def api_detect_anomalies(
    item_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await detect_anomalies(db, user, item_id)
    except (PermissionError, ValueError) as e:
        raise HTTPException(status_code=403 if isinstance(e, PermissionError) else 400, detail=str(e))
