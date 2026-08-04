"""Tests for certificate_service."""
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cargo import CargoRegistration, CargoStatus
from app.models.certificate import (
    CertificateRequestStatus,
    CertificateStatus,
    CertificateType,
)
from app.models.product import Product, ProductCategory
from app.models.taxonomy import Taxonomy, TaxonomyItem, TaxonomyNode
from app.services import certificate_service as cs


async def _make_item(db: AsyncSession, code: str = "CERT-ITEM") -> TaxonomyItem:
    t = Taxonomy(name=f"T-{uuid.uuid4().hex[:8]}")
    db.add(t)
    await db.commit()
    await db.refresh(t)
    n = TaxonomyNode(taxonomy_id=t.id, code="N", name="Node")
    db.add(n)
    await db.commit()
    await db.refresh(n)
    item = TaxonomyItem(node_id=n.id, code=code, common_name="Mango", scientific_name="M. indica")
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


async def _make_product(db: AsyncSession, item: TaxonomyItem, sku: str = "SKU-CERT") -> Product:
    p = Product(sku=sku, name="Mango Box", category=ProductCategory.FRESH_PRODUCE,
                item_id=item.id, producer_id=1, producer_name="Farm")
    db.add(p)
    await db.commit()
    await db.refresh(p)
    return p


async def test_issue_certificate_permissions(db, viewer_user, admin_user, taxonomy_item):
    with pytest.raises(PermissionError):
        await cs.issue_certificate(db, viewer_user, cert_type=CertificateType.HALAL)
    with pytest.raises(ValueError):
        await cs.issue_certificate(db, admin_user, cert_type=CertificateType.HALAL)
    with pytest.raises(ValueError):
        await cs.issue_certificate(db, admin_user, product_id=99999, cert_type=CertificateType.HALAL)
    with pytest.raises(ValueError):
        await cs.issue_certificate(db, admin_user, item_id=99999, cert_type=CertificateType.HALAL)
    with pytest.raises(ValueError):
        await cs.issue_certificate(db, admin_user, product_id=taxonomy_item.id, cert_type=CertificateType.HALAL)


async def test_issue_certificate_success(db, admin_user, taxonomy_item):
    cert = await cs.issue_certificate(
        db, admin_user, item_id=taxonomy_item.id, cert_type=CertificateType.HALAL,
        issuing_body="DMCC", recipient_entity="Acme", description="Halal ok",
        expiry_date="2030-01-15", document_url="https://docs/x.pdf",
    )
    assert cert.certificate_id.startswith("FT-")
    assert cert.status == CertificateStatus.ISSUED
    assert cert.issuer_id == admin_user.id
    assert cert.item_id == taxonomy_item.id
    assert cert.expiry_date.year == 2030


async def test_issue_certificate_with_product(db, admin_user, taxonomy_item):
    p = await _make_product(db, taxonomy_item)
    cert = await cs.issue_certificate(db, admin_user, product_id=p.id, cert_type=CertificateType.ORIGIN)
    assert cert.product_id == p.id


async def test_list_and_get_certificates(db, admin_user, taxonomy_item):
    c1 = await cs.issue_certificate(db, admin_user, item_id=taxonomy_item.id, cert_type=CertificateType.HALAL)
    c2 = await cs.issue_certificate(db, admin_user, item_id=taxonomy_item.id, cert_type=CertificateType.ORGANIC)
    all_certs = await cs.list_certificates(db)
    assert {c.certificate_id for c in all_certs} == {c1.certificate_id, c2.certificate_id}
    halal = await cs.list_certificates(db, cert_type=CertificateType.HALAL)
    assert [c.certificate_id for c in halal] == [c1.certificate_id]
    assert (await cs.get_certificate(db, c1.certificate_id)).id == c1.id
    assert await cs.get_certificate(db, "FT-NOPE") is None


async def test_verify_certificate(db, admin_user, taxonomy_item):
    cert = await cs.issue_certificate(db, admin_user, item_id=taxonomy_item.id, cert_type=CertificateType.HALAL)
    with pytest.raises(ValueError):
        await cs.verify_certificate(db, admin_user, "FT-NOPE")
    verified = await cs.verify_certificate(db, admin_user, cert.certificate_id)
    assert verified.status == CertificateStatus.VERIFIED
    assert verified.verified_by == admin_user.id
    with pytest.raises(ValueError):
        await cs.verify_certificate(db, admin_user, cert.certificate_id)


