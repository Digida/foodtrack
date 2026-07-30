from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app.models.esg import ItemCarbonFootprint
from app.models.taxonomy import TaxonomyItem
from app.models.user import User, UserRole
from app.utils.dependencies import get_current_user

router = APIRouter(prefix="/esg", tags=["esg"])


@router.post("/items/{item_id}/carbon-footprint")
async def api_create_carbon_footprint(
    item_id: int,
    kg_co2e_per_kg: float = Query(...),
    water_usage_l_per_kg: float | None = Query(None),
    source: str | None = Query(None),
    methodology: str | None = Query(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if user.role not in (UserRole.ADMIN, UserRole.ENTERPRISE):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    item = await db.get(TaxonomyItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    cf = ItemCarbonFootprint(item_id=item_id, kg_co2e_per_kg=kg_co2e_per_kg, water_usage_l_per_kg=water_usage_l_per_kg, source=source, methodology=methodology, created_by=user.id)
    db.add(cf)
    await db.commit()
    await db.refresh(cf)
    return {"id": cf.id, "kg_co2e_per_kg": cf.kg_co2e_per_kg}


@router.get("/items/{item_id}")
async def api_get_esg(
    item_id: int,
    db: AsyncSession = Depends(get_db),
):
    item = await db.get(TaxonomyItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    rows = await db.execute(
        select(ItemCarbonFootprint).where(ItemCarbonFootprint.item_id == item_id).order_by(ItemCarbonFootprint.created_at.desc()).limit(5)
    )
    footprints = []
    for cf in rows.scalars().all():
        footprints.append({
            "id": cf.id,
            "kg_co2e_per_kg": cf.kg_co2e_per_kg,
            "water_usage_l_per_kg": cf.water_usage_l_per_kg,
            "source": cf.source,
            "methodology": cf.methodology,
            "confidence": cf.confidence,
            "created_at": str(cf.created_at) if cf.created_at else None,
        })

    return {
        "item_id": item_id,
        "item_name": item.common_name,
        "carbon_footprints": footprints,
    }


@router.get("/summary")
async def api_esg_summary(
    db: AsyncSession = Depends(get_db),
):
    rows = await db.execute(
        select(ItemCarbonFootprint.item_id, TaxonomyItem.common_name, ItemCarbonFootprint.kg_co2e_per_kg)
        .join(TaxonomyItem, ItemCarbonFootprint.item_id == TaxonomyItem.id)
        .order_by(ItemCarbonFootprint.kg_co2e_per_kg.desc())
        .limit(20)
    )

    items = [{"item_id": item_id, "item_name": name, "kg_co2e_per_kg": co2} for item_id, name, co2 in rows.all()]

    avg = await db.execute(select(func.avg(ItemCarbonFootprint.kg_co2e_per_kg)))
    average_co2 = avg.scalar() or 0

    return {"items": items, "average_kg_co2e_per_kg": round(average_co2, 2), "item_count": len(items)}
