import hashlib
import secrets

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.api_key import ApiKey
from app.models.user import User
from app.utils.dependencies import get_current_user

router = APIRouter(prefix="/developer", tags=["developer"])


@router.post("/api-keys")
async def api_create_api_key(
    name: str = Query(...),
    rate_limit: int = Query(1000),
    scopes: str | None = Query(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    raw_key = f"ft_{secrets.token_hex(24)}"
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    key_prefix = raw_key[:8]

    api_key = ApiKey(
        key_prefix=key_prefix,
        key_hash=key_hash,
        name=name,
        rate_limit=rate_limit,
        scopes=scopes,
        created_by=user.id,
    )
    db.add(api_key)
    await db.commit()
    await db.refresh(api_key)

    return {"id": api_key.id, "name": api_key.name, "api_key": raw_key, "key_prefix": key_prefix, "rate_limit": rate_limit, "scopes": scopes}


@router.get("/api-keys")
async def api_list_api_keys(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    keys = await db.execute(
        select(ApiKey).order_by(ApiKey.created_at.desc())
    )
    results = []
    for k in keys.scalars().all():
        results.append({
            "id": k.id,
            "key_prefix": k.key_prefix,
            "name": k.name,
            "rate_limit": k.rate_limit,
            "scopes": k.scopes,
            "is_active": k.is_active,
            "last_used_at": str(k.last_used_at) if k.last_used_at else None,
            "created_at": str(k.created_at) if k.created_at else None,
        })
    return {"api_keys": results}


@router.delete("/api-keys/{key_id}")
async def api_revoke_api_key(
    key_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    api_key = await db.get(ApiKey, key_id)
    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")
    api_key.is_active = False
    await db.commit()
    return {"revoked": True}
