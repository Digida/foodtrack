from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.rate import ItemRate
from app.models.taxonomy import TaxonomyItem


async def get_rates_for_item(db: AsyncSession, item_id: int) -> dict | None:
    item = await db.get(TaxonomyItem, item_id)
    if not item:
        return None

    rows = await db.execute(
        select(ItemRate).where(
            ItemRate.item_id == item_id,
            ItemRate.is_active == "Y",
        ).order_by(ItemRate.price_per_kg.asc())
    )
    rates = []
    for r in rows.scalars().all():
        rates.append({
            "id": r.id,
            "origin_region": r.origin_region,
            "destination_region": r.destination_region,
            "mode": r.mode,
            "carrier": r.carrier,
            "price_per_kg": r.price_per_kg,
            "currency": r.currency,
            "transit_days_min": r.transit_days_min,
            "transit_days_max": r.transit_days_max,
            "notes": r.notes,
        })

    return {
        "item_id": item_id,
        "item_name": item.common_name,
        "rate_count": len(rates),
        "rates": rates,
    }


async def calculate_shipping_cost(
    db: AsyncSession,
    item_id: int,
    origin_region: str,
    destination_region: str,
    weight_kg: float,
    mode: str | None = None,
) -> dict | None:
    item = await db.get(TaxonomyItem, item_id)
    if not item:
        return None

    q = select(ItemRate).where(
        ItemRate.item_id == item_id,
        ItemRate.origin_region.ilike(f"%{origin_region}%"),
        ItemRate.destination_region.ilike(f"%{destination_region}%"),
        ItemRate.is_active == "Y",
    )
    if mode:
        q = q.where(ItemRate.mode == mode)

    rows = (await db.execute(q.order_by(ItemRate.price_per_kg.asc()))).scalars().all()

    if not rows:
        return {
            "item_id": item_id,
            "item_name": item.common_name,
            "origin_region": origin_region,
            "destination_region": destination_region,
            "weight_kg": weight_kg,
            "cost_estimates": [],
            "note": "No rates found for this route",
        }

    estimates = []
    for r in rows:
        cost = round(r.price_per_kg * weight_kg, 2)
        estimates.append({
            "rate_id": r.id,
            "mode": r.mode,
            "carrier": r.carrier,
            "price_per_kg": r.price_per_kg,
            "currency": r.currency,
            "weight_kg": weight_kg,
            "total_cost": cost,
            "transit_days": f"{r.transit_days_min}-{r.transit_days_max}" if r.transit_days_min else None,
        })

    return {
        "item_id": item_id,
        "item_name": item.common_name,
        "origin_region": origin_region,
        "destination_region": destination_region,
        "weight_kg": weight_kg,
        "cost_estimates": estimates,
    }


async def compare_rates(
    db: AsyncSession,
    item_id: int,
    origin_region: str,
    destination_region: str,
) -> dict | None:
    item = await db.get(TaxonomyItem, item_id)
    if not item:
        return None

    rows = await db.execute(
        select(ItemRate).where(
            ItemRate.item_id == item_id,
            ItemRate.origin_region.ilike(f"%{origin_region}%"),
            ItemRate.destination_region.ilike(f"%{destination_region}%"),
            ItemRate.is_active == "Y",
        ).order_by(ItemRate.price_per_kg.asc())
    )

    rates = []
    for r in rows.scalars().all():
        rates.append({
            "id": r.id,
            "mode": r.mode,
            "carrier": r.carrier,
            "price_per_kg": r.price_per_kg,
            "currency": r.currency,
            "transit_days_min": r.transit_days_min,
            "transit_days_max": r.transit_days_max,
        })

    cheapest = min(rates, key=lambda x: x["price_per_kg"]) if rates else None
    fastest = min(
        (r for r in rates if r["transit_days_min"] is not None),
        key=lambda x: x["transit_days_min"], default=None,
    ) if rates else None

    return {
        "item_id": item_id,
        "item_name": item.common_name,
        "origin_region": origin_region,
        "destination_region": destination_region,
        "rate_count": len(rates),
        "rates": rates,
        "cheapest": cheapest,
        "fastest": fastest,
    }
