"""Commerce & Bulking Pipeline service layer.

Implements the buyer aggregation workflow end-to-end:

1. Appointment bookings (buyer <-> farmer / cooperative / aggregator)
2. Bulking registers: contacts, bids, and buying an item from many farmers
3. Auto-aggregation ("our aggregating functionality") that generates a register
   populated with contacts and bids
4. Warehouse bookings for the aggregated stock
5. Courier jobs posted to move stock from pickup points to warehouses
6. Deal closing with credential (email) exchange between buyer and seller
7. Settlement calculation (gross - platform fee = net) per seller
8. Multi-provider payments (Stripe, MPesa, Airtel Money, MTN MoMo, Visa,
   Mastercard, bank transfer, cash) that settle sellers

All domain queries are scoped to the acting user unless the user is an admin.
"""
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
import random
import string

from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.user import User, UserRole
from app.models.taxonomy import TaxonomyItem, ItemSupplyBand
from app.models.tracking import Warehouse
from app.models.certificate import Certificate
from app.models.commerce import (
    Appointment, AppointmentStatus,
    BulkingRegister, RegisterStatus, SourcingMode,
    BulkingContact, ContactType,
    BulkingBid, BidStatus,
    WarehouseBooking, WarehouseBookingStatus,
    CourierJob, CourierJobStatus,
    Deal, DealStatus,
    Payment, PaymentMethod, PaymentStatus,
    Settlement, SettlementStatus,
    BulkingJobAssignment, BulkingJobRole, BulkingJobStatus,
    PackingRecord, PackingStatus,
    BulkingEscrow, EscrowStatus,
)

PAGE_SIZE = 20
PLATFORM_FEE_RATE = 0.025  # 2.5% platform fee on gross settlement
PLATFORM_FEE_DECIMAL = Decimal("0.025")
HUNDREDTH = Decimal("0.01")
# Investor escrow: buyers deposit a share of the deal value up front before the
# pipeline runs. Abundant items require 30%, rare items require 65%.
ESCROW_PCT_ABUNDANT = Decimal("0.30")
ESCROW_PCT_RARE = Decimal("0.65")


def _money(value) -> Decimal:
    """Coerce money values to Decimal to avoid float/Decimal mixed arithmetic."""
    return value if isinstance(value, Decimal) else Decimal(str(value))


def _round_money(value) -> Decimal:
    return _money(value).quantize(HUNDREDTH, rounding=ROUND_HALF_UP)


def escrow_percentage_for(item: TaxonomyItem | None) -> Decimal:
    """30% deposit for abundant items, 65% for rare items."""
    band = None
    if item is not None:
        band = item.supply_band
        if hasattr(band, "value"):
            band = band.value
    if band == ItemSupplyBand.RARE.value:
        return ESCROW_PCT_RARE
    return ESCROW_PCT_ABUNDANT


def _escrow_basis(register: BulkingRegister, deals: list, bids: list) -> Decimal:
    """The deal value an investor's escrow is calculated against: closed deals
    when present, otherwise accepted bid volume x price, otherwise the register
    target price x target quantity."""
    if deals:
        return sum((_money(d.total_value) for d in deals), Decimal("0"))
    accepted = [b for b in bids if b.status == BidStatus.ACCEPTED]
    if accepted:
        return sum((_money(b.quantity) * _money(b.unit_price) for b in accepted), Decimal("0"))
    return _round_money(_money(register.target_price or 0) * _money(register.target_quantity))


def _escrow_out(register: BulkingRegister, item: TaxonomyItem | None, deals: list, bids: list, escrows: list) -> dict:
    """Summary of the register's escrow requirement and latest deposit state."""
    band = None
    if item is not None:
        band = item.supply_band
        if hasattr(band, "value"):
            band = band.value
    pct = escrow_percentage_for(item)
    basis = _escrow_basis(register, deals, bids)
    latest = escrows[-1] if escrows else None
    status = None
    deposited_at = released_at = None
    deposited_amount = Decimal("0")
    if latest is not None:
        status = latest.status.value if hasattr(latest.status, "value") else str(latest.status)
        deposited_at = str(latest.deposited_at) if latest.deposited_at else None
        released_at = str(latest.released_at) if latest.released_at else None
        deposited_amount = _money(latest.amount)
    if status is None:
        status = EscrowStatus.REQUIRED.value
    return {
        "supply_band": band or ItemSupplyBand.ABUNDANT.value,
        "escrow_percentage": float(pct * 100),
        "basis_amount": float(basis),
        "required_amount": float(_round_money(basis * pct)),
        "currency": register.currency or "USD",
        "status": status,
        "deposited_amount": float(deposited_amount),
        "deposited_at": deposited_at,
        "released_at": released_at,
    }


def _escrow_record_out(e: BulkingEscrow) -> dict:
    return {
        "id": e.id,
        "register_id": e.register_id,
        "item_id": e.item_id,
        "payer_id": e.payer_id,
        "percentage": float(e.percentage),
        "amount": float(e.amount),
        "currency": e.currency or "USD",
        "status": e.status.value if hasattr(e.status, "value") else str(e.status),
        "payment_id": e.payment_id,
        "deposited_at": str(e.deposited_at) if e.deposited_at else None,
        "released_at": str(e.released_at) if e.released_at else None,
        "created_at": str(e.created_at) if e.created_at else None,
    }

SUPPORTED_PAYMENT_METHODS = [
    {
        "method": PaymentMethod.STRIPE.value,
        "name": "Stripe",
        "type": "card",
        "countries": ["global"],
    },
    {
        "method": PaymentMethod.MPESA.value,
        "name": "M-Pesa",
        "type": "mobile_money",
        "countries": ["KE", "TZ"],
    },
    {
        "method": PaymentMethod.AIRTEL_MONEY.value,
        "name": "Airtel Money",
        "type": "mobile_money",
        "countries": ["UG", "RW", "TZ", "MW", "KE"],
    },
    {
        "method": PaymentMethod.MTN_MOMO.value,
        "name": "MTN MoMo",
        "type": "mobile_money",
        "countries": ["UG", "GH", "CM", "NG"],
    },
    {
        "method": PaymentMethod.VISA.value,
        "name": "Visa",
        "type": "card",
        "countries": ["global"],
    },
    {
        "method": PaymentMethod.MASTERCARD.value,
        "name": "Mastercard",
        "type": "card",
        "countries": ["global"],
    },
    {
        "method": PaymentMethod.BANK_TRANSFER.value,
        "name": "Bank Transfer",
        "type": "bank",
        "countries": ["global"],
    },
    {
        "method": PaymentMethod.CASH.value,
        "name": "Cash on Delivery",
        "type": "cash",
        "countries": ["global"],
    },
]


# ── Helpers ────────────────────────────────────────────────────────────────

def _can_buy(user: User) -> bool:
    return user.role in (UserRole.SUPERUSER, UserRole.ADMIN, UserRole.ENTERPRISE)


def _is_admin(user: User) -> bool:
    return user.role in (UserRole.SUPERUSER, UserRole.ADMIN)


_REGISTER_TRANSITIONS: dict[RegisterStatus, set[RegisterStatus]] = {
    RegisterStatus.DRAFT: {RegisterStatus.SOURCING, RegisterStatus.AGGREGATED, RegisterStatus.CLOSED, RegisterStatus.CANCELLED},
    RegisterStatus.SOURCING: {RegisterStatus.AGGREGATED, RegisterStatus.CLOSED, RegisterStatus.CANCELLED},
    RegisterStatus.AGGREGATED: {RegisterStatus.CLOSED, RegisterStatus.CANCELLED},
    RegisterStatus.CLOSED: set(),
    RegisterStatus.CANCELLED: set(),
}

_APPOINTMENT_TRANSITIONS: dict[AppointmentStatus, set[AppointmentStatus]] = {
    AppointmentStatus.REQUESTED: {AppointmentStatus.CONFIRMED, AppointmentStatus.CANCELLED},
    AppointmentStatus.CONFIRMED: {AppointmentStatus.COMPLETED, AppointmentStatus.CANCELLED},
    AppointmentStatus.COMPLETED: set(),
    AppointmentStatus.CANCELLED: set(),
}

_BID_TRANSITIONS: dict[BidStatus, set[BidStatus]] = {
    BidStatus.PENDING: {BidStatus.ACCEPTED, BidStatus.REJECTED, BidStatus.WITHDRAWN},
    BidStatus.ACCEPTED: set(),
    BidStatus.REJECTED: set(),
    BidStatus.WITHDRAWN: set(),
}

_BOOKING_TRANSITIONS: dict[WarehouseBookingStatus, set[WarehouseBookingStatus]] = {
    WarehouseBookingStatus.REQUESTED: {WarehouseBookingStatus.CONFIRMED, WarehouseBookingStatus.CANCELLED},
    WarehouseBookingStatus.CONFIRMED: {WarehouseBookingStatus.IN_USE, WarehouseBookingStatus.COMPLETED, WarehouseBookingStatus.CANCELLED},
    WarehouseBookingStatus.IN_USE: {WarehouseBookingStatus.COMPLETED, WarehouseBookingStatus.CANCELLED},
    WarehouseBookingStatus.COMPLETED: set(),
    WarehouseBookingStatus.CANCELLED: set(),
}

