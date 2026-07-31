import json
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.insurance import CargoPolicy, InsuranceClaim, ClaimStatus
from app.models.taxonomy import TaxonomyItem
from app.models.user import User, UserRole

PAGE_SIZE = 20


async def create_policy(
    db: AsyncSession,
    user: User,
    item_id: int,
    policy_number: str,
    coverage_amount: float,
    carrier: str | None = None,
    premium: float | None = None,
    currency: str = "USD",
    valid_from: datetime | None = None,
    valid_until: datetime | None = None,
) -> CargoPolicy:
    if user.role not in (UserRole.SUPERUSER, UserRole.ADMIN, UserRole.ENTERPRISE):
        raise PermissionError("Insufficient permissions")

    item = await db.get(TaxonomyItem, item_id)
    if not item:
        raise ValueError(f"TaxonomyItem {item_id} not found")

    now = datetime.now(timezone.utc)
    policy = CargoPolicy(
        item_id=item_id,
        carrier=carrier,
        policy_number=policy_number,
        coverage_amount=coverage_amount,
        premium=premium,
        currency=currency,
        valid_from=valid_from or now,
        valid_until=valid_until or now.replace(year=now.year + 1),
        created_by=user.id,
        tenant_id=user.tenant_id,
    )
    db.add(policy)
    await db.commit()
    await db.refresh(policy)
    return policy


async def list_policies(db: AsyncSession, page: int = 1, item_id: int | None = None) -> dict:
    q = select(CargoPolicy).order_by(CargoPolicy.created_at.desc())
    if item_id:
        q = q.where(CargoPolicy.item_id == item_id)

    count_q = select(func.count()).select_from(q.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    rows = (await db.execute(q.offset((page - 1) * PAGE_SIZE).limit(PAGE_SIZE))).scalars().all()
    results = [
        {
            "id": p.id,
            "item_id": p.item_id,
            "policy_number": p.policy_number,
            "carrier": p.carrier,
            "coverage_amount": p.coverage_amount,
            "currency": p.currency,
            "valid_from": p.valid_from.isoformat() if p.valid_from else None,
            "valid_until": p.valid_until.isoformat() if p.valid_until else None,
            "is_active": p.is_active,
        }
        for p in rows
    ]
    return {"policies": results, "total": total, "page": page, "total_pages": max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)}


async def file_claim(
    db: AsyncSession,
    user: User,
    policy_id: int,
    incident_type: str,
    claim_amount: float,
    description: str | None = None,
    currency: str = "USD",
    documents: list[str] | None = None,
) -> InsuranceClaim:
    if user.role not in (UserRole.SUPERUSER, UserRole.ADMIN, UserRole.ENTERPRISE):
        raise PermissionError("Insufficient permissions")

    policy = await db.get(CargoPolicy, policy_id)
    if not policy:
        raise ValueError(f"Policy {policy_id} not found")

    claim = InsuranceClaim(
        policy_id=policy_id,
        incident_type=incident_type,
        claim_amount=claim_amount,
        currency=currency,
        description=description,
        status=ClaimStatus.DRAFT,
        # documents stored as a proper JSON array (column is JSON/Text)
        documents_json=json.dumps(documents) if documents else None,
        filed_by=user.id,
        tenant_id=user.tenant_id,
    )
    db.add(claim)
    await db.commit()
    await db.refresh(claim)
    return claim


async def list_claims(db: AsyncSession, page: int = 1, status: str | None = None) -> dict:
    q = select(InsuranceClaim).order_by(InsuranceClaim.created_at.desc())
    if status:
        q = q.where(InsuranceClaim.status == status)

    count_q = select(func.count()).select_from(q.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    rows = (await db.execute(q.offset((page - 1) * PAGE_SIZE).limit(PAGE_SIZE))).scalars().all()
    results = [
        {
            "id": c.id,
            "policy_id": c.policy_id,
            "incident_type": c.incident_type,
            "claim_amount": c.claim_amount,
            "currency": c.currency,
            "status": c.status.value if hasattr(c.status, "value") else str(c.status),
            "description": c.description,
            # Decode the JSON array for the response
            "documents": json.loads(c.documents_json) if c.documents_json else [],
            "created_at": c.created_at.isoformat() if c.created_at else None,
        }
        for c in rows
    ]
    return {"claims": results, "total": total, "page": page, "total_pages": max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)}


async def update_claim_status(db: AsyncSession, user: User, claim_id: int, new_status: ClaimStatus) -> InsuranceClaim:
    if user.role not in (UserRole.SUPERUSER, UserRole.ADMIN):
        raise PermissionError("Admin access required")

    claim = await db.get(InsuranceClaim, claim_id)
    if not claim:
        raise ValueError(f"Claim {claim_id} not found")

    claim.status = new_status
    await db.commit()
    await db.refresh(claim)
    return claim
