from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.models.supplier import Supplier, SupplierScorecard
from app.models.user import User, UserRole

PAGE_SIZE = 20


async def create_supplier(
    db: AsyncSession,
    user: User,
    name: str,
    contact_name: str | None = None,
    contact_email: str | None = None,
    contact_phone: str | None = None,
    address: str | None = None,
    regions: str | None = None,
    certifications: str | None = None,
) -> Supplier:
    if user.role not in (UserRole.SUPERUSER, UserRole.ADMIN, UserRole.ENTERPRISE):
        raise PermissionError("Insufficient permissions")

    supplier = Supplier(
        name=name,
        contact_name=contact_name,
        contact_email=contact_email,
        contact_phone=contact_phone,
        address=address,
        regions=regions,
        certifications=certifications,
        created_by=user.id,
        tenant_id=user.tenant_id,
    )
    db.add(supplier)
    await db.commit()
    await db.refresh(supplier)
    return supplier


async def get_supplier_detail(db: AsyncSession, supplier_id: int) -> dict | None:
    supplier = await db.get(Supplier, supplier_id)
    if not supplier:
        return None

    scorecards_result = await db.execute(
        select(SupplierScorecard)
        .where(SupplierScorecard.supplier_id == supplier_id)
        .order_by(SupplierScorecard.created_at.desc())
        .limit(10)
    )
    scorecards = scorecards_result.scalars().all()

    return {
        "id": supplier.id,
        "name": supplier.name,
        "contact_name": supplier.contact_name,
        "contact_email": supplier.contact_email,
        "contact_phone": supplier.contact_phone,
        "address": supplier.address,
        "regions": supplier.regions,
        "certifications": supplier.certifications,
        "is_active": supplier.is_active,
        "created_at": supplier.created_at.isoformat() if supplier.created_at else None,
        "scorecards": [
            {
                "id": s.id,
                "period": s.period,
                "overall_score": s.overall_score,
                "on_time_delivery_pct": s.on_time_delivery_pct,
                "quality_score": s.quality_score,
                "created_at": s.created_at.isoformat() if s.created_at else None,
            }
            for s in scorecards
        ],
    }


async def list_suppliers(db: AsyncSession, page: int = 1, tenant_id: int | None = None):
    q = select(Supplier).order_by(Supplier.name.asc())
    if tenant_id is not None:
        q = q.where(Supplier.tenant_id == tenant_id)
    count_q = select(func.count()).select_from(q.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    rows = (await db.execute(q.offset((page - 1) * PAGE_SIZE).limit(PAGE_SIZE))).scalars().all()
    results = [
        {
            "id": s.id,
            "name": s.name,
            "contact_email": s.contact_email,
            "regions": s.regions,
            "is_active": s.is_active,
        }
        for s in rows
    ]
    return {"suppliers": results, "total": total, "page": page, "total_pages": max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)}


async def create_scorecard(
    db: AsyncSession,
    user: User,
    supplier_id: int,
    period: str,
    on_time_delivery_pct: float | None = None,
    quality_score: float | None = None,
    cert_compliance_pct: float | None = None,
    audit_result: str | None = None,
    notes: str | None = None,
) -> SupplierScorecard:
    if user.role not in (UserRole.SUPERUSER, UserRole.ADMIN, UserRole.ENTERPRISE):
        raise PermissionError("Insufficient permissions")

    supplier = await db.get(Supplier, supplier_id)
    if not supplier:
        raise ValueError(f"Supplier {supplier_id} not found")

    scores = [s for s in [on_time_delivery_pct, quality_score, cert_compliance_pct] if s is not None]
    overall_score = round(sum(scores) / len(scores), 2) if scores else None

    scorecard = SupplierScorecard(
        supplier_id=supplier_id,
        period=period,
        on_time_delivery_pct=on_time_delivery_pct,
        quality_score=quality_score,
        cert_compliance_pct=cert_compliance_pct,
        audit_result=audit_result,
        overall_score=overall_score,
        notes=notes,
        created_by=user.id,
        tenant_id=user.tenant_id,
    )
    db.add(scorecard)
    await db.commit()
    await db.refresh(scorecard)
    return scorecard


async def get_supplier_ranking(db: AsyncSession) -> dict:
    """Return top 20 suppliers by best overall scorecard score.

    Uses a single JOIN query instead of N+1 per-row supplier lookups.
    """
    # Fetch top 50 scorecards joined with their supplier in one round-trip
    stmt = (
        select(SupplierScorecard, Supplier)
        .join(Supplier, SupplierScorecard.supplier_id == Supplier.id)
        .where(Supplier.is_active == True)
        .order_by(SupplierScorecard.overall_score.desc().nullslast())
        .limit(50)
    )
    rows = (await db.execute(stmt)).all()

    seen: dict[int, dict] = {}
    for scorecard, supplier in rows:
        if scorecard.supplier_id not in seen:
            seen[scorecard.supplier_id] = {
                "supplier_id": scorecard.supplier_id,
                "supplier_name": supplier.name,
                "overall_score": scorecard.overall_score,
                "period": scorecard.period,
                "quality_score": scorecard.quality_score,
                "on_time_delivery_pct": scorecard.on_time_delivery_pct,
            }

    return {"ranking": list(seen.values())[:20]}