_COURIER_TRANSITIONS: dict[CourierJobStatus, set[CourierJobStatus]] = {
    CourierJobStatus.POSTED: {CourierJobStatus.ASSIGNED, CourierJobStatus.CANCELLED},
    CourierJobStatus.ASSIGNED: {CourierJobStatus.IN_TRANSIT, CourierJobStatus.CANCELLED},
    CourierJobStatus.IN_TRANSIT: {CourierJobStatus.DELIVERED, CourierJobStatus.CANCELLED},
    CourierJobStatus.DELIVERED: set(),
    CourierJobStatus.CANCELLED: set(),
}

_PAYMENT_TRANSITIONS: dict[PaymentStatus, set[PaymentStatus]] = {
    PaymentStatus.PENDING: {PaymentStatus.PROCESSING, PaymentStatus.SUCCEEDED, PaymentStatus.FAILED},
    PaymentStatus.PROCESSING: {PaymentStatus.SUCCEEDED, PaymentStatus.FAILED},
    PaymentStatus.SUCCEEDED: set(),
    PaymentStatus.FAILED: set(),
    PaymentStatus.REFUNDED: set(),
}

_BULKING_JOB_TRANSITIONS: dict[BulkingJobStatus, set[BulkingJobStatus]] = {
    BulkingJobStatus.ASSIGNED: {BulkingJobStatus.IN_PROGRESS, BulkingJobStatus.CANCELLED},
    BulkingJobStatus.IN_PROGRESS: {BulkingJobStatus.COMPLETED, BulkingJobStatus.CANCELLED},
    BulkingJobStatus.COMPLETED: set(),
    BulkingJobStatus.CANCELLED: set(),
}

_PACKING_TRANSITIONS: dict[PackingStatus, set[PackingStatus]] = {
    PackingStatus.PACKED: {PackingStatus.CERTIFIED, PackingStatus.CANCELLED},
    PackingStatus.CERTIFIED: set(),
    PackingStatus.CANCELLED: set(),
}


def _ensure_transition(entity: str, current, target, transitions: dict) -> None:
    allowed = transitions.get(current)
    if target not in (allowed or set()):
        raise ValueError(
            f"Cannot transition {entity} from "
            f"{current.value if hasattr(current, 'value') else current} to "
            f"{target.value if hasattr(target, 'value') else target}"
        )


def _register_number() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    suffix = "".join(random.choices(string.digits, k=4))
    return f"BR-{stamp}-{suffix}"


def _provider_ref(method: PaymentMethod) -> str:
    token = "".join(random.choices(string.ascii_uppercase + string.digits, k=10))
    return f"{method.value.upper()}-{token}"


def _item_summary(item: TaxonomyItem | None) -> dict:
    if item is None:
        return {}
    band = item.supply_band
    if hasattr(band, "value"):
        band = band.value
    return {
        "item_id": item.id,
        "item_code": item.code,
        "item_name": item.common_name,
        "supply_band": band or ItemSupplyBand.ABUNDANT.value,
    }


def _appointment_out(a: Appointment) -> dict:
    return {
        "id": a.id,
        "buyer_id": a.buyer_id,
        "participant_type": a.participant_type,
        "participant_name": a.participant_name,
        "participant_phone": a.participant_phone,
        "participant_email": a.participant_email,
        "purpose": a.purpose,
        "scheduled_at": str(a.scheduled_at) if a.scheduled_at else None,
        "duration_minutes": a.duration_minutes,
        "channel": a.channel,
        "location": a.location,
        "status": a.status.value if hasattr(a.status, "value") else str(a.status),
        "notes": a.notes,
        "created_at": str(a.created_at) if a.created_at else None,
    }


def _contact_out(c: BulkingContact) -> dict:
    return {
        "id": c.id,
        "register_id": c.register_id,
        "contact_type": c.contact_type.value if hasattr(c.contact_type, "value") else str(c.contact_type),
        "name": c.name,
        "phone": c.phone,
        "email": c.email,
        "location": c.location,
        "is_primary": c.is_primary,
        "notes": c.notes,
        "created_at": str(c.created_at) if c.created_at else None,
    }


def _bid_out(b: BulkingBid, item: TaxonomyItem | None = None) -> dict:
    return {
        "id": b.id,
        "register_id": b.register_id,
        "contact_id": b.contact_id,
        **(_item_summary(item or (b.item if hasattr(b, "item") else None)) if item is not None else {}),
        "quantity": b.quantity,
        "unit": b.unit,
        "unit_price": b.unit_price,
        "currency": b.currency,
        "quality_grade": b.quality_grade,
        "status": b.status.value if hasattr(b.status, "value") else str(b.status),
        "notes": b.notes,
        "created_at": str(b.created_at) if b.created_at else None,
    }


def _booking_out(b: WarehouseBooking) -> dict:
    return {
        "id": b.id,
        "register_id": b.register_id,
        "warehouse_id": b.warehouse_id,
        "start_date": str(b.start_date) if b.start_date else None,
        "end_date": str(b.end_date) if b.end_date else None,
        "quantity": b.quantity,
        "unit": b.unit,
        "storage_cost": b.storage_cost,
        "currency": b.currency,
        "status": b.status.value if hasattr(b.status, "value") else str(b.status),
        "notes": b.notes,
        "created_at": str(b.created_at) if b.created_at else None,
    }


def _courier_out(j: CourierJob) -> dict:
    return {
        "id": j.id,
        "register_id": j.register_id,
        "item_id": j.item_id,
        "pickup_location": j.pickup_location,
        "dropoff_warehouse_id": j.dropoff_warehouse_id,
        "deliver_to_buyer": bool(j.deliver_to_buyer),
        "quantity": j.quantity,
        "unit": j.unit,
        "weight_kg": j.weight_kg,
        "budget": j.budget,
        "currency": j.currency,
        "status": j.status.value if hasattr(j.status, "value") else str(j.status),
        "courier_name": j.courier_name,
        "tracking_code": j.tracking_code,
        "posted_at": str(j.posted_at) if j.posted_at else None,
        "delivered_at": str(j.delivered_at) if j.delivered_at else None,
        "created_at": str(j.created_at) if j.created_at else None,
    }


def _deal_out(d: Deal, item: TaxonomyItem | None = None, contact: BulkingContact | None = None) -> dict:
    return {
        "id": d.id,
        "register_id": d.register_id,
        "buyer_id": d.buyer_id,
        "seller_contact_id": d.seller_contact_id,
        "seller_name": contact.name if contact else None,
        **(_item_summary(item or (d.item if hasattr(d, "item") else None)) if item is not None else {}),
        "quantity": d.quantity,
        "unit": d.unit,
        "unit_price": d.unit_price,
        "total_value": d.total_value,
        "currency": d.currency,
        "status": d.status.value if hasattr(d.status, "value") else str(d.status),
        "credentials_exchanged": d.credentials_exchanged,
        "closed_at": str(d.closed_at) if d.closed_at else None,
        "created_at": str(d.created_at) if d.created_at else None,
    }


def _payment_out(p: Payment) -> dict:
    return {
        "id": p.id,
        "register_id": p.register_id,
        "deal_id": p.deal_id,
        "payer_id": p.payer_id,
        "payee_id": p.payee_id,
        "amount": p.amount,
        "currency": p.currency,
        "method": p.method.value if hasattr(p.method, "value") else str(p.method),
        "provider_reference": p.provider_reference,
        "status": p.status.value if hasattr(p.status, "value") else str(p.status),
        "paid_at": str(p.paid_at) if p.paid_at else None,
        "created_at": str(p.created_at) if p.created_at else None,
    }


def _settlement_out(s: Settlement, item: TaxonomyItem | None = None) -> dict:
    return {
        "id": s.id,
        "register_id": s.register_id,
        "deal_id": s.deal_id,
        "bid_id": s.bid_id,
        "payee_id": s.payee_id,
        "payee_name": s.payee_name,
        **(_item_summary(item or (s.item if hasattr(s, "item") else None)) if item is not None else {}),
        "quantity": s.quantity,
        "unit_price": s.unit_price,
        "gross_amount": s.gross_amount,
        "platform_fee": s.platform_fee,
        "net_amount": s.net_amount,
        "currency": s.currency,
        "status": s.status.value if hasattr(s.status, "value") else str(s.status),
        "payment_id": s.payment_id,
        "settled_at": str(s.settled_at) if s.settled_at else None,
        "created_at": str(s.created_at) if s.created_at else None,
    }


def _job_out(j: BulkingJobAssignment, item: TaxonomyItem | None = None) -> dict:
    return {
        "id": j.id,
        "register_id": j.register_id,
        **(_item_summary(item or (j.item if hasattr(j, "item") else None)) if item is not None else {}),
        "role": j.role.value if hasattr(j.role, "value") else str(j.role),
        "assignee_id": j.assignee_id,
        "assignee_name": j.assignee_name,
        "assignee_location": j.assignee_location,
        "status": j.status.value if hasattr(j.status, "value") else str(j.status),
        "notes": j.notes,
        "assigned_at": str(j.assigned_at) if j.assigned_at else None,
        "completed_at": str(j.completed_at) if j.completed_at else None,
        "created_at": str(j.created_at) if j.created_at else None,
    }


