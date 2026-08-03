from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.database import get_db
from app.models.user import User
from app.services.share_service import generate_share_links, get_peer_comparison
from app.services.product_service import get_product_detail, get_product_by_sku
from app.utils.dependencies import get_current_user_or_guest

router = APIRouter(prefix="/share", tags=["share"])


class ShareRequest(BaseModel):
    product_id: int


@router.post("/generate-link")
async def api_generate_share_link(req: ShareRequest,
                                   user: User = Depends(get_current_user_or_guest),
                                   db: AsyncSession = Depends(get_db)):
    product = await get_product_detail(db, req.product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    result = await generate_share_links(product.sku, product.name)
    return result


@router.get("/peer-compare/{product_id}")
async def api_peer_compare(product_id: int,
                            db: AsyncSession = Depends(get_db)):
    try:
        result = await get_peer_comparison(db, product_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
