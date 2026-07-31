from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.services.search_service import unified_search, autocomplete_search, get_search_analytics
from app.utils.dependencies import get_current_user
from app.models.user import User, UserRole

router = APIRouter(prefix="/search", tags=["search"])


@router.get("")
async def api_search(
    q: str = Query(..., min_length=1),
    page: int = Query(1, ge=1),
    category: str | None = None,
    taxonomy_id: int | None = None,
    entity_type: str | None = Query(None, alias="entity_type"),
    collection_id: int | None = None,
    warehouse_id: int | None = None,
    sort_by: str = "relevance",
    request: Request = None,
    db: AsyncSession = Depends(get_db),
):
    user = None
    if request:
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            try:
                from app.services.auth_service import decode_access_token
                payload = decode_access_token(auth[7:])
                if payload and payload.get("sub"):
                    uid = int(payload["sub"])
                    r = await db.execute(select(User).where(User.id == uid))
                    user = r.scalar_one_or_none()
            except Exception:
                pass

    result = await unified_search(
        db, q, page, category, taxonomy_id, entity_type,
        collection_id, warehouse_id, sort_by,
        user_id=user.id if user else None,
        ip_address=request.client.host if request and request.client else None,
        include_batches=user is not None,
    )
    return result


@router.get("/autocomplete")
async def api_autocomplete(
    q: str = Query(..., min_length=1, max_length=100),
    limit: int = Query(8, ge=1, le=25),
    request: Request = None,
    db: AsyncSession = Depends(get_db),
):
    user = None
    if request:
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            try:
                from app.services.auth_service import decode_access_token
                payload = decode_access_token(auth[7:])
                if payload and payload.get("sub"):
                    uid = int(payload["sub"])
                    r = await db.execute(select(User).where(User.id == uid))
                    user = r.scalar_one_or_none()
            except Exception:
                pass
    results = await autocomplete_search(db, q, limit, include_batches=user is not None)
    return {"results": results}


@router.get("/analytics")
async def api_search_analytics(
    days: int = Query(7, ge=1, le=90),
    limit: int = Query(50, ge=1, le=200),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if user.role not in (UserRole.ADMIN, UserRole.ENTERPRISE):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    return await get_search_analytics(db, days, limit)