def _packing_out(p: PackingRecord, item: TaxonomyItem | None = None) -> dict:
    return {
        "id": p.id,
        "register_id": p.register_id,
        **(_item_summary(item or (p.item if hasattr(p, "item") else None)) if item is not None else {}),
        "quantity": p.quantity,
        "unit": p.unit,
        "package_type": p.package_type,
        "package_count": p.package_count,
        "total_weight_kg": p.total_weight_kg,
        "certificate_id": p.certificate_id,
        "status": p.status.value if hasattr(p.status, "value") else str(p.status),
        "packed_by_id": p.packed_by_id,
        "packed_by_name": p.packed_by_name,
        "notes": p.notes,
        "packed_at": str(p.packed_at) if p.packed_at else None,
        "created_at": str(p.created_at) if p.created_at else None,
    }


async def _get_register(db: AsyncSession, register_id: int) -> BulkingRegister | None:
    return await db.get(BulkingRegister, register_id)


async def _register_detail(db: AsyncSession, r: BulkingRegister, user: User | None = None) -> dict:
    item = await db.get(TaxonomyItem, r.item_id)
    contacts = (await db.execute(
        select(BulkingContact).where(BulkingContact.register_id == r.id)
        .order_by(BulkingContact.created_at)
    )).scalars().all()
    bids = (await db.execute(
        select(BulkingBid).where(BulkingBid.register_id == r.id)
        .order_by(BulkingBid.created_at)
    )).scalars().all()
    bookings = (await db.execute(
        select(WarehouseBooking).where(WarehouseBooking.register_id == r.id)
        .order_by(WarehouseBooking.created_at)
    )).scalars().all()
    jobs = (await db.execute(
        select(CourierJob).where(CourierJob.register_id == r.id)
        .order_by(CourierJob.created_at)
    )).scalars().all()
    deals = (await db.execute(
        select(Deal).where(Deal.register_id == r.id).order_by(Deal.created_at)
    )).scalars().all()
    settlements = (await db.execute(
        select(Settlement).where(Settlement.register_id == r.id).order_by(Settlement.created_at)
    )).scalars().all()
    payments = (await db.execute(
        select(Payment).where(Payment.register_id == r.id).order_by(Payment.created_at)
    )).scalars().all()
    job_assignments = (await db.execute(
        select(BulkingJobAssignment).where(BulkingJobAssignment.register_id == r.id)
        .order_by(BulkingJobAssignment.created_at)
    )).scalars().all()
    packing_records = (await db.execute(
        select(PackingRecord).where(PackingRecord.register_id == r.id)
        .order_by(PackingRecord.created_at)
    )).scalars().all()
    escrows = (await db.execute(
        select(BulkingEscrow).where(BulkingEscrow.register_id == r.id)
        .order_by(BulkingEscrow.created_at)
    )).scalars().all()

    accepted_volume = sum(b.quantity for b in bids if b.status == BidStatus.ACCEPTED)
    return {
        "id": r.id,
        "register_number": r.register_number,
        "buyer_id": r.buyer_id,
        **_item_summary(item),
        "title": r.title,
        "target_quantity": r.target_quantity,
        "unit": r.unit,
        "target_price": r.target_price,
        "currency": r.currency,
        "region": r.region,
        "sourcing_mode": r.sourcing_mode.value if hasattr(r.sourcing_mode, "value") else str(r.sourcing_mode),
        "sourcing_entity_id": r.sourcing_entity_id,
        "sourcing_entity_name": r.sourcing_entity_name,
        "status": r.status.value if hasattr(r.status, "value") else str(r.status),
        "generated": r.generated,
        "notes": r.notes,
        "accepted_volume": accepted_volume,
        "escrow": _escrow_out(r, item, deals, bids, escrows),
        "created_at": str(r.created_at) if r.created_at else None,
        "updated_at": str(r.updated_at) if r.updated_at else None,
        "contacts": [_contact_out(c) for c in contacts],
        "bids": [_bid_out(b) for b in bids],
        "warehouse_bookings": [_booking_out(b) for b in bookings],
        "courier_jobs": [_courier_out(j) for j in jobs],
        "deals": [_deal_out(d) for d in deals],
        "settlements": [_settlement_out(s) for s in settlements],
        "payments": [_payment_out(p) for p in payments],
        "job_assignments": [_job_out(j) for j in job_assignments],
        "packing_records": [_packing_out(p) for p in packing_records],
        "escrows": [_escrow_record_out(e) for e in escrows],
    }


# ── Appointments ───────────────────────────────────────────────────────────

async def book_appointment(
    db: AsyncSession, user: User, participant_name: str,
    scheduled_at: datetime, participant_type: str | None = None,
    participant_phone: str | None = None, participant_email: str | None = None,
    purpose: str | None = None, duration_minutes: int = 60,
    channel: str | None = None, location: str | None = None, notes: str | None = None,
) -> Appointment:
    if not participant_name or not participant_name.strip():
        raise ValueError("participant_name is required")
    if duration_minutes is not None and duration_minutes <= 0:
        raise ValueError("duration_minutes must be greater than 0")
    appointment = Appointment(
        buyer_id=user.id, tenant_id=user.tenant_id,
        participant_type=participant_type, participant_name=participant_name,
        participant_phone=participant_phone, participant_email=participant_email,
        purpose=purpose, scheduled_at=scheduled_at, duration_minutes=duration_minutes,
        channel=channel, location=location, notes=notes,
        status=AppointmentStatus.REQUESTED, created_by=user.id,
    )
    db.add(appointment)
    await db.commit()
    await db.refresh(appointment)
    return appointment


async def list_appointments(db: AsyncSession, user: User, page: int = 1, upcoming_only: bool = False) -> dict:
    q = select(Appointment)
    if not _is_admin(user):
        q = q.where(Appointment.buyer_id == user.id)
    if upcoming_only:
        q = q.where(Appointment.scheduled_at >= datetime.now(timezone.utc))
    count_q = select(func.count()).select_from(q.subquery())
    total = (await db.execute(count_q)).scalar() or 0
    rows = (await db.execute(
        q.order_by(Appointment.scheduled_at.asc())
        .offset((page - 1) * PAGE_SIZE).limit(PAGE_SIZE)
    )).scalars().all()
    return {
        "appointments": [_appointment_out(a) for a in rows],
        "total": total,
        "page": page,
        "total_pages": max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE),
    }


async def update_appointment_status(db: AsyncSession, user: User, appointment_id: int, status: AppointmentStatus) -> Appointment:
    appointment = await db.get(Appointment, appointment_id)
    if not appointment:
        raise ValueError("Appointment not found")
    if not _is_admin(user) and appointment.buyer_id != user.id:
        raise PermissionError("You can only manage your own appointments")
    _ensure_transition("appointment", appointment.status, status, _APPOINTMENT_TRANSITIONS)
    appointment.status = status
    await db.commit()
    await db.refresh(appointment)
    return appointment


# ── Bulking registers ──────────────────────────────────────────────────────

async def create_bulking_register(
    db: AsyncSession, user: User, item_id: int, target_quantity: float,
    title: str | None = None, unit: str | None = None, target_price: float | None = None,
    currency: str = "USD", region: str | None = None,
    sourcing_mode: SourcingMode = SourcingMode.SELF, auto_generate: bool = False,
    sourcing_entity_id: int | None = None, sourcing_entity_name: str | None = None,
    notes: str | None = None,
) -> BulkingRegister:
    if not _can_buy(user):
        raise PermissionError("Only ADMIN and ENTERPRISE users can create bulking registers")
    if target_quantity <= 0:
        raise ValueError("target_quantity must be greater than 0")
    if target_price is not None and target_price <= 0:
        raise ValueError("target_price must be greater than 0")
    item = await db.get(TaxonomyItem, item_id)
    if not item:
        raise ValueError(f"TaxonomyItem {item_id} not found")

    # Resolve the sourcing entity (cooperative/company supplying the item through
    # its member users). The entity name drives the same-company self-certify block.
    entity_id = sourcing_entity_id
    entity_name = sourcing_entity_name
    if entity_id:
        entity_user = await db.get(User, entity_id)
        if not entity_user or not entity_user.is_active:
            raise ValueError("Sourcing entity user not found or inactive")
        if not entity_name:
            entity_name = entity_user.company or entity_user.full_name

    # Hoist ORM attribute reads above the retry loop: db.rollback() on a
    # failed insert expires every instance in the session, so touching
    # user/item after a rollback would trigger a lazy-load outside greenlet.
    buyer_id = user.id
    tenant_id = user.tenant_id
    register_title = title or f"Aggregate {item.common_name}"
    reg_unit = unit or "kg"
    reg_currency = currency or "USD"

    register = None
    for attempt in range(5):
        register = BulkingRegister(
            register_number=_register_number(),
            buyer_id=buyer_id, tenant_id=tenant_id, item_id=item_id,
            title=register_title,
            target_quantity=target_quantity, unit=reg_unit,
            target_price=target_price, currency=reg_currency,
            region=region, sourcing_mode=sourcing_mode,
            sourcing_entity_id=entity_id, sourcing_entity_name=entity_name,
            status=RegisterStatus.DRAFT, notes=notes,
            created_by=buyer_id,
        )
        db.add(register)
        try:
            await db.commit()
            break
        except IntegrityError:
            await db.rollback()
            if attempt == 4:
                raise
    await db.refresh(register)

    if auto_generate:
        await _auto_aggregate_register(db, user, register.id)

    return register


