"""Analytics service: dashboard aggregation, reports, filtering."""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, case

from app.models.product import Product, ProductCategory
from app.models.traceability import TraceabilityEvent, EventType
from app.models.certificate import Certificate, CertificateStatus, CertificateType
from app.models.tracking import ShipmentBatch, Shipment
from app.models.inventory import ItemInventory
from app.models.taxonomy import TaxonomyItem


async def get_dashboard_stats(db: AsyncSession) -> dict:
    total_products = await db.scalar(select(func.count(Product.id)).where(Product.is_active == True))
    total_events = await db.scalar(select(func.count(TraceabilityEvent.id)))
    total_certificates = await db.scalar(select(func.count(Certificate.id)))
    verified_certs = await db.scalar(
        select(func.count(Certificate.id)).where(Certificate.status == CertificateStatus.VERIFIED)
    )
    return {
        "total_products": total_products or 0,
        "total_traceability_events": total_events or 0,
        "total_certificates": total_certificates or 0,
        "verified_certificates": verified_certs or 0,
    }


async def get_products_by_category(db: AsyncSession) -> list[dict]:
    result = await db.execute(
        select(Product.category, func.count(Product.id))
        .where(Product.is_active == True).group_by(Product.category)
    )
    return [{"category": cat.value, "count": cnt} for cat, cnt in result.all()]


async def get_events_by_type(db: AsyncSession) -> list[dict]:
    result = await db.execute(
        select(TraceabilityEvent.event_type, func.count(TraceabilityEvent.id))
        .group_by(TraceabilityEvent.event_type)
    )
    return [{"type": et.value, "count": cnt} for et, cnt in result.all()]


async def get_certificates_by_status(db: AsyncSession) -> list[dict]:
    result = await db.execute(
        select(Certificate.status, func.count(Certificate.id)).group_by(Certificate.status)
    )
    return [{"status": s.value, "count": cnt} for s, cnt in result.all()]


async def get_top_moved_items(db: AsyncSession, limit: int = 20) -> list[dict]:
    """Items with the most shipment movement volume."""
    result = await db.execute(
        select(
            ShipmentBatch.item_id,
            func.sum(ShipmentBatch.quantity).label("total_moved"),
        )
        .where(ShipmentBatch.item_id.isnot(None))
        .group_by(ShipmentBatch.item_id)
        .order_by(desc("total_moved"))
        .limit(limit)
    )
    rows = result.all()
    item_ids = [r.item_id for r in rows]
    items = {i.id: i for i in (await db.execute(
        select(TaxonomyItem).where(TaxonomyItem.id.in_(item_ids))
    )).scalars().all()}
    return [{
        "item_id": r.item_id,
        "item_code": items[r.item_id].code if r.item_id in items else None,
        "item_name": items[r.item_id].common_name if r.item_id in items else None,
        "total_moved": int(r.total_moved),
    } for r in rows]


async def get_top_stored_items(db: AsyncSession, limit: int = 20) -> list[dict]:
    """Items with the highest current stock levels."""
    result = await db.execute(
        select(
            ItemInventory.item_id,
            func.sum(ItemInventory.total_quantity).label("total_stock"),
        )
        .group_by(ItemInventory.item_id)
        .order_by(desc("total_stock"))
        .limit(limit)
    )
    rows = result.all()
    item_ids = [r.item_id for r in rows]
    items = {i.id: i for i in (await db.execute(
        select(TaxonomyItem).where(TaxonomyItem.id.in_(item_ids))
    )).scalars().all()}
    return [{
        "item_id": r.item_id,
        "item_code": items[r.item_id].code if r.item_id in items else None,
        "item_name": items[r.item_id].common_name if r.item_id in items else None,
        "total_stock": int(r.total_stock),
    } for r in rows]


async def get_item_delay_rates(db: AsyncSession, limit: int = 20) -> list[dict]:
    """Delay rates per item — proportion of shipments with exception status."""
    total = select(
        ShipmentBatch.item_id,
        func.count(ShipmentBatch.id).label("total_shipments"),
    ).where(ShipmentBatch.item_id.isnot(None)).group_by(ShipmentBatch.item_id).subquery()

    delayed_sq = select(
        ShipmentBatch.item_id,
        func.count(ShipmentBatch.id).label("delayed_count"),
    ).join(Shipment, ShipmentBatch.shipment_id == Shipment.id).where(
        ShipmentBatch.item_id.isnot(None),
        Shipment.status.in_(["exception", "delayed"]),
    ).group_by(ShipmentBatch.item_id).subquery()

    result = await db.execute(
        select(
            total.c.item_id,
            total.c.total_shipments,
            func.coalesce(delayed_sq.c.delayed_count, 0).label("delayed_count"),
        )
        .outerjoin(delayed_sq, total.c.item_id == delayed_sq.c.item_id)
        .order_by(desc("delayed_count"))
        .limit(limit)
    )
    rows = result.all()
    item_ids = [r.item_id for r in rows]
    items = {i.id: i for i in (await db.execute(
        select(TaxonomyItem).where(TaxonomyItem.id.in_(item_ids))
    )).scalars().all()}
    return [{
        "item_id": r.item_id,
        "item_code": items[r.item_id].code if r.item_id in items else None,
        "item_name": items[r.item_id].common_name if r.item_id in items else None,
        "total_shipments": int(r.total_shipments),
        "delayed_shipments": int(r.delayed_count),
        "delay_rate": round(int(r.delayed_count) / max(int(r.total_shipments), 1) * 100, 1),
    } for r in rows]


async def get_low_stock_items(db: AsyncSession, threshold: int = 50, limit: int = 20) -> list[dict]:
    """Items with stock below threshold."""
    result = await db.execute(
        select(
            ItemInventory.item_id,
            func.sum(ItemInventory.total_quantity).label("total_stock"),
        )
        .group_by(ItemInventory.item_id)
        .having(func.sum(ItemInventory.total_quantity) < threshold)
        .order_by(desc("total_stock"))
        .limit(limit)
    )
    rows = result.all()
    item_ids = [r.item_id for r in rows]
    items = {i.id: i for i in (await db.execute(
        select(TaxonomyItem).where(TaxonomyItem.id.in_(item_ids))
    )).scalars().all()}
    return [{
        "item_id": r.item_id,
        "item_code": items[r.item_id].code if r.item_id in items else None,
        "item_name": items[r.item_id].common_name if r.item_id in items else None,
        "total_stock": int(r.total_stock),
        "threshold": threshold,
    } for r in rows]


async def get_certification_gaps(db: AsyncSession, limit: int = 20) -> list[dict]:
    """Items with zero certificates — certification gaps."""
    subq = select(Certificate.item_id).where(Certificate.item_id.isnot(None)).distinct().subquery()
    result = await db.execute(
        select(TaxonomyItem)
        .where(
            TaxonomyItem.is_active == True,
            TaxonomyItem.id.notin_(select(subq.c.item_id)),
        )
        .limit(limit)
    )
    items = result.scalars().all()
    return [{
        "item_id": item.id,
        "item_code": item.code,
        "item_name": item.common_name,
    } for item in items]
