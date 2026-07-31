from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.services.public_verify_service import public_verify
from app.utils.dependencies import get_current_user

router = APIRouter(tags=["verify"])


@router.get("/verify/{code}")
async def api_public_verify(code: str, user: User = Depends(get_current_user),
                            db: AsyncSession = Depends(get_db)):
    result = await public_verify(db, code)
    if not result:
        raise HTTPException(status_code=404, detail="No item found for this code")
    return result
