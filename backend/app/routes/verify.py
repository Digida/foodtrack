from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.public_verify_service import public_verify

router = APIRouter(tags=["verify"])


@router.get("/verify/{code}")
async def api_public_verify(code: str, db: AsyncSession = Depends(get_db)):
    result = await public_verify(db, code)
    if not result:
        raise HTTPException(status_code=404, detail="No item found for this code")
    return result
