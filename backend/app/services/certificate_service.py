"""Certificate service: issuance, verification, revocation, lifecycle management."""

import uuid
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.certificate import Certificate, CertificateStatus, CertificateType, CertificateRequest, CertificateRequestStatus
from app.models.taxonomy import TaxonomyItem
from app.models.product import Product
from app.models.user import User, UserRole
from tools.notification_dispatcher import send_notification

DUBAI_MARKET_CERTS: dict[str, list[CertificateType]] = {
    "dubai_import": [
        CertificateType.HALAL,
        CertificateType.ORIGIN,
        CertificateType.SAFETY,
        CertificateType.ISO22000,
    ],
    "dubai_hospitality": [
        CertificateType.HALAL,
        CertificateType.ORGANIC,
        CertificateType.GLOBALGAP,
        CertificateType.BRC,
        CertificateType.ORIGIN,
    ],
    "eu_export": [
        CertificateType.ORGANIC,
        CertificateType.GLOBALGAP,
        CertificateType.GRASP,
        CertificateType.SMETA,
        CertificateType.BRC,
    ],
}

CERT_EXPIRY_NOTIFY_DAYS = 30


async def issue_certificate(db: AsyncSession, user: User, product_id: int | None = None, cert_type: CertificateType = None,
                             issuing_body: str | None = None, recipient_entity: str | None = None,
                             description: str | None = None, expiry_date: str | None = None,
                             document_url: str | None = None, metadata_json: str | None = None,
                             item_id: int | None = None) -> Certificate:
    if user.role not in (UserRole.SUPERUSER, UserRole.ADMIN, UserRole.ENTERPRISE, UserRole.VERIFIER):
        raise PermissionError("Insufficient permissions")
    if product_id is None and item_id is None:
        raise ValueError("A product_id or item_id is required to issue a certificate")
    product = None
    if product_id is not None:
        prod_result = await db.execute(select(Product).where(Product.id == product_id))
        product = prod_result.scalar_one_or_none()
        if not product:
            raise ValueError("Product not found")
    if item_id is not None:
        item = await db.get(TaxonomyItem, item_id)
        if not item:
            raise ValueError("Item not found")
    cert_id = f"FT-{uuid.uuid4().hex[:8].upper()}"
    cert = Certificate(
        certificate_id=cert_id, product_id=product_id, item_id=item_id, type=cert_type,
        status=CertificateStatus.ISSUED, issuer_id=user.id, issuer_name=user.full_name,
        issuing_body=issuing_body or user.company, recipient_entity=recipient_entity,
        description=description, digital_signature=uuid.uuid4().hex,
        document_url=document_url, metadata_json=metadata_json,
    )
    if expiry_date:
        cert.expiry_date = datetime.fromisoformat(expiry_date.replace("Z", "+00:00"))
    db.add(cert)
    await db.commit()
    await db.refresh(cert)
    return cert


async def list_certificates(db: AsyncSession, status: CertificateStatus | None = None,
                             cert_type: CertificateType | None = None, limit: int = 100) -> list[Certificate]:
    query = select(Certificate)
    if status:
        query = query.where(Certificate.status == status)
    if cert_type:
        query = query.where(Certificate.type == cert_type)
    query = query.order_by(Certificate.issued_date.desc()).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_certificate(db: AsyncSession, certificate_id: str) -> Certificate | None:
    result = await db.execute(select(Certificate).where(Certificate.certificate_id == certificate_id))
    return result.scalar_one_or_none()


async def verify_certificate(db: AsyncSession, user: User, certificate_id: str) -> Certificate:
    result = await db.execute(select(Certificate).where(Certificate.certificate_id == certificate_id))
    cert = result.scalar_one_or_none()
    if not cert:
        raise ValueError("Certificate not found")
    if cert.status != CertificateStatus.ISSUED:
        raise ValueError(f"Cannot verify certificate in status '{cert.status.value}'")
    cert.status = CertificateStatus.VERIFIED
    cert.verified_by = user.id
    cert.verified_date = datetime.now(timezone.utc)
    await db.commit()
    return cert


async def revoke_certificate(db: AsyncSession, user: User, certificate_id: str) -> Certificate:
    if user.role not in (UserRole.SUPERUSER, UserRole.ADMIN):
        raise PermissionError("Admin only")
    result = await db.execute(select(Certificate).where(Certificate.certificate_id == certificate_id))
    cert = result.scalar_one_or_none()
    if not cert:
        raise ValueError("Certificate not found")
    cert.status = CertificateStatus.REVOKED
    await db.commit()
    return cert


