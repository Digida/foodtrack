from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.taxonomy import TaxonomyItem, TaxonomyNode
from app.models.certificate import Certificate, CertificateStatus
from tools.compliance_checker import check_compliance
from tools.regulation_fetcher import fetch_regulations

CATEGORY_MAP = {
    "MEAT_POULTRY": "meat",
    "SEAFOOD": "seafood",
    "ADDITIONAL_SEAFOOD": "seafood",
    "DAIRY_EGGS": "dairy",
    "ADDITIONAL_DAIRY": "dairy",
    "BEVERAGE_CROPS": "beverage",
    "PROCESSED_FOODS": "food",
    "GRAINS": "produce",
    "LEGUMES": "produce",
    "TROPICAL_FRUITS": "produce",
    "TEMPERATE_FRUITS": "produce",
    "VEGETABLES": "produce",
    "ADDITIONAL_GRAINS": "produce",
    "ADDITIONAL_FRUITS": "produce",
    "ADDITIONAL_VEGETABLES": "produce",
    "HERBS_SPICES": "produce",
    "ADDITIONAL_HERBS_SPICES": "produce",
    "NUTS_SEEDS": "produce",
    "OILS_FATS": "food",
    "MUSHROOMS": "produce",
    "SEAWEED": "produce",
}


def _map_category(node_code: str | None) -> str:
    if not node_code:
        return "food"
    return CATEGORY_MAP.get(node_code, "food")


async def check_dubai_import_compliance(db: AsyncSession, item_id: int) -> dict | None:
    item = await db.get(TaxonomyItem, item_id)
    if not item:
        return None

    node = await db.get(TaxonomyNode, item.node_id) if item.node_id else None
    cat = _map_category(node.code if node else None)

    certs = await db.execute(
        select(Certificate).where(
            Certificate.item_id == item_id,
            Certificate.status.in_([CertificateStatus.ISSUED, CertificateStatus.VERIFIED, CertificateStatus.ACTIVE]),
        )
    )
    cert_types = [c.type.value if hasattr(c.type, 'value') else str(c.type) for c in certs.scalars().all()]

    result = check_compliance(
        item_category=cat,
        target_market="dubai",
        current_certs=cert_types,
    )

    regulations = await fetch_regulations("dubai", cat)

    return {
        "item_id": item_id,
        "item_name": item.common_name,
        "category": cat,
        "node_code": node.code if node else None,
        "compliance": result,
        "regulations": regulations,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


async def get_required_documents(db: AsyncSession, item_id: int) -> dict | None:
    item = await db.get(TaxonomyItem, item_id)
    if not item:
        return None

    node = await db.get(TaxonomyNode, item.node_id) if item.node_id else None
    cat = _map_category(node.code if node else None)

    certs = await db.execute(
        select(Certificate).where(
            Certificate.item_id == item_id,
            Certificate.status.in_([CertificateStatus.ISSUED, CertificateStatus.VERIFIED, CertificateStatus.ACTIVE]),
        )
    )
    cert_types = [c.type.value if hasattr(c.type, 'value') else str(c.type) for c in certs.scalars().all()]

    result = check_compliance(
        item_category=cat,
        target_market="dubai",
        current_certs=cert_types,
    )

    missing = result.get("missing_certifications", [])
    missing_labelling = result.get("missing_labelling", [])

    return {
        "item_id": item_id,
        "item_name": item.common_name,
        "category": cat,
        "target_market": "dubai",
        "compliant": result.get("compliant", False),
        "score": result.get("score", 0),
        "required_certifications": CATEGORY_MAP.get(node.code if node else None, {}),
        "present_certifications": cert_types,
        "missing_certifications": missing,
        "missing_labelling": missing_labelling,
        "document_checklist": _generate_checklist(missing, missing_labelling),
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


def _generate_checklist(missing_certs: list[str], missing_labelling: list[str]) -> list[dict]:
    checklist = []
    for c in missing_certs:
        checklist.append({"type": "certification", "name": c, "status": "missing"})
    for l in missing_labelling:
        checklist.append({"type": "labelling", "name": l, "status": "missing"})
    if not checklist:
        checklist.append({"type": "all", "name": "All requirements met", "status": "satisfied"})
    return checklist


async def audit_item_compliance(db: AsyncSession, item_id: int) -> dict | None:
    item = await db.get(TaxonomyItem, item_id)
    if not item:
        return None

    node = await db.get(TaxonomyNode, item.node_id) if item.node_id else None
    cat = _map_category(node.code if node else None)

    all_certs = await db.execute(
        select(Certificate).where(Certificate.item_id == item_id)
        .order_by(Certificate.issued_date.desc())
    )
    cert_list = []
    for c in all_certs.scalars().all():
        now = datetime.now(timezone.utc)
        expiry = c.expiry_date
        is_expired = expiry and expiry.replace(tzinfo=timezone.utc) < now if expiry else False
        cert_list.append({
            "id": c.id,
            "certificate_id": c.certificate_id,
            "type": c.type.value if hasattr(c.type, 'value') else str(c.type),
            "status": c.status.value if hasattr(c.status, 'value') else str(c.status),
            "issuer_name": c.issuer_name,
            "issued_date": str(c.issued_date) if c.issued_date else None,
            "expiry_date": str(c.expiry_date) if c.expiry_date else None,
            "is_expired": is_expired,
        })

    cert_types = [c["type"] for c in cert_list if c["status"] not in ("expired", "revoked")]
    result = check_compliance(cat, "dubai", cert_types)

    now = datetime.now(timezone.utc)
    expiring_soon = [
        c for c in cert_list
        if c.get("expiry_date") and not c.get("is_expired")
    ]

    return {
        "item_id": item_id,
        "item_name": item.common_name,
        "category": cat,
        "node_code": node.code if node else None,
        "total_certificates": len(cert_list),
        "active_certificates": len(cert_types),
        "expired_certificates": sum(1 for c in cert_list if c["is_expired"]),
        "compliance": result,
        "certificates": cert_list,
        "recommendations": _generate_recommendations(result, expiring_soon),
        "audited_at": datetime.now(timezone.utc).isoformat(),
    }


def _generate_recommendations(compliance_result: dict, expiring_soon: list) -> list[str]:
    recs = []
    for c in compliance_result.get("missing_certifications", []):
        recs.append(f"Obtain {c} certification")
    for l in compliance_result.get("missing_labelling", []):
        recs.append(f"Add {l} to labelling")
    for c in expiring_soon:
        recs.append(f"Renew {c['type']} — expires {c['expiry_date']}")
    if not recs and compliance_result.get("compliant"):
        recs.append("All compliance requirements satisfied")
    return recs