async def _auto_aggregate_register(db: AsyncSession, user: User, register_id: int) -> dict:
    """'Our aggregating functionality' — builds a bulking register by generating
    contacts and bids across farmers and cooperatives, then marks it aggregated."""
    register = await _get_register(db, register_id)
    if not register:
        raise ValueError("Register not found")
    if not _is_admin(user) and register.buyer_id != user.id:
        raise PermissionError("Not your register")

    item = await db.get(TaxonomyItem, register.item_id)
    base_price = _money(register.target_price) if register.target_price is not None else Decimal("10.0")
    target = register.target_quantity

    # Deterministic pseudo-random pool so repeated generation is stable per register
    rng = random.Random(register.id)

    spec = [
        {"type": ContactType.FARMER, "name": f"Coastal Farmers Co-op ({item.common_name})", "location": f"{register.region or 'Coastal'} Region"},
        {"type": ContactType.FARMER, "name": "Green Valley Produce", "location": "Central Highlands"},
        {"type": ContactType.COOPERATIVE, "name": f"{item.common_name} Cooperative Union", "location": f"{register.region or 'Northern'} District"},
        {"type": ContactType.AGGREGATOR, "name": "AgriLink Aggregators", "location": "Market Hub"},
        {"type": ContactType.TRADER, "name": "FairFields Traders", "location": "Capital Market"},
    ]
    contact_ids: list[int] = []
    for i, s in enumerate(spec):
        contact = BulkingContact(
            register_id=register.id, tenant_id=register.tenant_id,
            contact_type=s["type"], name=s["name"], location=s["location"],
            phone=f"+2567{rng.randint(100, 999)}{rng.randint(100, 999)}",
            email=f"supply{i + 1}@foodtrack.suppliers",
            is_primary=(i == 0),
        )
        db.add(contact)
        await db.flush()
        contact_ids.append(contact.id)

    # Distribute the target quantity across contacts with price variation
    weights = [0.35, 0.25, 0.2, 0.12, 0.08]
    grades = ["A", "A", "B", "A", "B"]
    created_bids = 0
    for i, cid in enumerate(contact_ids):
        qty = round(target * weights[i], 2)
        price = _round_money(base_price * Decimal(str(rng.uniform(0.9, 1.1))))
        bid = BulkingBid(
            register_id=register.id, contact_id=cid, item_id=register.item_id,
            tenant_id=register.tenant_id, quantity=qty, unit=register.unit or "kg",
            unit_price=price, currency=register.currency or "USD",
            quality_grade=grades[i], status=BidStatus.PENDING,
            notes="Auto-aggregated offer",
        )
        db.add(bid)
        created_bids += 1

    register.generated = True
    register.status = RegisterStatus.AGGREGATED
    await db.commit()

    return {
        "register_id": register.id,
        "status": RegisterStatus.AGGREGATED.value,
        "contacts_created": len(contact_ids),
        "bids_created": created_bids,
    }


async def get_register_detail(db: AsyncSession, user: User, register_id: int) -> dict | None:
    register = await _get_register(db, register_id)
    if not register:
        return None
    if not _is_admin(user) and register.buyer_id != user.id:
        raise PermissionError("Not your register")
    return await _register_detail(db, register, user)


async def list_registers(db: AsyncSession, user: User, page: int = 1, status: str | None = None) -> dict:
    q = select(BulkingRegister)
    if not _is_admin(user):
        q = q.where(BulkingRegister.buyer_id == user.id)
    if status:
        q = q.where(BulkingRegister.status == status)
    count_q = select(func.count()).select_from(q.subquery())
    total = (await db.execute(count_q)).scalar() or 0
    rows = (await db.execute(
        q.order_by(BulkingRegister.created_at.desc())
        .offset((page - 1) * PAGE_SIZE).limit(PAGE_SIZE)
    )).scalars().all()

    results = []
    for r in rows:
        item = await db.get(TaxonomyItem, r.item_id)
        results.append({
            "id": r.id,
            "register_number": r.register_number,
            "buyer_id": r.buyer_id,
            **_item_summary(item),
            "title": r.title,
            "target_quantity": r.target_quantity,
            "unit": r.unit,
            "target_price": r.target_price,
            "currency": r.currency,
            "region": r.region,
            "sourcing_mode": r.sourcing_mode.value if hasattr(r.sourcing_mode, "value") else str(r.sourcing_mode),
            "status": r.status.value if hasattr(r.status, "value") else str(r.status),
            "generated": r.generated,
            "created_at": str(r.created_at) if r.created_at else None,
        })
    return {"registers": results, "total": total, "page": page, "total_pages": max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)}


async def update_register_status(db: AsyncSession, user: User, register_id: int, status: RegisterStatus) -> BulkingRegister:
    register = await _get_register(db, register_id)
    if not register:
        raise ValueError("Register not found")
    if not _is_admin(user) and register.buyer_id != user.id:
        raise PermissionError("Not your register")
    _ensure_transition("register", register.status, status, _REGISTER_TRANSITIONS)
    register.status = status
    await db.commit()
    await db.refresh(register)
    return register


# ── Escrow (investor deposit) ───────────────────────────────────────────────

async def get_escrow_requirement(db: AsyncSession, user: User, register_id: int) -> dict:
    """The investor's escrow requirement: 30% of deal value for abundant items,
    65% for rare items, plus the current deposit state."""
    register = await _get_register(db, register_id)
    if not register:
        raise ValueError("Register not found")
    if not _is_admin(user) and register.buyer_id != user.id:
        raise PermissionError("Not your register")
    item = await db.get(TaxonomyItem, register.item_id)
    deals = (await db.execute(
        select(Deal).where(Deal.register_id == register_id)
    )).scalars().all()
    bids = (await db.execute(
        select(BulkingBid).where(BulkingBid.register_id == register_id)
    )).scalars().all()
    escrows = (await db.execute(
        select(BulkingEscrow).where(BulkingEscrow.register_id == register_id)
        .order_by(BulkingEscrow.created_at)
    )).scalars().all()
    return _escrow_out(register, item, deals, bids, escrows)


async def deposit_escrow(
    db: AsyncSession, user: User, register_id: int,
    method: PaymentMethod = PaymentMethod.BANK_TRANSFER,
) -> BulkingEscrow:
    """Record the investor's escrow deposit for a register. The amount is
    30% (abundant) or 65% (rare) of the deal value; a succeeded Payment is
    created alongside the escrow record."""
    register = await _get_register(db, register_id)
    if not register:
        raise ValueError("Register not found")
    if not _is_admin(user) and register.buyer_id != user.id:
        raise PermissionError("Not your register")
    if register.status in (RegisterStatus.CLOSED, RegisterStatus.CANCELLED):
        raise ValueError("Cannot deposit escrow on a closed or cancelled register")
    if not method:
        raise ValueError("payment method is required")

    item = await db.get(TaxonomyItem, register.item_id)
    deals = (await db.execute(
        select(Deal).where(Deal.register_id == register_id)
    )).scalars().all()
    bids = (await db.execute(
        select(BulkingBid).where(BulkingBid.register_id == register_id)
    )).scalars().all()
    escrows = (await db.execute(
        select(BulkingEscrow).where(BulkingEscrow.register_id == register_id)
        .order_by(BulkingEscrow.created_at)
    )).scalars().all()
    for e in escrows:
        if e.status in (EscrowStatus.DEPOSITED, EscrowStatus.HELD, EscrowStatus.RELEASED):
            raise ValueError("Escrow has already been deposited for this register")

    basis = _escrow_basis(register, deals, bids)
    if basis <= 0:
        raise ValueError("No deal value to escrow yet — accept bids or close deals first")
    pct = escrow_percentage_for(item)
    amount = _round_money(basis * pct)
    currency = register.currency or "USD"

    payment = Payment(
        register_id=register_id, payer_id=user.id, payee_id=None,
        tenant_id=register.tenant_id, amount=amount, currency=currency,
        method=method, provider_reference=_provider_ref(method),
        status=PaymentStatus.SUCCEEDED, paid_at=datetime.now(timezone.utc),
    )
    db.add(payment)
    await db.flush()

    escrow = BulkingEscrow(
        register_id=register_id, item_id=register.item_id, tenant_id=register.tenant_id,
        payer_id=user.id, percentage=pct * 100, amount=amount, currency=currency,
        status=EscrowStatus.DEPOSITED, payment_id=payment.id,
        deposited_at=datetime.now(timezone.utc),
    )
    db.add(escrow)
    await db.commit()
    await db.refresh(escrow)
    return escrow


# ── Pipeline trace ──────────────────────────────────────────────────────────