async def test_revoke_certificate(db, admin_user, viewer_user, taxonomy_item):
    cert = await cs.issue_certificate(db, admin_user, item_id=taxonomy_item.id, cert_type=CertificateType.HALAL)
    with pytest.raises(PermissionError):
        await cs.revoke_certificate(db, viewer_user, cert.certificate_id)
    with pytest.raises(ValueError):
        await cs.revoke_certificate(db, admin_user, "FT-NOPE")
    revoked = await cs.revoke_certificate(db, admin_user, cert.certificate_id)
    assert revoked.status == CertificateStatus.REVOKED


async def test_get_certificates_for_item(db, admin_user, taxonomy_item):
    await cs.issue_certificate(db, admin_user, item_id=taxonomy_item.id, cert_type=CertificateType.HALAL)
    out = await cs.get_certificates_for_item(db, taxonomy_item.id)
    assert len(out) == 1 and out[0]["type"] == "halal"
    assert await cs.get_certificates_for_item(db, 99999) == []


async def test_get_certificates_for_item_via_product(db, admin_user, taxonomy_item):
    p = await _make_product(db, taxonomy_item)
    await cs.issue_certificate(db, admin_user, product_id=p.id, cert_type=CertificateType.ORGANIC)
    out = await cs.get_certificates_for_item(db, taxonomy_item.id)
    assert len(out) == 1 and out[0]["type"] == "organic"


async def test_verify_certificate_chain(db, admin_user, taxonomy_item):
    with pytest.raises(ValueError):
        await cs.verify_certificate_chain(db, 99999)
    await cs.issue_certificate(db, admin_user, item_id=taxonomy_item.id, cert_type=CertificateType.HALAL,
                               expiry_date="2030-01-01")
    out = await cs.verify_certificate_chain(db, taxonomy_item.id)
    assert out["total_certificates"] == 1
    assert out["active_count"] == 1
    assert out["chain_valid"] is True
    assert out["item_name"] == "Test Item"


async def test_verify_certificate_chain_expired(db, admin_user, taxonomy_item):
    past = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
    cert = await cs.issue_certificate(db, admin_user, item_id=taxonomy_item.id,
                                      cert_type=CertificateType.HALAL, expiry_date=past)
    out = await cs.verify_certificate_chain(db, taxonomy_item.id)
    assert out["expired_in_chain"] == [cert.certificate_id]
    assert out["chain_valid"] is False


async def test_verify_certificate_chain_with_revoked(db, admin_user, taxonomy_item):
    cert = await cs.issue_certificate(db, admin_user, item_id=taxonomy_item.id, cert_type=CertificateType.HALAL)
    await cs.revoke_certificate(db, admin_user, cert.certificate_id)
    out = await cs.verify_certificate_chain(db, taxonomy_item.id)
    assert out["revoked_count"] == 1
    assert out["chain_valid"] is False


async def test_get_missing_certifications(db, admin_user, taxonomy_item):
    with pytest.raises(ValueError):
        await cs.get_missing_certifications(db, 99999)
    unknown = await cs.get_missing_certifications(db, taxonomy_item.id, "mars")
    assert unknown["message"] == "Unknown market profile"
    out = await cs.get_missing_certifications(db, taxonomy_item.id)
    assert out["total_required"] == 4
    assert "halal" in out["missing"]
    assert out["compliant"] is False
    await cs.issue_certificate(db, admin_user, item_id=taxonomy_item.id, cert_type=CertificateType.HALAL)
    after = await cs.get_missing_certifications(db, taxonomy_item.id)
    assert "halal" not in after["missing"]


async def test_request_certificate(db, admin_user, taxonomy_item):
    with pytest.raises(ValueError):
        await cs.request_certificate(db, admin_user, 99999, CertificateType.HALAL)
    req = await cs.request_certificate(
        db, admin_user, taxonomy_item.id, CertificateType.HALAL,
        applicant_notes="urgent", target_market="dubai_import",
    )
    assert req.status == CertificateRequestStatus.PENDING
    assert req.applicant_id == admin_user.id


async def test_list_and_get_certificate_requests(db, admin_user, taxonomy_item):
    r1 = await cs.request_certificate(db, admin_user, taxonomy_item.id, CertificateType.HALAL)
    r2 = await cs.request_certificate(db, admin_user, taxonomy_item.id, CertificateType.ORGANIC)
    reqs = await cs.list_certificate_requests(db)
    assert {r.id for r in reqs} == {r1.id, r2.id}
    pending = await cs.list_certificate_requests(db, status=CertificateRequestStatus.PENDING)
    assert len(pending) == 2
    mine = await cs.list_certificate_requests(db, applicant_id=admin_user.id)
    assert len(mine) == 2
    assert (await cs.get_certificate_request(db, r1.id)).id == r1.id


