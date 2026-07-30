from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.i18n_service import get_supported_languages, translate, get_accept_language
from app.models.taxonomy import TaxonomyItem, ItemName

router = APIRouter(prefix="/i18n", tags=["i18n"])


@router.get("/languages")
async def api_supported_languages():
    return {"supported_languages": get_supported_languages()}


@router.get("/translate")
async def api_translate(
    key: str = Query(...),
    lang: str = Query("en"),
):
    return {"key": key, "translated": translate(key, lang), "language": lang}


@router.get("/items/{item_id}/localized")
async def api_localized_item(
    item_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    lang = get_accept_language(request.headers.get("accept-language"))

    item = await db.get(TaxonomyItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    names = await db.execute(
        select(ItemName).where(ItemName.item_id == item_id)
    )
    name_map = {n.language: n.name for n in names.scalars().all()}

    localized_name = name_map.get(lang) or name_map.get("en") or item.common_name

    return {
        "item_id": item.id,
        "code": item.code,
        "localized_name": localized_name,
        "language": lang,
        "scientific_name": item.scientific_name,
        "all_names": name_map,
    }