async def get_pipeline_trace(db: AsyncSession, user: User, register_id: int) -> dict:
    """Investor-facing view of the bulking pipeline: register, collate (bids),
    escrow, member jobs (clerk/verifier/packer/certifier/courier), packing &
    certification, buyer delivery and receipt."""
    register = await _get_register(db, register_id)
    if not register:
        raise ValueError("Register not found")
    if not _is_admin(user) and register.buyer_id != user.id:
        raise PermissionError("Not your register")

    item = await db.get(TaxonomyItem, register.item_id)
    bids = (await db.execute(
        select(BulkingBid).where(BulkingBid.register_id == register_id)
    )).scalars().all()
    deals = (await db.execute(
        select(Deal).where(Deal.register_id == register_id)
    )).scalars().all()
    courier_jobs = (await db.execute(
        select(CourierJob).where(CourierJob.register_id == register_id)
    )).scalars().all()
    job_assignments = (await db.execute(
        select(BulkingJobAssignment).where(BulkingJobAssignment.register_id == register_id)
    )).scalars().all()
    packing_records = (await db.execute(
        select(PackingRecord).where(PackingRecord.register_id == register_id)
    )).scalars().all()
    escrows = (await db.execute(
        select(BulkingEscrow).where(BulkingEscrow.register_id == register_id)
        .order_by(BulkingEscrow.created_at)
    )).scalars().all()

    accepted = [b for b in bids if b.status == BidStatus.ACCEPTED]
    escrow = _escrow_out(register, item, deals, bids, escrows)
    escrow_status = escrow["status"]
    delivery_jobs = [j for j in courier_jobs if j.deliver_to_buyer]
    delivery_done = any(j.status == CourierJobStatus.DELIVERED for j in delivery_jobs)
    packing_done = len(packing_records) > 0
    certified = any(p.status == PackingStatus.CERTIFIED for p in packing_records)

    role_status = {}
    for role in BulkingJobRole:
        role_items = [j for j in job_assignments if j.role == role]
        role_status[role.value] = {
            "assigned": len(role_items),
            "completed": sum(1 for j in role_items if j.status == BulkingJobStatus.COMPLETED),
        }

    reg_status = register.status.value if hasattr(register.status, "value") else str(register.status)
    jobs_total = len(job_assignments)
    jobs_completed = sum(1 for j in job_assignments if j.status == BulkingJobStatus.COMPLETED)
    stages = [
        {"key": "register", "label": "Register", "icon": "📋",
         "done": register.status != RegisterStatus.DRAFT, "status": reg_status},
        {"key": "collate", "label": "Collate", "icon": "🤝",
         "done": len(accepted) > 0, "status": "accepted" if accepted else "pending"},
        {"key": "escrow", "label": "Escrow Deposit", "icon": "🔒",
         "done": escrow_status in (EscrowStatus.DEPOSITED.value, EscrowStatus.HELD.value, EscrowStatus.RELEASED.value),
         "status": escrow_status},
        {"key": "jobs", "label": "Member Jobs", "icon": "🧑‍🔧",
         "done": jobs_total > 0 and jobs_completed == jobs_total,
         "status": (f"{jobs_completed}/{jobs_total} completed" if jobs_total else "no jobs")},
        {"key": "pack", "label": "Pack", "icon": "📦",
         "done": packing_done, "status": "packed" if packing_done else "pending"},
        {"key": "certify", "label": "Certify", "icon": "📜",
         "done": certified, "status": "certified" if certified else "pending"},
        {"key": "deliver", "label": "Deliver to Buyer", "icon": "🚚",
         "done": delivery_done, "status": CourierJobStatus.DELIVERED.value if delivery_done else "pending"},
        {"key": "receive", "label": "Received & Released", "icon": "✅",
         "done": escrow_status == EscrowStatus.RELEASED.value,
         "status": "received" if escrow_status == EscrowStatus.RELEASED.value else reg_status},
    ]

    return {
        "register_id": register_id,
        "register_number": register.register_number,
        **_item_summary(item),
        "status": reg_status,
        "escrow": escrow,
        "stages": stages,
        "roles": role_status,
        "delivery_jobs": [_courier_out(j) for j in delivery_jobs],
    }


# ── Contacts ───────────────────────────────────────────────────────────────

async def add_contact(
    db: AsyncSession, user: User, register_id: int, name: str,
    contact_type: ContactType = ContactType.FARMER, phone: str | None = None,
    email: str | None = None, location: str | None = None,
    is_primary: bool = False, notes: str | None = None,
) -> BulkingContact:
    register = await _get_register(db, register_id)
    if not register:
        raise ValueError("Register not found")
    if not _is_admin(user) and register.buyer_id != user.id:
        raise PermissionError("Not your register")
    contact = BulkingContact(
        register_id=register_id, tenant_id=register.tenant_id,
        contact_type=contact_type, name=name, phone=phone, email=email,
        location=location, is_primary=is_primary, notes=notes,
    )
    db.add(contact)
    await db.commit()
    await db.refresh(contact)
    return contact


async def list_contacts(db: AsyncSession, user: User, register_id: int) -> list[dict]:
    register = await _get_register(db, register_id)
    if not register:
        raise ValueError("Register not found")
    if not _is_admin(user) and register.buyer_id != user.id:
        raise PermissionError("Not your register")
    rows = (await db.execute(
        select(BulkingContact).where(BulkingContact.register_id == register_id).order_by(BulkingContact.created_at)
    )).scalars().all()
    return [_contact_out(c) for c in rows]


# ── Bids ───────────────────────────────────────────────────────────────────

async def submit_bid(
    db: AsyncSession, user: User, register_id: int, quantity: float, unit_price: float,
    contact_id: int | None = None, item_id: int | None = None,
    unit: str | None = None, currency: str = "USD",
    quality_grade: str | None = None, notes: str | None = None,
) -> BulkingBid:
    register = await _get_register(db, register_id)
    if not register:
        raise ValueError("Register not found")
    if not _is_admin(user) and register.buyer_id != user.id:
        raise PermissionError("Not your register")
    if register.status in (RegisterStatus.CLOSED, RegisterStatus.CANCELLED):
        raise ValueError("Cannot bid on a closed or cancelled register")
    if quantity <= 0:
        raise ValueError("quantity must be greater than 0")
    if unit_price <= 0:
        raise ValueError("unit_price must be greater than 0")
    if item_id is not None and item_id != register.item_id:
        raise ValueError("item_id does not match the register's item")
    if contact_id:
        contact = await db.get(BulkingContact, contact_id)
        if not contact or contact.register_id != register_id:
            raise ValueError("Contact does not belong to this register")

    bid = BulkingBid(
        register_id=register_id, contact_id=contact_id,
        item_id=item_id or register.item_id, tenant_id=register.tenant_id,
        quantity=quantity, unit=unit or register.unit or "kg",
        unit_price=unit_price, currency=currency or register.currency or "USD",
        quality_grade=quality_grade, status=BidStatus.PENDING, notes=notes,
    )
    db.add(bid)
    await db.commit()
    await db.refresh(bid)
    return bid


async def list_bids(db: AsyncSession, user: User, register_id: int) -> list[dict]:
    register = await _get_register(db, register_id)
    if not register:
        raise ValueError("Register not found")
    if not _is_admin(user) and register.buyer_id != user.id:
        raise PermissionError("Not your register")
    rows = (await db.execute(
        select(BulkingBid).where(BulkingBid.register_id == register_id).order_by(BulkingBid.created_at)
    )).scalars().all()
    return [_bid_out(b) for b in rows]


async def _set_bid_status(db: AsyncSession, user: User, bid_id: int, status: BidStatus) -> BulkingBid:
    bid = await db.get(BulkingBid, bid_id)
    if not bid:
        raise ValueError("Bid not found")
    register = await _get_register(db, bid.register_id)
    if not _is_admin(user) and register.buyer_id != user.id:
        raise PermissionError("Not your register")
    _ensure_transition("bid", bid.status, status, _BID_TRANSITIONS)
    bid.status = status
    await db.commit()
    await db.refresh(bid)
    return bid


async def accept_bid(db: AsyncSession, user: User, bid_id: int) -> BulkingBid:
    return await _set_bid_status(db, user, bid_id, BidStatus.ACCEPTED)


async def reject_bid(db: AsyncSession, user: User, bid_id: int) -> BulkingBid:
    return await _set_bid_status(db, user, bid_id, BidStatus.REJECTED)


# ── Warehousing ────────────────────────────────────────────────────────────

async def book_warehouse(
    db: AsyncSession, user: User, register_id: int, warehouse_id: int,
    start_date: datetime | None = None, end_date: datetime | None = None,
    quantity: float | None = None, unit: str | None = None,
    storage_cost: float | None = None, currency: str = "USD", notes: str | None = None,
) -> WarehouseBooking:
    register = await _get_register(db, register_id)
    if not register:
        raise ValueError("Register not found")
    if not _is_admin(user) and register.buyer_id != user.id:
        raise PermissionError("Not your register")
    warehouse = await db.get(Warehouse, warehouse_id)
    if not warehouse:
        raise ValueError("Warehouse not found")
    if not warehouse.is_active:
        raise ValueError("Warehouse is not active")
    if quantity is not None and quantity <= 0:
        raise ValueError("quantity must be greater than 0")
    if storage_cost is not None and storage_cost < 0:
        raise ValueError("storage_cost cannot be negative")
    booking = WarehouseBooking(
        register_id=register_id, warehouse_id=warehouse_id, tenant_id=register.tenant_id,
        start_date=start_date, end_date=end_date, quantity=quantity,
        unit=unit or register.unit or "kg", storage_cost=storage_cost,
        currency=currency or register.currency or "USD",
        status=WarehouseBookingStatus.REQUESTED, notes=notes,
    )
    db.add(booking)
    await db.commit()
    await db.refresh(booking)
    return booking


async def list_warehouse_bookings(db: AsyncSession, user: User, register_id: int) -> list[dict]:
    register = await _get_register(db, register_id)
    if not register:
        raise ValueError("Register not found")
    if not _is_admin(user) and register.buyer_id != user.id:
        raise PermissionError("Not your register")
    rows = (await db.execute(
        select(WarehouseBooking).where(WarehouseBooking.register_id == register_id).order_by(WarehouseBooking.created_at)
    )).scalars().all()
    return [_booking_out(b) for b in rows]


