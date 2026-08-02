import hashlib
import secrets

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.database import get_db
from app.models.api_key import ApiKey
from app.models.user import User
from app.services.email_service import email_configured, send_email
from app.utils.dependencies import get_current_user

router = APIRouter(prefix="/developer", tags=["developer"])


class ApiKeyCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    rate_limit: int = Field(1000, ge=1, le=100000)
    scopes: str | None = None
    notify_email: EmailStr | None = None


@router.post("/api-keys")
async def api_create_api_key(
    req: ApiKeyCreateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    raw_key = f"ft_{secrets.token_hex(24)}"
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    key_prefix = raw_key[:8]

    api_key = ApiKey(
        key_prefix=key_prefix,
        key_hash=key_hash,
        name=req.name,
        rate_limit=req.rate_limit,
        scopes=req.scopes,
        created_by=user.id,
    )
    db.add(api_key)
    await db.commit()
    await db.refresh(api_key)

    # Automatically email the raw key to the developer (or an explicit
    # recipient). Delivery is best-effort and never blocks the response.
    email_to = req.notify_email or settings.DEV_EMAIL
    email_status = "not_configured"
    if email_configured():
        sent = await send_email(
            email_to,
            "FoodTrack — Your New API Key",
            (
                f"Hi {user.full_name or user.email},\n\n"
                f"A FoodTrack API key was generated:\n\n"
                f"  {raw_key}\n\n"
                f"Name: {req.name}\n"
                f"Rate limit: {req.rate_limit} requests/hour\n\n"
                f"Store it securely — it is shown only once.\n\n"
                f"— FoodTrack Team"
            ),
        )
        email_status = "sent" if sent else "failed"

    return {
        "id": api_key.id,
        "name": api_key.name,
        "api_key": raw_key,
        "key_prefix": key_prefix,
        "rate_limit": req.rate_limit,
        "scopes": req.scopes,
        "email_to": email_to,
        "email_status": email_status,
    }


@router.get("/api-keys")
async def api_list_api_keys(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List only API keys owned by the current user."""
    keys = await db.execute(
        select(ApiKey)
        .where(ApiKey.created_by == user.id)
        .order_by(ApiKey.created_at.desc())
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
            "last_used_at": k.last_used_at.isoformat() if k.last_used_at else None,
            "created_at": k.created_at.isoformat() if k.created_at else None,
        })
    return {"api_keys": results}


@router.delete("/api-keys/{key_id}")
async def api_revoke_api_key(
    key_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Revoke an API key. Only the key owner may revoke it."""
    api_key = await db.get(ApiKey, key_id)
    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")
    if api_key.created_by != user.id:
        raise HTTPException(status_code=403, detail="You do not own this API key")
    api_key.is_active = False
    await db.commit()
    return {"revoked": True}