async def get_certificates_for_item(db: AsyncSession, item_id: int) -> list[dict]:
    result = await db.execute(
        select(Certificate).where(Certificate.item_id == item_id)
        .order_by(Certificate.issued_date.desc())
    )
    certs = result.scalars().all()
    if not certs:
        result = await db.execute(
            select(Certificate).join(Product, Certificate.product_id == Product.id)
            .where(Product.item_id == item_id)
            .order_by(Certificate.issued_date.desc())
        )
        certs = result.scalars().all()
    return [serialize_certificate(c) for c in certs]


async def verify_certificate_chain(db: AsyncSession, item_id: int) -> dict:
    item = await db.get(TaxonomyItem, item_id)
    if not item:
        raise ValueError("Item not found")

    certs = await get_certificates_for_item(db, item_id)
    now = datetime.now(timezone.utc)

    issued = [c for c in certs if c["status"] == "issued"]
    verified = [c for c in certs if c["status"] == "verified"]
    expired = [c for c in certs if c["status"] == "expired"]
    revoked = [c for c in certs if c["status"] == "revoked"]

    active = [c for c in certs if c["status"] in ("issued", "verified")]
    expired_chain = []
    for c in active:
        if c.get("expiry_date"):
            try:
                exp = datetime.fromisoformat(c["expiry_date"].replace("Z", "+00:00"))
                if exp.tzinfo is None:
                    exp = exp.replace(tzinfo=timezone.utc)
                if exp < now:
                    expired_chain.append(c["certificate_id"])
            except (ValueError, TypeError):
                pass

    return {
        "item_id": item_id,
        "item_name": item.common_name,
        "total_certificates": len(certs),
        "active_count": len(active),
        "issued_count": len(issued),
        "verified_count": len(verified),
        "expired_count": len(expired),
        "revoked_count": len(revoked),
        "expired_in_chain": expired_chain,
        "chain_valid": len(expired_chain) == 0 and len(revoked) == 0,
        "certificates": certs,
    }


async def get_missing_certifications(db: AsyncSession, item_id: int, target_market: str = "dubai_import") -> dict:
    item = await db.get(TaxonomyItem, item_id)
    if not item:
        raise ValueError("Item not found")

    required = DUBAI_MARKET_CERTS.get(target_market, [])
    if not required:
        return {"item_id": item_id, "target_market": target_market, "message": "Unknown market profile", "missing": [], "optional": []}

    existing = await get_certificates_for_item(db, item_id)
    existing_types = {c["type"] for c in existing if c["status"] in ("issued", "verified")}

    missing = [t for t in required if t not in existing_types]
    optional = [t for t in required if t not in missing and t in existing_types]

    return {
        "item_id": item_id,
        "item_name": item.common_name,
        "target_market": target_market,
        "total_required": len(required),
        "fulfilled": len(optional),
        "missing": [t.value for t in missing],
        "existing": [t.value for t in optional],
        "compliant": len(missing) == 0,
    }


async def request_certificate(
    db: AsyncSession, user: User, item_id: int, requested_type: CertificateType,
    cargo_id: int | None = None, applicant_notes: str | None = None,
    target_market: str | None = None,
) -> CertificateRequest:
    item = await db.get(TaxonomyItem, item_id)
    if not item:
        raise ValueError(f"TaxonomyItem {item_id} not found")

    req = CertificateRequest(
        cargo_id=cargo_id, item_id=item_id, requested_type=requested_type,
        applicant_id=user.id, applicant_notes=applicant_notes,
        target_market=target_market or "dubai_import",
    )
    db.add(req)
    await db.commit()
    await db.refresh(req)
    return req


async def list_certificate_requests(
    db: AsyncSession, status: CertificateRequestStatus | None = None,
    applicant_id: int | None = None, limit: int = 50,
) -> list[CertificateRequest]:
    query = select(CertificateRequest)
    if status:
        query = query.where(CertificateRequest.status == status)
    if applicant_id:
        query = query.where(CertificateRequest.applicant_id == applicant_id)
    query = query.order_by(CertificateRequest.created_at.desc()).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_certificate_request(db: AsyncSession, request_id: int) -> CertificateRequest | None:
    return await db.get(CertificateRequest, request_id)


async def review_certificate_request(
    db: AsyncSession, user: User, request_id: int,
    decision: CertificateRequestStatus, reviewer_notes: str | None = None,
) -> CertificateRequest:
    if user.role not in (UserRole.SUPERUSER, UserRole.ADMIN, UserRole.VERIFIER):
        raise PermissionError("Only ADMIN and VERIFIER can review requests")

    req = await db.get(CertificateRequest, request_id)
    if not req:
        raise ValueError("Certificate request not found")
    if req.status != CertificateRequestStatus.PENDING:
        raise ValueError(f"Cannot review request in status '{req.status.value}'")
    if decision not in (CertificateRequestStatus.APPROVED, CertificateRequestStatus.REJECTED):
        raise ValueError("Review decision must be 'approved' or 'rejected'")

    req.status = decision
    req.reviewer_id = user.id
    req.reviewer_notes = reviewer_notes
    req.reviewed_at = datetime.now(timezone.utc)

    if decision == CertificateRequestStatus.APPROVED:
        cert = await issue_certificate(
            db=db, user=user, cert_type=req.requested_type,
            item_id=req.item_id,
            recipient_entity=getattr(user, 'company', None),
            description=f"Auto-issued from approved request #{request_id}",
        )

    await db.commit()
    await db.refresh(req)
    return req