async def update_warehouse_booking_status(db: AsyncSession, user: User, booking_id: int, status: WarehouseBookingStatus) -> WarehouseBooking:
    booking = await db.get(WarehouseBooking, booking_id)
    if not booking:
        raise ValueError("Booking not found")
    register = await _get_register(db, booking.register_id)
    if not _is_admin(user) and register.buyer_id != user.id:
        raise PermissionError("Not your register")
    _ensure_transition("warehouse booking", booking.status, status, _BOOKING_TRANSITIONS)
    booking.status = status
    await db.commit()
    await db.refresh(booking)
    return booking


# ── Courier jobs ───────────────────────────────────────────────────────────

async def post_courier_job(
    db: AsyncSession, user: User, register_id: int, pickup_location: str,
    item_id: int | None = None, dropoff_warehouse_id: int | None = None,
    quantity: float | None = None, unit: str | None = None, weight_kg: float | None = None,
    budget: float | None = None, currency: str = "USD", courier_name: str | None = None,
    deliver_to_buyer: bool = False,
) -> CourierJob:
    register = await _get_register(db, register_id)
    if not register:
        raise ValueError("Register not found")
    if not _is_admin(user) and register.buyer_id != user.id:
        raise PermissionError("Not your register")
    if not pickup_location or not pickup_location.strip():
        raise ValueError("pickup_location is required")
    if quantity is not None and quantity <= 0:
        raise ValueError("quantity must be greater than 0")
    if budget is not None and budget <= 0:
        raise ValueError("budget must be greater than 0")
    if dropoff_warehouse_id:
        dropoff = await db.get(Warehouse, dropoff_warehouse_id)
        if not dropoff:
            raise ValueError("Dropoff warehouse not found")
        if not dropoff.is_active:
            raise ValueError("Dropoff warehouse is not active")
    job = CourierJob(
        register_id=register_id, item_id=item_id or register.item_id, tenant_id=register.tenant_id,
        pickup_location=pickup_location, dropoff_warehouse_id=dropoff_warehouse_id,
        deliver_to_buyer=deliver_to_buyer,
        quantity=quantity, unit=unit or register.unit or "kg", weight_kg=weight_kg,
        budget=budget, currency=currency or register.currency or "USD",
        status=CourierJobStatus.POSTED, courier_name=courier_name,
        tracking_code="".join(random.choices(string.ascii_uppercase + string.digits, k=10)),
        posted_at=datetime.now(timezone.utc),
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    return job


async def list_courier_jobs(db: AsyncSession, user: User, register_id: int) -> list[dict]:
    register = await _get_register(db, register_id)
    if not register:
        raise ValueError("Register not found")
    if not _is_admin(user) and register.buyer_id != user.id:
        raise PermissionError("Not your register")
    rows = (await db.execute(
        select(CourierJob).where(CourierJob.register_id == register_id).order_by(CourierJob.created_at)
    )).scalars().all()
    return [_courier_out(j) for j in rows]


async def update_courier_job_status(db: AsyncSession, user: User, job_id: int, status: CourierJobStatus) -> CourierJob:
    job = await db.get(CourierJob, job_id)
    if not job:
        raise ValueError("Courier job not found")
    register = await _get_register(db, job.register_id)
    if not _is_admin(user) and register.buyer_id != user.id:
        raise PermissionError("Not your register")
    _ensure_transition("courier job", job.status, status, _COURIER_TRANSITIONS)
    job.status = status
    if status == CourierJobStatus.DELIVERED and not job.delivered_at:
        job.delivered_at = datetime.now(timezone.utc)
        # Buyer-delivery final leg: the investor received the goods they paid
        # for, so the escrow is released to the seller.
        if job.deliver_to_buyer:
            await _release_register_escrow(db, register)
    await db.commit()
    await db.refresh(job)
    return job


async def _release_register_escrow(db: AsyncSession, register: BulkingRegister) -> None:
    escrows = (await db.execute(
        select(BulkingEscrow).where(BulkingEscrow.register_id == register.id)
        .order_by(BulkingEscrow.created_at)
    )).scalars().all()
    for escrow in escrows:
        if escrow.status in (EscrowStatus.DEPOSITED, EscrowStatus.HELD):
            escrow.status = EscrowStatus.RELEASED
            escrow.released_at = datetime.now(timezone.utc)


# ── Deals & credential exchange ────────────────────────────────────────────

async def close_deal(
    db: AsyncSession, user: User, register_id: int, quantity: float, unit_price: float,
    seller_contact_id: int | None = None, item_id: int | None = None,
    unit: str | None = None, currency: str = "USD",
) -> dict:
    """Close a deal on aggregated stock. The deal is created in the AGREED state;
    the buyer and seller exchange credentials (emails) via exchange_credentials,
    which flips the deal to CLOSED."""
    register = await _get_register(db, register_id)
    if not register:
        raise ValueError("Register not found")
    if not _is_admin(user) and register.buyer_id != user.id:
        raise PermissionError("Not your register")
    if quantity <= 0:
        raise ValueError("quantity must be greater than 0")
    if unit_price <= 0:
        raise ValueError("unit_price must be greater than 0")

    contact = None
    if seller_contact_id:
        contact = await db.get(BulkingContact, seller_contact_id)
        if not contact or contact.register_id != register_id:
            raise ValueError("Seller contact does not belong to this register")

    total_value = _round_money(_money(quantity) * _money(unit_price))
    deal = Deal(
        register_id=register_id, buyer_id=user.id, seller_contact_id=seller_contact_id,
        item_id=item_id or register.item_id, tenant_id=register.tenant_id,
        quantity=quantity, unit=unit or register.unit or "kg",
        unit_price=unit_price, total_value=total_value,
        currency=currency or register.currency or "USD",
        status=DealStatus.AGREED, credentials_exchanged=False,
    )
    db.add(deal)
    await db.flush()

    # Auto-create the pending settlement for this deal (pipeline step: settlement)
    settlement = Settlement(
        register_id=register_id, deal_id=deal.id, payee_id=None,
        payee_name=contact.name if contact else "Aggregated seller",
        item_id=deal.item_id, tenant_id=register.tenant_id,
        quantity=quantity, unit_price=unit_price,
        gross_amount=total_value,
        platform_fee=_round_money(total_value * PLATFORM_FEE_DECIMAL),
        net_amount=_round_money(total_value * (Decimal("1") - PLATFORM_FEE_DECIMAL)),
        currency=deal.currency or "USD", status=SettlementStatus.PENDING,
    )
    db.add(settlement)

    await db.commit()
    await db.refresh(deal)

    # Credentials (emails) are exchanged out-of-band, never returned in the API.
    return {
        "deal": _deal_out(deal, contact=contact),
        "credentials_exchanged": False,
        "settlement_created": True,
    }


async def list_deals(db: AsyncSession, user: User, page: int = 1) -> dict:
    q = select(Deal)
    if not _is_admin(user):
        q = q.where(Deal.buyer_id == user.id)
    count_q = select(func.count()).select_from(q.subquery())
    total = (await db.execute(count_q)).scalar() or 0
    rows = (await db.execute(
        q.order_by(Deal.created_at.desc()).offset((page - 1) * PAGE_SIZE).limit(PAGE_SIZE)
    )).scalars().all()
    results = []
    for d in rows:
        contact = await db.get(BulkingContact, d.seller_contact_id) if d.seller_contact_id else None
        results.append(_deal_out(d, contact=contact))
    return {"deals": results, "total": total, "page": page, "total_pages": max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)}


async def exchange_credentials(db: AsyncSession, user: User, deal_id: int) -> dict:
    deal = await db.get(Deal, deal_id)
    if not deal:
        raise ValueError("Deal not found")
    if not _is_admin(user) and deal.buyer_id != user.id:
        raise PermissionError("Not your deal")

    contact = await db.get(BulkingContact, deal.seller_contact_id) if deal.seller_contact_id else None

    if not deal.credentials_exchanged:
        deal.status = DealStatus.CLOSED
        deal.closed_at = datetime.now(timezone.utc)
        deal.credentials_exchanged = True
        await db.commit()

    return {
        "deal_id": deal.id,
        "credentials_exchanged": True,
        "seller_name": contact.name if contact else None,
    }


# ── Settlement ─────────────────────────────────────────────────────────────