async def test_review_certificate_request(db, admin_user, viewer_user, taxonomy_item):
    req = await cs.request_certificate(db, admin_user, taxonomy_item.id, CertificateType.HALAL)
    with pytest.raises(PermissionError):
        await cs.review_certificate_request(db, viewer_user, req.id, CertificateRequestStatus.APPROVED)
    with pytest.raises(ValueError):
        await cs.review_certificate_request(db, admin_user, 99999, CertificateRequestStatus.APPROVED)
    approved = await cs.review_certificate_request(db, admin_user, req.id, CertificateRequestStatus.APPROVED,
                                                   reviewer_notes="looks good")
    assert approved.status == CertificateRequestStatus.APPROVED
    assert approved.reviewer_id == admin_user.id
    certs = await cs.list_certificates(db)
    assert len(certs) == 1 and certs[0].item_id == taxonomy_item.id


async def test_review_certificate_request_rejected_and_guards(db, admin_user, taxonomy_item):
    req = await cs.request_certificate(db, admin_user, taxonomy_item.id, CertificateType.HALAL)
    with pytest.raises(ValueError):
        await cs.review_certificate_request(db, admin_user, req.id, CertificateRequestStatus.CANCELLED)
    rejected = await cs.review_certificate_request(db, admin_user, req.id, CertificateRequestStatus.REJECTED)
    assert rejected.status == CertificateRequestStatus.REJECTED
    with pytest.raises(ValueError):
        await cs.review_certificate_request(db, admin_user, req.id, CertificateRequestStatus.APPROVED)


async def test_serializers(db, admin_user, taxonomy_item):
    cert = await cs.issue_certificate(db, admin_user, item_id=taxonomy_item.id, cert_type=CertificateType.HALAL)
    s = cs.serialize_certificate(cert)
    assert s["type"] == "halal" and s["status"] == "issued"
    req = await cs.request_certificate(db, admin_user, taxonomy_item.id, CertificateType.ORGANIC)
    sr = cs.serialize_certificate_request(req)
    assert sr["requested_type"] == "organic" and sr["status"] == "pending"


async def test_notify_expiring_certificates(db, admin_user, taxonomy_item, monkeypatch):
    notified = []
    async def fake_send_notification(recipient, subject, message, channel):
        notified.append((recipient, subject))
    monkeypatch.setattr("app.services.certificate_service.send_notification", fake_send_notification)
    soon = (datetime.now(timezone.utc) + timedelta(days=10)).isoformat()
    far = (datetime.now(timezone.utc) + timedelta(days=300)).isoformat()
    await cs.issue_certificate(db, admin_user, item_id=taxonomy_item.id, cert_type=CertificateType.HALAL,
                               expiry_date=soon)
    await cs.issue_certificate(db, admin_user, item_id=taxonomy_item.id, cert_type=CertificateType.ORGANIC,
                               expiry_date=far)
    out = await cs.notify_expiring_certificates(db)
    assert out["total_expiring"] == 1
    assert out["notified_count"] == 1
    assert len(notified) == 1
    assert "admin@foodtrack.local" in notified[0]


async def test_auto_advance_cargo(db, admin_user, taxonomy_item):
    with pytest.raises(ValueError):
        await cs.auto_advance_cargo_on_cert_approval(db, 99999)
    req = await cs.request_certificate(db, admin_user, taxonomy_item.id, CertificateType.HALAL)
    no_approve = await cs.auto_advance_cargo_on_cert_approval(db, req.id)
    assert no_approve["advanced"] is False
    cargo = CargoRegistration(item_id=taxonomy_item.id, quantity=100, unit="kg",
                              status=CargoStatus.REGISTERED, created_by=admin_user.id)
    db.add(cargo)
    await db.commit()
    await db.refresh(cargo)
    req.cargo_id = cargo.id
    await db.commit()
    no_cargo_link = await cs.auto_advance_cargo_on_cert_approval(db, req.id)
    assert no_cargo_link["advanced"] is False
    await cs.review_certificate_request(db, admin_user, req.id, CertificateRequestStatus.APPROVED)
    ok = await cs.auto_advance_cargo_on_cert_approval(db, req.id)
    assert ok["advanced"] is True
    assert ok["new_status"] == "certified"
    again = await cs.auto_advance_cargo_on_cert_approval(db, req.id)
    assert again["advanced"] is False
