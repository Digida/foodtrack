from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.taxonomy import TaxonomyItem, ItemName
from app.models.product import Product
from app.models.certificate import Certificate
from app.models.tracking import Shipment, ShipmentBatch
from app.models.traceability import TraceabilityEvent
from app.services.code_service import resolve_scan
from app.services.item_detail_service import get_item_timeline, get_item_provenance


async def public_verify(db: AsyncSession, code: str) -> dict | None:
    scan = await resolve_scan(db, code)
    if scan.get("type") == "unknown":
        return None

    item_id = scan.get("item_id")
    if not item_id:
        return None

    item = await db.get(TaxonomyItem, item_id)
    if not item or not item.is_active:
        return None

    names = await db.execute(
        select(ItemName).where(ItemName.item_id == item_id)
    )
    names_list = [
        {"language": n.language, "name": n.name}
        for n in names.scalars().all()
    ]

    products = await db.execute(
        select(Product).where(Product.item_id == item_id, Product.is_active == True)
    )
    products_list = [
        {
            "name": p.name, "sku": p.sku,
            "producer_name": p.producer_name,
            "origin_country": p.origin_country,
            "image_url": None,
        }
        for p in products.scalars().all()
    ]

    certs = await db.execute(
        select(Certificate).where(Certificate.item_id == item_id)
        .order_by(Certificate.issued_date.desc())
    )
    certs_list = []
    for c in certs.scalars().all():
        certs_list.append({
            "type": c.type.value if hasattr(c.type, 'value') else str(c.type),
            "status": c.status.value if hasattr(c.status, 'value') else str(c.status),
            "issuer_name": c.issuer_name,
            "issuing_body": c.issuing_body,
            "issued_date": str(c.issued_date) if c.issued_date else None,
            "expiry_date": str(c.expiry_date) if c.expiry_date else None,
            "certificate_id": c.certificate_id,
        })

    timeline = await get_item_timeline(db, item_id)
    provenance = await get_item_provenance(db, item_id)

    return {
        "verified": True,
        "scan_type": scan.get("type"),
        "item": {
            "id": item.id,
            "common_name": item.common_name,
            "scientific_name": item.scientific_name,
            "code": item.code,
            "description": item.description,
            "image_url": item.image_url,
            "names": names_list,
        },
        "products": products_list,
        "certificates": certs_list,
        "provenance": provenance,
        "timeline": timeline[:20] if timeline else [],
    }