async def calculate_settlements(db: AsyncSession, user: User, register_id: int) -> dict:
    """Compute settlements for the register: one per accepted bid / closed deal.
    gross = quantity x unit_price; platform_fee = 2.5% of gross; net = gross - fee."""
    register = await _get_register(db, register_id)
    if not register:
        raise ValueError("Register not found")
    if not _is_admin(user) and register.buyer_id != user.id:
        raise PermissionError("Not your register")

    deals = (await db.execute(
        select(Deal).where(Deal.register_id == register_id)
    )).scalars().all()

    created = 0
    for d in deals:
        existing = (await db.execute(
            select(Settlement).where(Settlement.deal_id == d.id)
        )).scalars().first()
        if existing:
            continue
        contact = await db.get(BulkingContact, d.seller_contact_id) if d.seller_contact_id else None
        gross = _money(d.total_value)
        settlement = Settlement(
            register_id=register_id, deal_id=d.id, payee_id=None,
            payee_name=contact.name if contact else "Aggregated seller",
            item_id=d.item_id, tenant_id=register.tenant_id,
            quantity=d.quantity, unit_price=d.unit_price,
            gross_amount=gross,
            platform_fee=_round_money(gross * PLATFORM_FEE_DECIMAL),
            net_amount=_round_money(gross * (Decimal("1") - PLATFORM_FEE_DECIMAL)),
            currency=d.currency or "USD", status=SettlementStatus.PENDING,
        )
        db.add(settlement)
        created += 1

    # Accepted bids without a closed deal still generate a settlement (buy from many farmers)
    accepted_bids = (await db.execute(
        select(BulkingBid)
        .options(selectinload(BulkingBid.contact))
        .where(
            BulkingBid.register_id == register_id,
            BulkingBid.status == BidStatus.ACCEPTED,
        )
    )).scalars().all()
    for b in accepted_bids:
        existing = (await db.execute(
            select(Settlement).where(
                Settlement.register_id == register_id,
                Settlement.deal_id.is_(None),
                Settlement.bid_id == b.id,
            )
        )).scalars().first()
        if existing:
            continue
        gross = _round_money(_money(b.quantity) * _money(b.unit_price))
        settlement = Settlement(
            register_id=register_id, deal_id=None, bid_id=b.id,
            payee_id=None,
            payee_name=b.contact.name if b.contact else "Aggregated seller",
            item_id=b.item_id, tenant_id=register.tenant_id,
            quantity=b.quantity, unit_price=b.unit_price,
            gross_amount=gross,
            platform_fee=_round_money(gross * PLATFORM_FEE_DECIMAL),
            net_amount=_round_money(gross * (Decimal("1") - PLATFORM_FEE_DECIMAL)),
            currency=b.currency or "USD", status=SettlementStatus.PENDING,
        )
        db.add(settlement)
        created += 1

    await db.commit()
    return {"register_id": register_id, "settlements_created": created}


async def list_settlements(db: AsyncSession, user: User, register_id: int) -> list[dict]:
    register = await _get_register(db, register_id)
    if not register:
        raise ValueError("Register not found")
    if not _is_admin(user) and register.buyer_id != user.id:
        raise PermissionError("Not your register")
    rows = (await db.execute(
        select(Settlement).where(Settlement.register_id == register_id).order_by(Settlement.created_at)
    )).scalars().all()
    return [_settlement_out(s) for s in rows]


async def mark_settlement_paid(db: AsyncSession, user: User, settlement_id: int, payment_id: int | None = None) -> Settlement:
    settlement = await db.get(Settlement, settlement_id)
    if not settlement:
        raise ValueError("Settlement not found")
    register = await _get_register(db, settlement.register_id)
    if not _is_admin(user) and register.buyer_id != user.id:
        raise PermissionError("Not your register")
    if payment_id:
        payment = await db.get(Payment, payment_id)
        if not payment:
            raise ValueError("Payment not found")
        if payment.status != PaymentStatus.SUCCEEDED:
            raise ValueError("Only succeeded payments can settle")
        if payment.register_id != settlement.register_id:
            raise ValueError("Payment does not belong to the settlement's register")
        settlement.payment_id = payment.id
    settlement.status = SettlementStatus.PAID
    settlement.settled_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(settlement)
    return settlement


# ── Payments ───────────────────────────────────────────────────────────────

async def initiate_payment(
    db: AsyncSession, user: User, amount: float, currency: str, method: PaymentMethod,
    register_id: int | None = None, deal_id: int | None = None,
    payee_id: int | None = None, provider_reference: str | None = None,
) -> Payment:
    if amount <= 0:
        raise ValueError("amount must be greater than 0")
    if register_id is not None:
        register = await _get_register(db, register_id)
        if not register:
            raise ValueError("Register not found")
        if not _is_admin(user) and register.buyer_id != user.id:
            raise PermissionError("Not your register")
    if deal_id is not None:
        deal = await db.get(Deal, deal_id)
        if not deal:
            raise ValueError("Deal not found")
        if register_id is not None and deal.register_id != register_id:
            raise ValueError("Deal does not belong to the given register")
    payment = Payment(
        register_id=register_id, deal_id=deal_id,
        payer_id=user.id, payee_id=payee_id, tenant_id=user.tenant_id,
        amount=amount, currency=currency or "USD", method=method,
        provider_reference=provider_reference or _provider_ref(method),
        status=PaymentStatus.PENDING,
    )
    db.add(payment)
    await db.commit()
    await db.refresh(payment)
    return payment


async def confirm_payment(db: AsyncSession, user: User, payment_id: int) -> Payment:
    payment = await db.get(Payment, payment_id)
    if not payment:
        raise ValueError("Payment not found")
    if not _is_admin(user) and payment.payer_id != user.id:
        raise PermissionError("Not your payment")
    _ensure_transition("payment", payment.status, PaymentStatus.SUCCEEDED, _PAYMENT_TRANSITIONS)
    payment.status = PaymentStatus.SUCCEEDED
    payment.paid_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(payment)
    return payment


async def list_payments(db: AsyncSession, user: User, page: int = 1) -> dict:
    q = select(Payment)
    if not _is_admin(user):
        q = q.where(Payment.payer_id == user.id)
    count_q = select(func.count()).select_from(q.subquery())
    total = (await db.execute(count_q)).scalar() or 0
    rows = (await db.execute(
        q.order_by(Payment.created_at.desc()).offset((page - 1) * PAGE_SIZE).limit(PAGE_SIZE)
    )).scalars().all()
    return {"payments": [_payment_out(p) for p in rows], "total": total, "page": page, "total_pages": max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)}


def list_payment_methods() -> list[dict]:
    return SUPPORTED_PAYMENT_METHODS


# ── Pipeline jobs (Clerks, Verifiers, Couriers) ─────────────────────────────

async def list_job_candidates(db: AsyncSession, user: User, register_id: int) -> list[dict]:
    """Users in the item's locus eligible for pipeline job assignment.

    The locus is scoped to the register's tenant users when one exists,
    otherwise every active user on the platform. The buyer (acting user) is
    excluded so jobs are assigned to distinct workers."""
    register = await _get_register(db, register_id)
    if not register:
        raise ValueError("Register not found")
    if not _is_admin(user) and register.buyer_id != user.id:
        raise PermissionError("Not your register")

    q = select(User).where(User.is_active.is_(True), User.id != user.id)
    if register.tenant_id:
        q = q.where(User.tenant_id == register.tenant_id)
    rows = (await db.execute(q.order_by(User.full_name.asc()))).scalars().all()
    return [
        {
            "id": u.id,
            "name": u.full_name,
            "email": u.email,
            "company": u.company,
            "role": u.role.value if hasattr(u.role, "value") else str(u.role),
        }
        for u in rows
    ]


async def create_job_assignment(
    db: AsyncSession, user: User, register_id: int, role: BulkingJobRole,
    assignee_id: int | None = None, assignee_name: str | None = None,
    assignee_location: str | None = None, notes: str | None = None,
) -> BulkingJobAssignment:
    register = await _get_register(db, register_id)
    if not register:
        raise ValueError("Register not found")
    if not _is_admin(user) and register.buyer_id != user.id:
        raise PermissionError("Not your register")
    if not role:
        raise ValueError("role is required")
    if register.status in (RegisterStatus.CLOSED, RegisterStatus.CANCELLED):
        raise ValueError("Cannot assign jobs to a closed or cancelled register")

    assignee = None
    if assignee_id:
        assignee = await db.get(User, assignee_id)
        if not assignee or not assignee.is_active:
            raise ValueError("Assignee user not found or inactive")
        if not assignee_name:
            assignee_name = assignee.full_name
    if not assignee_name or not assignee_name.strip():
        raise ValueError("assignee_name is required")

    # Same-company no-self-certify: the certifier is an entity member user, but
    # they must not belong to the sourcing entity that produced the item.
    if role == BulkingJobRole.CERTIFIER:
        if assignee is None:
            raise ValueError("Certifier must be a registered user (assignee_id is required)")
        entity = (register.sourcing_entity_name or "").strip().lower()
        company = (assignee.company or "").strip().lower()
        if entity and company and entity == company:
            raise ValueError(
                "Certifier cannot belong to the sourcing entity — "
                "same-company self-certification is not allowed"
            )

    assignment = BulkingJobAssignment(
        register_id=register_id, item_id=register.item_id, tenant_id=register.tenant_id,
        role=role, assignee_id=assignee.id if assignee else None,
        assignee_name=assignee_name, assignee_location=assignee_location,
        status=BulkingJobStatus.ASSIGNED, notes=notes,
    )
    db.add(assignment)
    await db.commit()
    await db.refresh(assignment)
    return assignment


async def list_job_assignments(db: AsyncSession, user: User, register_id: int) -> list[dict]:
    register = await _get_register(db, register_id)
    if not register:
        raise ValueError("Register not found")
    if not _is_admin(user) and register.buyer_id != user.id:
        raise PermissionError("Not your register")
    rows = (await db.execute(
        select(BulkingJobAssignment).where(BulkingJobAssignment.register_id == register_id)
        .order_by(BulkingJobAssignment.created_at)
    )).scalars().all()
    return [_job_out(j) for j in rows]


async def update_job_assignment_status(
    db: AsyncSession, user: User, assignment_id: int, status: BulkingJobStatus,
) -> BulkingJobAssignment:
    assignment = await db.get(BulkingJobAssignment, assignment_id)
    if not assignment:
        raise ValueError("Job assignment not found")
    register = await _get_register(db, assignment.register_id)
    if not _is_admin(user) and register.buyer_id != user.id:
        raise PermissionError("Not your register")
    _ensure_transition("job assignment", assignment.status, status, _BULKING_JOB_TRANSITIONS)
    assignment.status = status
    if status == BulkingJobStatus.COMPLETED and not assignment.completed_at:
        assignment.completed_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(assignment)
    return assignment


