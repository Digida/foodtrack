from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.services.compliance_service import (
    check_dubai_import_compliance,
    get_required_documents,
    audit_item_compliance,
)
from app.utils.dependencies import get_current_user

router = APIRouter(prefix="/compliance", tags=["compliance"])


@router.get("/items/{item_id}/dubai")
async def api_dubai_compliance(
    item_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await check_dubai_import_compliance(db, item_id)
    if not result:
        raise HTTPException(status_code=404, detail="Item not found")
    return result


@router.get("/items/{item_id}/documents")
async def api_required_documents(
    item_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await get_required_documents(db, item_id)
    if not result:
        raise HTTPException(status_code=404, detail="Item not found")
    return result


@router.get("/items/{item_id}/report")
async def api_compliance_report(
    item_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await audit_item_compliance(db, item_id)
    if not result:
        raise HTTPException(status_code=404, detail="Item not found")
    return result
