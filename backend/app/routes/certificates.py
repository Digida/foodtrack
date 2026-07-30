from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.database import get_db
from app.models.user import User
from app.models.certificate import CertificateType, CertificateStatus, CertificateRequestStatus
from app.services.certificate_service import (
    issue_certificate, list_certificates, get_certificate,
    verify_certificate, revoke_certificate, serialize_certificate,
    get_certificates_for_item, verify_certificate_chain, get_missing_certifications,
    request_certificate, list_certificate_requests, get_certificate_request,
    review_certificate_request, serialize_certificate_request,
    notify_expiring_certificates, auto_advance_cargo_on_cert_approval,
)
from app.utils.dependencies import get_current_user

router = APIRouter(prefix="/certificates", tags=["certificates"])


class CertificateCreateRequest(BaseModel):
    product_id: int
    type: CertificateType
    issuing_body: str | None = None
    recipient_entity: str | None = None
    description: str | None = None
    expiry_date: str | None = None
    document_url: str | None = None
    metadata_json: str | None = None


@router.post("")
async def api_issue_certificate(req: CertificateCreateRequest, user: User = Depends(get_current_user),
                                 db: AsyncSession = Depends(get_db)):
    try:
        cert = await issue_certificate(
            db, user, req.product_id, req.type, req.issuing_body,
            req.recipient_entity, req.description, req.expiry_date,
            req.document_url, req.metadata_json,
        )
        return {"certificate": serialize_certificate(cert)}
    except (ValueError, PermissionError) as e:
        raise HTTPException(status_code=404 if isinstance(e, ValueError) else 403, detail=str(e))


@router.get("")
async def api_list_certificates(
    status: CertificateStatus | None = None,
    type: CertificateType | None = None,
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    certs = await list_certificates(db, status, type)
    return {"certificates": [serialize_certificate(c) for c in certs]}


@router.get("/{certificate_id}")
async def api_get_certificate(certificate_id: str, db: AsyncSession = Depends(get_db)):
    cert = await get_certificate(db, certificate_id)
    if not cert:
        raise HTTPException(status_code=404, detail="Certificate not found")
    return serialize_certificate(cert)


@router.post("/{certificate_id}/verify-auth")
async def api_verify_certificate(certificate_id: str, user: User = Depends(get_current_user),
                                  db: AsyncSession = Depends(get_db)):
    try:
        cert = await verify_certificate(db, user, certificate_id)
        return {"status": "verified", "certificate_id": certificate_id}
    except (ValueError, PermissionError) as e:
        raise HTTPException(status_code=400 if isinstance(e, ValueError) else 403, detail=str(e))


@router.post("/{certificate_id}/revoke")
async def api_revoke_certificate(certificate_id: str, user: User = Depends(get_current_user),
                                  db: AsyncSession = Depends(get_db)):
    try:
        cert = await revoke_certificate(db, user, certificate_id)
        return {"status": "revoked"}
    except (ValueError, PermissionError) as e:
        raise HTTPException(status_code=404 if isinstance(e, ValueError) else 403, detail=str(e))


@router.get("/by-item/{item_id}")
async def api_certificates_by_item(
    item_id: int,
    db: AsyncSession = Depends(get_db),
):
    certs = await get_certificates_for_item(db, item_id)
    return {"item_id": item_id, "certificates": certs}


@router.get("/verify-chain/{item_id}")
async def api_verify_certificate_chain(
    item_id: int,
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await verify_certificate_chain(db, item_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/missing/{item_id}")
async def api_missing_certifications(
    item_id: int,
    target_market: str = "dubai_import",
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await get_missing_certifications(db, item_id, target_market)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


class CertificateRequestCreate(BaseModel):
    item_id: int
    requested_type: CertificateType
    cargo_id: int | None = None
    applicant_notes: str | None = None
    target_market: str | None = None


class CertificateRequestReview(BaseModel):
    decision: CertificateRequestStatus
    reviewer_notes: str | None = None


@router.post("/requests")
async def api_request_certificate(
    req: CertificateRequestCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        cr = await request_certificate(
            db, user, req.item_id, req.requested_type,
            cargo_id=req.cargo_id, applicant_notes=req.applicant_notes,
            target_market=req.target_market,
        )
        return {"certificate_request": serialize_certificate_request(cr)}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/requests")
async def api_list_requests(
    status: CertificateRequestStatus | None = None,
    applicant_id: int | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    requests = await list_certificate_requests(db, status, applicant_id)
    return {"certificate_requests": [serialize_certificate_request(r) for r in requests]}


@router.get("/requests/{request_id}")
async def api_get_request(
    request_id: int,
    db: AsyncSession = Depends(get_db),
):
    cr = await get_certificate_request(db, request_id)
    if not cr:
        raise HTTPException(status_code=404, detail="Certificate request not found")
    return {"certificate_request": serialize_certificate_request(cr)}


@router.post("/requests/{request_id}/review")
async def api_review_request(
    request_id: int,
    req: CertificateRequestReview,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        cr = await review_certificate_request(db, user, request_id, req.decision, req.reviewer_notes)

        # Auto-advance linked cargo to CERTIFIED when request is approved
        advance_result = None
        if req.decision == CertificateRequestStatus.APPROVED:
            try:
                advance_result = await auto_advance_cargo_on_cert_approval(db, request_id)
            except (ValueError, Exception):
                pass

        return {
            "certificate_request": serialize_certificate_request(cr),
            "cargo_auto_advance": advance_result,
        }
    except (ValueError, PermissionError) as e:
        raise HTTPException(status_code=400 if isinstance(e, ValueError) else 403, detail=str(e))


@router.post("/notify-expiring")
async def api_notify_expiring(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await notify_expiring_certificates(db)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