# ── Packing & certification ─────────────────────────────────────────────────

async def create_packing_record(
    db: AsyncSession, user: User, register_id: int, quantity: float,
    unit: str | None = None, package_type: str | None = None,
    package_count: int | None = None, total_weight_kg: float | None = None,
    certificate_id: str | None = None, packed_by_id: int | None = None,
    notes: str | None = None,
) -> PackingRecord:
    register = await _get_register(db, register_id)
    if not register:
        raise ValueError("Register not found")
    if not _is_admin(user) and register.buyer_id != user.id:
        raise PermissionError("Not your register")
    if quantity <= 0:
        raise ValueError("quantity must be greater than 0")
    if package_count is not None and package_count <= 0:
        raise ValueError("package_count must be greater than 0")
    if total_weight_kg is not None and total_weight_kg <= 0:
        raise ValueError("total_weight_kg must be greater than 0")
    if certificate_id:
        cert = (await db.execute(
            select(Certificate).where(Certificate.certificate_id == certificate_id)
        )).scalar_one_or_none()
        if not cert:
            raise ValueError("Certificate not found")
        if cert.item_id is not None and cert.item_id != register.item_id:
            raise ValueError("Certificate does not belong to the register's item")

    packed_by = await db.get(User, packed_by_id) if packed_by_id else None
    record = PackingRecord(
        register_id=register_id, item_id=register.item_id, tenant_id=register.tenant_id,
        quantity=quantity, unit=unit or register.unit or "kg",
        package_type=package_type, package_count=package_count,
        total_weight_kg=total_weight_kg, certificate_id=certificate_id,
        status=PackingStatus.CERTIFIED if certificate_id else PackingStatus.PACKED,
        packed_by_id=packed_by.id if packed_by else user.id,
        packed_by_name=packed_by.full_name if packed_by else user.full_name,
        notes=notes,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


async def list_packing_records(db: AsyncSession, user: User, register_id: int) -> list[dict]:
    register = await _get_register(db, register_id)
    if not register:
        raise ValueError("Register not found")
    if not _is_admin(user) and register.buyer_id != user.id:
        raise PermissionError("Not your register")
    rows = (await db.execute(
        select(PackingRecord).where(PackingRecord.register_id == register_id)
        .order_by(PackingRecord.created_at)
    )).scalars().all()
    return [_packing_out(p) for p in rows]


async def update_packing_status(
    db: AsyncSession, user: User, packing_id: int, status: PackingStatus,
    certificate_id: str | None = None,
) -> PackingRecord:
    record = await db.get(PackingRecord, packing_id)
    if not record:
        raise ValueError("Packing record not found")
    register = await _get_register(db, record.register_id)
    if not _is_admin(user) and register.buyer_id != user.id:
        raise PermissionError("Not your register")
    _ensure_transition("packing record", record.status, status, _PACKING_TRANSITIONS)
    if status == PackingStatus.CERTIFIED:
        cert_id = certificate_id or record.certificate_id
        if not cert_id:
            raise ValueError("certificate_id is required to certify a packing record")
        cert = (await db.execute(
            select(Certificate).where(Certificate.certificate_id == cert_id)
        )).scalar_one_or_none()
        if not cert:
            raise ValueError("Certificate not found")
        if cert.item_id is not None and cert.item_id != register.item_id:
            raise ValueError("Certificate does not belong to the register's item")
        record.certificate_id = cert_id
    record.status = status
    await db.commit()
    await db.refresh(record)
    return record


# ── Business dashboard ─────────────────────────────────────────────────────

async def get_business_dashboard(db: AsyncSession, user: User) -> dict:
    """Aggregated KPIs for the commerce / bulking pipeline, scoped to the buyer
    unless the caller is an admin."""
    admin = _is_admin(user)

    def _register_scope():
        return select(BulkingRegister.id).where(BulkingRegister.buyer_id == user.id)

    async def _count(model, col, *extra):
        q = select(func.count(model.id))
        if not admin and col is not None:
            q = q.where(col == user.id)
        if extra:
            q = q.where(*extra)
        return (await db.execute(q)).scalar() or 0

    async def _register_count(model, *extra):
        q = select(func.count(model.id))
        if not admin:
            q = q.where(model.register_id.in_(_register_scope()))
        if extra:
            q = q.where(*extra)
        return (await db.execute(q)).scalar() or 0

    total_registers = await _count(BulkingRegister, BulkingRegister.buyer_id)
    closed_registers = await _count(BulkingRegister, BulkingRegister.buyer_id, BulkingRegister.status == RegisterStatus.CLOSED)
    total_contacts = await _register_count(BulkingContact)
    total_bids = await _register_count(BulkingBid)
    accepted_bids = await _register_count(BulkingBid, BulkingBid.status == BidStatus.ACCEPTED)

    total_appointments = await _count(Appointment, Appointment.buyer_id)
    upcoming_appointments = await _count(
        Appointment,
        Appointment.buyer_id,
        Appointment.scheduled_at >= datetime.now(timezone.utc),
    )

    total_deals = await _count(Deal, Deal.buyer_id)
    closed_deals = await _count(Deal, Deal.buyer_id, Deal.status == DealStatus.CLOSED)

    total_settlements = await _register_count(Settlement)
    pending_settlements = await _register_count(Settlement, Settlement.status == SettlementStatus.PENDING)
    paid_settlements = await _register_count(Settlement, Settlement.status == SettlementStatus.PAID)

    total_payments = await _count(Payment, Payment.payer_id)
    succeeded_payments = await _count(Payment, Payment.payer_id, Payment.status == PaymentStatus.SUCCEEDED)

    # Escrow KPIs
    escrow_total = await _register_count(BulkingEscrow)
    escrow_deposited = await _register_count(
        BulkingEscrow,
        BulkingEscrow.status.in_([EscrowStatus.DEPOSITED, EscrowStatus.HELD]),
    )
    escrow_released = await _register_count(BulkingEscrow, BulkingEscrow.status == EscrowStatus.RELEASED)
    q_escrow_value = select(func.coalesce(func.sum(BulkingEscrow.amount), 0)).where(
        BulkingEscrow.status.in_([EscrowStatus.DEPOSITED, EscrowStatus.HELD])
    )
    if not admin:
        q_escrow_value = q_escrow_value.where(BulkingEscrow.register_id.in_(_register_scope()))
    escrow_value = (await db.execute(q_escrow_value)).scalar() or 0.0

    # Monetary aggregates
    q_deal_value = select(func.coalesce(func.sum(Deal.total_value), 0))
    q_net_value = select(func.coalesce(func.sum(Settlement.net_amount), 0))
    q_paid_value = select(func.coalesce(func.sum(Settlement.net_amount), 0)).where(Settlement.status == SettlementStatus.PAID)
    if not admin:
        q_deal_value = q_deal_value.where(Deal.buyer_id == user.id)
        q_net_value = q_net_value.where(Settlement.register_id.in_(_register_scope()))
        q_paid_value = q_paid_value.where(Settlement.register_id.in_(_register_scope()))
    deal_value_total = (await db.execute(q_deal_value)).scalar() or 0.0
    settlement_value_total = (await db.execute(q_net_value)).scalar() or 0.0
    paid_value_total = (await db.execute(q_paid_value)).scalar() or 0.0

    # Payments by method
    q_pm = select(Payment.method, func.count(Payment.id)).group_by(Payment.method)
    if not admin:
        q_pm = q_pm.where(Payment.payer_id == user.id)
    pm_rows = (await db.execute(q_pm)).all()
    payments_by_method = {
        (m.value if hasattr(m, "value") else str(m)): cnt for m, cnt in pm_rows
    }

    # Active warehouse bookings + courier jobs
    active_bookings = await _register_count(
        WarehouseBooking,
        WarehouseBooking.status.in_([WarehouseBookingStatus.CONFIRMED, WarehouseBookingStatus.IN_USE]),
    )
    active_courier_jobs = await _register_count(
        CourierJob,
        CourierJob.status.in_([CourierJobStatus.POSTED, CourierJobStatus.ASSIGNED, CourierJobStatus.IN_TRANSIT]),
    )

    return {
        "registers": {
            "total": total_registers,
            "closed": closed_registers,
        },
        "contacts": total_contacts,
        "bids": {
            "total": total_bids,
            "accepted": accepted_bids,
        },
        "appointments": {
            "total": total_appointments,
            "upcoming": upcoming_appointments,
        },
        "deals": {
            "total": total_deals,
            "closed": closed_deals,
            "value_total": round(deal_value_total, 2),
        },
        "warehouse_bookings_active": active_bookings,
        "courier_jobs_active": active_courier_jobs,
        "settlements": {
            "total": total_settlements,
            "pending": pending_settlements,
            "paid": paid_settlements,
            "value_total": round(settlement_value_total, 2),
            "paid_value_total": round(paid_value_total, 2),
        },
        "payments": {
            "total": total_payments,
            "succeeded": succeeded_payments,
            "by_method": payments_by_method,
        },
        "escrows": {
            "total": escrow_total,
            "deposited": escrow_deposited,
            "released": escrow_released,
            "value_held": round(escrow_value, 2),
        },
        "platform_fee_rate": PLATFORM_FEE_RATE,
    }
