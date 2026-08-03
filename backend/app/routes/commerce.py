"""Commerce & Bulking Pipeline API routes.

Exposes the buyer aggregation workflow: appointment bookings, bulking registers
(contacts + bids), warehouse bookings, courier jobs, deal closing with credential
exchange, settlements and multi-provider payments.
"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.commerce import (
    AppointmentStatus, RegisterStatus, SourcingMode,
    ContactType, BidStatus, WarehouseBookingStatus, CourierJobStatus,
    DealStatus, PaymentMethod, BulkingJobRole, BulkingJobStatus, PackingStatus,
)
from app.services.commerce_service import (
    book_appointment, list_appointments, update_appointment_status,
    create_bulking_register, get_register_detail, list_registers,
    update_register_status, add_contact, list_contacts,
    submit_bid, list_bids, accept_bid, reject_bid,
    book_warehouse, list_warehouse_bookings, update_warehouse_booking_status,
    post_courier_job, list_courier_jobs, update_courier_job_status,
    close_deal, list_deals, exchange_credentials,
    calculate_settlements, list_settlements, mark_settlement_paid,
    initiate_payment, confirm_payment, list_payments, list_payment_methods,
    get_business_dashboard,
    get_escrow_requirement, deposit_escrow, get_pipeline_trace,
    list_job_candidates, create_job_assignment, list_job_assignments,
    update_job_assignment_status,
    create_packing_record, list_packing_records, update_packing_status,
)
from app.utils.dependencies import get_current_user

router = APIRouter(prefix="/commerce", tags=["commerce"])


def _raise(e: Exception):
    raise HTTPException(status_code=400 if isinstance(e, ValueError) else 403, detail=str(e))


# ── Appointments ───────────────────────────────────────────────────────────

class AppointmentCreate(BaseModel):
    participant_name: str
    scheduled_at: datetime
    participant_type: str | None = None
    participant_phone: str | None = None
    participant_email: str | None = None
    purpose: str | None = None
    duration_minutes: int = 60
    channel: str | None = None
    location: str | None = None
    notes: str | None = None


class AppointmentStatusUpdate(BaseModel):
    status: AppointmentStatus


@router.post("/appointments")
async def api_book_appointment(
    req: AppointmentCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        appointment = await book_appointment(
            db, user, req.participant_name, req.scheduled_at,
            participant_type=req.participant_type,
            participant_phone=req.participant_phone,
            participant_email=req.participant_email,
            purpose=req.purpose, duration_minutes=req.duration_minutes,
            channel=req.channel, location=req.location, notes=req.notes,
        )
    except (ValueError, PermissionError) as e:
        _raise(e)
    return {"id": appointment.id, "status": appointment.status.value}


@router.get("/appointments")
async def api_list_appointments(
    page: int = Query(1, ge=1),
    upcoming_only: bool = Query(False),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await list_appointments(db, user, page=page, upcoming_only=upcoming_only)


@router.patch("/appointments/{appointment_id}/status")
async def api_update_appointment_status(
    appointment_id: int,
    req: AppointmentStatusUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        appointment = await update_appointment_status(db, user, appointment_id, req.status)
    except (ValueError, PermissionError) as e:
        _raise(e)
    return {"id": appointment.id, "status": appointment.status.value}


# ── Bulking registers ──────────────────────────────────────────────────────

class RegisterCreate(BaseModel):
    item_id: int
    target_quantity: float
    title: str | None = None
    unit: str | None = None
    target_price: float | None = None
    currency: str = "USD"
    region: str | None = None
    sourcing_mode: SourcingMode = SourcingMode.SELF
    auto_generate: bool = False
    sourcing_entity_id: int | None = None
    sourcing_entity_name: str | None = None
    notes: str | None = None


class RegisterStatusUpdate(BaseModel):
    status: RegisterStatus


@router.post("/registers")
async def api_create_register(
    req: RegisterCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        register = await create_bulking_register(
            db, user, req.item_id, req.target_quantity,
            title=req.title, unit=req.unit, target_price=req.target_price,
            currency=req.currency, region=req.region,
            sourcing_mode=req.sourcing_mode, auto_generate=req.auto_generate,
            sourcing_entity_id=req.sourcing_entity_id,
            sourcing_entity_name=req.sourcing_entity_name,
            notes=req.notes,
        )
    except (ValueError, PermissionError) as e:
        _raise(e)
    return {"id": register.id, "register_number": register.register_number, "status": register.status.value}


@router.get("/registers")
async def api_list_registers(
    page: int = Query(1, ge=1),
    status: str | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await list_registers(db, user, page=page, status=status)


@router.get("/registers/{register_id}")
async def api_get_register(
    register_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await get_register_detail(db, user, register_id)
    except PermissionError as e:
        _raise(e)
    if not result:
        raise HTTPException(status_code=404, detail="Register not found")
    return result


@router.patch("/registers/{register_id}/status")
async def api_update_register_status(
    register_id: int,
    req: RegisterStatusUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        register = await update_register_status(db, user, register_id, req.status)
    except (ValueError, PermissionError) as e:
        _raise(e)
    return {"id": register.id, "status": register.status.value}


# ── Escrow & pipeline trace ─────────────────────────────────────────────────

class EscrowDeposit(BaseModel):
    method: PaymentMethod = PaymentMethod.BANK_TRANSFER


@router.get("/registers/{register_id}/escrow")
async def api_get_escrow_requirement(
    register_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await get_escrow_requirement(db, user, register_id)
    except (ValueError, PermissionError) as e:
        _raise(e)


@router.post("/registers/{register_id}/escrow/deposit")
async def api_deposit_escrow(
    register_id: int,
    req: EscrowDeposit,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        escrow = await deposit_escrow(db, user, register_id, method=req.method)
    except (ValueError, PermissionError) as e:
        _raise(e)
    return {
        "id": escrow.id,
        "percentage": float(escrow.percentage),
        "amount": float(escrow.amount),
        "currency": escrow.currency or "USD",
        "status": escrow.status.value,
        "payment_id": escrow.payment_id,
    }


@router.get("/registers/{register_id}/pipeline")
async def api_get_pipeline_trace(
    register_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await get_pipeline_trace(db, user, register_id)
    except (ValueError, PermissionError) as e:
        _raise(e)


# ── Contacts ───────────────────────────────────────────────────────────────

class ContactCreate(BaseModel):
    name: str
    contact_type: ContactType = ContactType.FARMER
    phone: str | None = None
    email: str | None = None
    location: str | None = None
    is_primary: bool = False
    notes: str | None = None


@router.post("/registers/{register_id}/contacts")
async def api_add_contact(
    register_id: int,
    req: ContactCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        contact = await add_contact(
            db, user, register_id, req.name,
            contact_type=req.contact_type, phone=req.phone, email=req.email,
            location=req.location, is_primary=req.is_primary, notes=req.notes,
        )
    except (ValueError, PermissionError) as e:
        _raise(e)
    return {"id": contact.id}


@router.get("/registers/{register_id}/contacts")
async def api_list_contacts(
    register_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await list_contacts(db, user, register_id)
    except (ValueError, PermissionError) as e:
        _raise(e)


# ── Bids ───────────────────────────────────────────────────────────────────

class BidCreate(BaseModel):
    quantity: float
    unit_price: float
    contact_id: int | None = None
    item_id: int | None = None
    unit: str | None = None
    currency: str = "USD"
    quality_grade: str | None = None
    notes: str | None = None


@router.post("/registers/{register_id}/bids")
async def api_submit_bid(
    register_id: int,
    req: BidCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        bid = await submit_bid(
            db, user, register_id, req.quantity, req.unit_price,
            contact_id=req.contact_id, item_id=req.item_id,
            unit=req.unit, currency=req.currency,
            quality_grade=req.quality_grade, notes=req.notes,
        )
    except (ValueError, PermissionError) as e:
        _raise(e)
    return {"id": bid.id, "status": bid.status.value}


@router.get("/registers/{register_id}/bids")
async def api_list_bids(
    register_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await list_bids(db, user, register_id)
    except (ValueError, PermissionError) as e:
        _raise(e)


@router.post("/bids/{bid_id}/accept")
async def api_accept_bid(
    bid_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        bid = await accept_bid(db, user, bid_id)
    except (ValueError, PermissionError) as e:
        _raise(e)
    return {"id": bid.id, "status": bid.status.value}


@router.post("/bids/{bid_id}/reject")
async def api_reject_bid(
    bid_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        bid = await reject_bid(db, user, bid_id)
    except (ValueError, PermissionError) as e:
        _raise(e)
    return {"id": bid.id, "status": bid.status.value}


# ── Warehousing ────────────────────────────────────────────────────────────

class WarehouseBookingCreate(BaseModel):
    warehouse_id: int
    start_date: datetime | None = None
    end_date: datetime | None = None
    quantity: float | None = None
    unit: str | None = None
    storage_cost: float | None = None
    currency: str = "USD"
    notes: str | None = None


class WarehouseBookingStatusUpdate(BaseModel):
    status: WarehouseBookingStatus


@router.post("/registers/{register_id}/warehouse-bookings")
async def api_book_warehouse(
    register_id: int,
    req: WarehouseBookingCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        booking = await book_warehouse(
            db, user, register_id, req.warehouse_id,
            start_date=req.start_date, end_date=req.end_date,
            quantity=req.quantity, unit=req.unit,
            storage_cost=req.storage_cost, currency=req.currency, notes=req.notes,
        )
    except (ValueError, PermissionError) as e:
        _raise(e)
    return {"id": booking.id, "status": booking.status.value}


@router.get("/registers/{register_id}/warehouse-bookings")
async def api_list_warehouse_bookings(
    register_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await list_warehouse_bookings(db, user, register_id)
    except (ValueError, PermissionError) as e:
        _raise(e)


@router.patch("/warehouse-bookings/{booking_id}/status")
async def api_update_warehouse_booking_status(
    booking_id: int,
    req: WarehouseBookingStatusUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        booking = await update_warehouse_booking_status(db, user, booking_id, req.status)
    except (ValueError, PermissionError) as e:
        _raise(e)
    return {"id": booking.id, "status": booking.status.value}


# ── Courier jobs ───────────────────────────────────────────────────────────

class CourierJobCreate(BaseModel):
    pickup_location: str
    item_id: int | None = None
    dropoff_warehouse_id: int | None = None
    quantity: float | None = None
    unit: str | None = None
    weight_kg: float | None = None
    budget: float | None = None
    currency: str = "USD"
    courier_name: str | None = None
    deliver_to_buyer: bool = False


class CourierJobStatusUpdate(BaseModel):
    status: CourierJobStatus


@router.post("/registers/{register_id}/courier-jobs")
async def api_post_courier_job(
    register_id: int,
    req: CourierJobCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        job = await post_courier_job(
            db, user, register_id, req.pickup_location,
            item_id=req.item_id, dropoff_warehouse_id=req.dropoff_warehouse_id,
            quantity=req.quantity, unit=req.unit, weight_kg=req.weight_kg,
            budget=req.budget, currency=req.currency, courier_name=req.courier_name,
            deliver_to_buyer=req.deliver_to_buyer,
        )
    except (ValueError, PermissionError) as e:
        _raise(e)
    return {"id": job.id, "tracking_code": job.tracking_code, "status": job.status.value}


@router.get("/registers/{register_id}/courier-jobs")
async def api_list_courier_jobs(
    register_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await list_courier_jobs(db, user, register_id)
    except (ValueError, PermissionError) as e:
        _raise(e)


@router.patch("/courier-jobs/{job_id}/status")
async def api_update_courier_job_status(
    job_id: int,
    req: CourierJobStatusUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        job = await update_courier_job_status(db, user, job_id, req.status)
    except (ValueError, PermissionError) as e:
        _raise(e)
    return {"id": job.id, "status": job.status.value}


# ── Deals & credential exchange ────────────────────────────────────────────

class DealCreate(BaseModel):
    quantity: float
    unit_price: float
    seller_contact_id: int | None = None
    item_id: int | None = None
    unit: str | None = None
    currency: str = "USD"


@router.post("/registers/{register_id}/deals")
async def api_close_deal(
    register_id: int,
    req: DealCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await close_deal(
            db, user, register_id, req.quantity, req.unit_price,
            seller_contact_id=req.seller_contact_id, item_id=req.item_id,
            unit=req.unit, currency=req.currency,
        )
    except (ValueError, PermissionError) as e:
        _raise(e)
    return result


@router.get("/deals")
async def api_list_deals(
    page: int = Query(1, ge=1),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await list_deals(db, user, page=page)


@router.post("/deals/{deal_id}/exchange-credentials")
async def api_exchange_credentials(
    deal_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await exchange_credentials(db, user, deal_id)
    except (ValueError, PermissionError) as e:
        _raise(e)


# ── Settlement ─────────────────────────────────────────────────────────────

@router.post("/registers/{register_id}/settlements/calculate")
async def api_calculate_settlements(
    register_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await calculate_settlements(db, user, register_id)
    except (ValueError, PermissionError) as e:
        _raise(e)


@router.get("/registers/{register_id}/settlements")
async def api_list_settlements(
    register_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await list_settlements(db, user, register_id)
    except (ValueError, PermissionError) as e:
        _raise(e)


class MarkSettlementPaid(BaseModel):
    payment_id: int | None = None


@router.patch("/settlements/{settlement_id}/mark-paid")
async def api_mark_settlement_paid(
    settlement_id: int,
    req: MarkSettlementPaid,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        settlement = await mark_settlement_paid(db, user, settlement_id, payment_id=req.payment_id)
    except (ValueError, PermissionError) as e:
        _raise(e)
    return {"id": settlement.id, "status": settlement.status.value}


# ── Payments ───────────────────────────────────────────────────────────────

class PaymentCreate(BaseModel):
    amount: float
    currency: str = "USD"
    method: PaymentMethod
    register_id: int | None = None
    deal_id: int | None = None
    payee_id: int | None = None
    provider_reference: str | None = None


@router.post("/payments")
async def api_initiate_payment(
    req: PaymentCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        payment = await initiate_payment(
            db, user, req.amount, req.currency, req.method,
            register_id=req.register_id, deal_id=req.deal_id,
            payee_id=req.payee_id, provider_reference=req.provider_reference,
        )
    except (ValueError, PermissionError) as e:
        _raise(e)
    return {"id": payment.id, "provider_reference": payment.provider_reference, "status": payment.status.value}


@router.post("/payments/{payment_id}/confirm")
async def api_confirm_payment(
    payment_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        payment = await confirm_payment(db, user, payment_id)
    except (ValueError, PermissionError) as e:
        _raise(e)
    return {"id": payment.id, "status": payment.status.value}


@router.get("/payments")
async def api_list_payments(
    page: int = Query(1, ge=1),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await list_payments(db, user, page=page)


@router.get("/payment-methods")
async def api_payment_methods(
    user: User = Depends(get_current_user),
):
    return {"methods": list_payment_methods()}


# ── Pipeline jobs (Clerks, Verifiers, Couriers) ────────────────────────────

class JobAssignmentCreate(BaseModel):
    role: BulkingJobRole
    assignee_id: int | None = None
    assignee_name: str | None = None
    assignee_location: str | None = None
    notes: str | None = None


class JobAssignmentStatusUpdate(BaseModel):
    status: BulkingJobStatus


@router.get("/registers/{register_id}/job-candidates")
async def api_list_job_candidates(
    register_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        return {"candidates": await list_job_candidates(db, user, register_id)}
    except (ValueError, PermissionError) as e:
        _raise(e)


@router.post("/registers/{register_id}/job-assignments")
async def api_create_job_assignment(
    register_id: int,
    req: JobAssignmentCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        assignment = await create_job_assignment(
            db, user, register_id, req.role,
            assignee_id=req.assignee_id, assignee_name=req.assignee_name,
            assignee_location=req.assignee_location, notes=req.notes,
        )
    except (ValueError, PermissionError) as e:
        _raise(e)
    return {"id": assignment.id, "role": assignment.role.value, "status": assignment.status.value}


@router.get("/registers/{register_id}/job-assignments")
async def api_list_job_assignments(
    register_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        return {"job_assignments": await list_job_assignments(db, user, register_id)}
    except (ValueError, PermissionError) as e:
        _raise(e)


@router.patch("/job-assignments/{assignment_id}/status")
async def api_update_job_assignment_status(
    assignment_id: int,
    req: JobAssignmentStatusUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        assignment = await update_job_assignment_status(db, user, assignment_id, req.status)
    except (ValueError, PermissionError) as e:
        _raise(e)
    return {"id": assignment.id, "status": assignment.status.value}


# ── Packing & certification ────────────────────────────────────────────────

class PackingRecordCreate(BaseModel):
    quantity: float
    unit: str | None = None
    package_type: str | None = None
    package_count: int | None = None
    total_weight_kg: float | None = None
    certificate_id: str | None = None
    packed_by_id: int | None = None
    notes: str | None = None


class PackingStatusUpdate(BaseModel):
    status: PackingStatus
    certificate_id: str | None = None


@router.post("/registers/{register_id}/packing-records")
async def api_create_packing_record(
    register_id: int,
    req: PackingRecordCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        record = await create_packing_record(
            db, user, register_id, req.quantity,
            unit=req.unit, package_type=req.package_type,
            package_count=req.package_count, total_weight_kg=req.total_weight_kg,
            certificate_id=req.certificate_id, packed_by_id=req.packed_by_id,
            notes=req.notes,
        )
    except (ValueError, PermissionError) as e:
        _raise(e)
    return {"id": record.id, "status": record.status.value}


@router.get("/registers/{register_id}/packing-records")
async def api_list_packing_records(
    register_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        return {"packing_records": await list_packing_records(db, user, register_id)}
    except (ValueError, PermissionError) as e:
        _raise(e)


@router.patch("/packing-records/{packing_id}/status")
async def api_update_packing_status(
    packing_id: int,
    req: PackingStatusUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        record = await update_packing_status(db, user, packing_id, req.status, certificate_id=req.certificate_id)
    except (ValueError, PermissionError) as e:
        _raise(e)
    return {"id": record.id, "status": record.status.value}


# ── Business dashboard ─────────────────────────────────────────────────────

@router.get("/dashboard")
async def api_business_dashboard(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_business_dashboard(db, user)
