from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.utils.dependencies import get_current_user, require_admin
from app.services.taxonomy_suggestion_service import (
    create_suggestion, list_suggestions, list_my_suggestions,
    accept_suggestion, reject_suggestion, serialize_suggestion,
)

router = APIRouter(prefix="/taxonomy/suggestions", tags=["taxonomy"])


class SuggestionCreate(BaseModel):
    kind: str
    item_id: int | None = None
    node_id: int | None = None
    language: str | None = None
    key: str | None = None
    value: str
    unit: str | None = None


@router.post("")
async def api_create_suggestion(
    req: SuggestionCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Authed faucet — any logged-in user can propose taxonomy info."""
    try:
        s = await create_suggestion(
            db, user,
            kind=req.kind, value=req.value,
            item_id=req.item_id, node_id=req.node_id,
            language=req.language, key=req.key, unit=req.unit,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return await serialize_suggestion(db, s)


@router.get("/mine")
async def api_my_suggestions(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    suggestions = await list_my_suggestions(db, user.id)
    return {"suggestions": [await serialize_suggestion(db, s) for s in suggestions]}


@router.get("")
async def api_list_suggestions(
    status: str | None = Query(default=None, pattern="^(pending|accepted|rejected)$"),
    item_id: int | None = None,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    suggestions = await list_suggestions(db, status=status, item_id=item_id)
    return {"suggestions": [await serialize_suggestion(db, s) for s in suggestions]}


@router.post("/{suggestion_id}/accept")
async def api_accept_suggestion(
    suggestion_id: int,
    note: str | None = None,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    try:
        s = await accept_suggestion(db, admin, suggestion_id, note)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not s:
        raise HTTPException(status_code=404, detail="Suggestion not found")
    return await serialize_suggestion(db, s)


@router.post("/{suggestion_id}/reject")
async def api_reject_suggestion(
    suggestion_id: int,
    note: str | None = None,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    try:
        s = await reject_suggestion(db, admin, suggestion_id, note)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not s:
        raise HTTPException(status_code=404, detail="Suggestion not found")
    return await serialize_suggestion(db, s)