def serialize_certificate_request(req: CertificateRequest) -> dict:
    return {
        "id": req.id,
        "cargo_id": req.cargo_id,
        "item_id": req.item_id,
        "requested_type": req.requested_type.value if hasattr(req.requested_type, 'value') else str(req.requested_type),
        "status": req.status.value if hasattr(req.status, 'value') else str(req.status),
        "applicant_id": req.applicant_id,
        "applicant_notes": req.applicant_notes,
        "target_market": req.target_market,
        "reviewer_id": req.reviewer_id,
        "reviewer_notes": req.reviewer_notes,
        "reviewed_at": str(req.reviewed_at) if req.reviewed_at else None,
        "created_at": str(req.created_at) if req.created_at else None,
        "updated_at": str(req.updated_at) if req.updated_at else None,
    }


def serialize_certificate(cert: Certificate) -> dict:
    return {
        "certificate_id": cert.certificate_id, "type": cert.type.value,
        "status": cert.status.value, "issuer_name": cert.issuer_name,
        "issuing_body": cert.issuing_body, "recipient_entity": cert.recipient_entity,
        "description": cert.description, "issued_date": str(cert.issued_date),
        "expiry_date": str(cert.expiry_date) if cert.expiry_date else None,
        "digital_signature": cert.digital_signature, "document_url": cert.document_url,
        "product_id": cert.product_id, "item_id": cert.item_id,
    }


async def notify_expiring_certificates(db: AsyncSession) -> dict:
    """Find certificates expiring within CERT_EXPIRY_NOTIFY_DAYS and send notifications."""
    now = datetime.now(timezone.utc)
    cutoff = now + timedelta(days=CERT_EXPIRY_NOTIFY_DAYS)

    rows = await db.execute(
        select(Certificate).where(
            Certificate.expiry_date.isnot(None),
            Certificate.expiry_date <= cutoff,
            Certificate.expiry_date > now,
            Certificate.status.in_([CertificateStatus.ISSUED, CertificateStatus.VERIFIED]),
        ).order_by(Certificate.expiry_date.asc())
    )
    certs = rows.scalars().all()

    notified = []
    for cert in certs:
        exp = cert.expiry_date
        if exp is not None and exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        days_left = (exp - now).days
        try:
            await send_notification(
                recipient="admin@foodtrack.local",
                subject=f"Certificate Expiring Soon: {cert.certificate_id}",
                message=(
                    f"Certificate {cert.certificate_id} ({cert.type.value}) "
                    f"issued by {cert.issuer_name} expires in {days_left} days "
                    f"on {exp.date()}. "
                    f"Please renew before expiry."
                ),
                channel="email",
            )
            notified.append({
                "certificate_id": cert.certificate_id,
                "type": cert.type.value,
                "expiry_date": str(exp.date()) if exp else None,
                "days_left": days_left,
            })
        except Exception:
            pass

    return {
        "checked_at": str(now),
        "total_expiring": len(certs),
        "notified_count": len(notified),
        "certificates": notified,
    }


async def auto_advance_cargo_on_cert_approval(db: AsyncSession, request_id: int) -> dict:
    """When a certificate request linked to cargo is approved, auto-advance cargo to CERTIFIED status."""
    req = await db.get(CertificateRequest, request_id)
    if not req:
        raise ValueError(f"CertificateRequest {request_id} not found")
    if req.status != CertificateRequestStatus.APPROVED:
        return {"advanced": False, "reason": f"Request status is {req.status.value}, not approved"}
    if not req.cargo_id:
        return {"advanced": False, "reason": "No cargo linked to this request"}

    from app.models.cargo import CargoRegistration, CargoStatus
    cargo = await db.get(CargoRegistration, req.cargo_id)
    if not cargo:
        raise ValueError(f"Cargo {req.cargo_id} not found")
    if cargo.status != CargoStatus.REGISTERED:
        return {"advanced": False, "reason": f"Cargo status is {cargo.status.value}, not REGISTERED"}

    cargo.status = CargoStatus.CERTIFIED
    await db.commit()
    await db.refresh(cargo)

    return {
        "advanced": True,
        "cargo_id": cargo.id,
        "previous_status": "registered",
        "new_status": "certified",
        "certificate_request_id": request_id,
    }
