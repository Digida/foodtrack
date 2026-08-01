"""Tests for commerce_service.py — bulking registers, bids, deals, settlements, payments.

Covers the F6 fixes: register-number retry on IntegrityError, state-machine
ValueErrors, bid item_id mismatch, settlement dedupe by deal/bid, and the
"deal stays AGREED until exchange_credentials" semantics.
"""

import pytest
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.commerce import (
    AppointmentStatus,
    BulkingBid, BidStatus,
    BulkingJobRole, BulkingJobStatus,
    PackingStatus,
    CourierJobStatus,
    Deal, DealStatus,
    Payment, PaymentMethod, PaymentStatus,
    RegisterStatus,
    Settlement, SettlementStatus,
    WarehouseBookingStatus,
)
from app.models.taxonomy import TaxonomyItem
from app.models.tracking import Warehouse
from app.models.certificate import CertificateType
from app.services import commerce_service
from app.services.commerce_service import (
    book_appointment,
    book_warehouse,
    calculate_settlements,
    close_deal,
    confirm_payment,
    create_bulking_register,
    create_job_assignment,
    create_packing_record,
    exchange_credentials,
    initiate_payment,
    list_job_assignments,
    list_job_candidates,
    list_packing_records,
    list_settlements,
    mark_settlement_paid,
    post_courier_job,
    submit_bid,
    update_appointment_status,
    update_courier_job_status,
    update_job_assignment_status,
    update_packing_status,
    update_register_status,
    update_warehouse_booking_status,
)


async def _make_warehouse(db: AsyncSession, code: str, is_active: bool = True) -> Warehouse:
    wh = Warehouse(code=code, name=f"Warehouse {code}", is_active=is_active)
    db.add(wh)
    await db.commit()
    await db.refresh(wh)
    return wh


# ── Registers ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_bulking_register_success(db: AsyncSession, admin_user, taxonomy_item):
    register = await create_bulking_register(
        db, admin_user, taxonomy_item.id, target_quantity=1000, unit="kg",
        target_price=1.5, currency="USD", region="Nairobi",
    )
    assert register.id is not None
    assert register.status == RegisterStatus.DRAFT
    assert register.register_number.startswith("BR-")
    assert register.buyer_id == admin_user.id
    assert register.item_id == taxonomy_item.id
    assert register.target_quantity == 1000


@pytest.mark.asyncio
async def test_create_bulking_register_viewer_denied(db: AsyncSession, viewer_user, taxonomy_item):
    with pytest.raises(PermissionError):
        await create_bulking_register(db, viewer_user, taxonomy_item.id, target_quantity=100)


@pytest.mark.asyncio
async def test_create_bulking_register_validation(db: AsyncSession, admin_user, taxonomy_item):
    with pytest.raises(ValueError, match="target_quantity"):
        await create_bulking_register(db, admin_user, taxonomy_item.id, target_quantity=0)
    with pytest.raises(ValueError, match="TaxonomyItem"):
        await create_bulking_register(db, admin_user, 99999, target_quantity=100)


@pytest.mark.asyncio
async def test_register_number_retry_on_collision(db: AsyncSession, admin_user, taxonomy_item, monkeypatch):
    """First generated register_number collides; retry generates a fresh one."""
    seed = await create_bulking_register(db, admin_user, taxonomy_item.id, target_quantity=1)
    seed.register_number = "BR-COLLIDE-0001"
    await db.commit()
    await db.refresh(admin_user)

    calls = {"n": 0}
    def fake_register_number() -> str:
        calls["n"] += 1
        return "BR-COLLIDE-0001" if calls["n"] == 1 else "BR-UNIQUE-0001"
    monkeypatch.setattr(commerce_service, "_register_number", fake_register_number)

    register = await create_bulking_register(db, admin_user, taxonomy_item.id, target_quantity=500)
    assert register.register_number == "BR-UNIQUE-0001"
    assert calls["n"] >= 2


@pytest.mark.asyncio
async def test_register_number_raises_after_5_collisions(db: AsyncSession, admin_user, taxonomy_item, monkeypatch):
    seed = await create_bulking_register(db, admin_user, taxonomy_item.id, target_quantity=1)
    seed.register_number = "BR-COLLIDE-0001"
    await db.commit()
    await db.refresh(admin_user)

    monkeypatch.setattr(commerce_service, "_register_number", lambda: "BR-COLLIDE-0001")
    with pytest.raises(IntegrityError):
        await create_bulking_register(db, admin_user, taxonomy_item.id, target_quantity=500)


@pytest.mark.asyncio
async def test_register_status_valid_transitions(db: AsyncSession, admin_user, taxonomy_item):
    register = await create_bulking_register(db, admin_user, taxonomy_item.id, target_quantity=500)
    register = await update_register_status(db, admin_user, register.id, RegisterStatus.SOURCING)
    assert register.status == RegisterStatus.SOURCING
    register = await update_register_status(db, admin_user, register.id, RegisterStatus.AGGREGATED)
    assert register.status == RegisterStatus.AGGREGATED
    register = await update_register_status(db, admin_user, register.id, RegisterStatus.CLOSED)
    assert register.status == RegisterStatus.CLOSED


@pytest.mark.asyncio
async def test_register_status_invalid_transition(db: AsyncSession, admin_user, taxonomy_item):
    register = await create_bulking_register(db, admin_user, taxonomy_item.id, target_quantity=500)
    await update_register_status(db, admin_user, register.id, RegisterStatus.CLOSED)
    with pytest.raises(ValueError, match="Cannot transition register"):
        await update_register_status(db, admin_user, register.id, RegisterStatus.SOURCING)


# ── Appointments ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_appointment_workflow_and_transitions(db: AsyncSession, admin_user):
    a = await book_appointment(
        db, admin_user, participant_name="Farmer Joe",
        scheduled_at=datetime.now(timezone.utc),
    )
    assert a.status == AppointmentStatus.REQUESTED

    # REQUESTED -> COMPLETED is not a valid transition
    with pytest.raises(ValueError, match="Cannot transition appointment"):
        await update_appointment_status(db, admin_user, a.id, AppointmentStatus.COMPLETED)

    a = await update_appointment_status(db, admin_user, a.id, AppointmentStatus.CONFIRMED)
    assert a.status == AppointmentStatus.CONFIRMED

    a = await update_appointment_status(db, admin_user, a.id, AppointmentStatus.COMPLETED)
    assert a.status == AppointmentStatus.COMPLETED


# ── Contacts & bids ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_submit_bid_item_mismatch(db: AsyncSession, admin_user, taxonomy_item):
    other = TaxonomyItem(node_id=taxonomy_item.node_id, code="TEST-ITEM-002", common_name="Other Item")
    db.add(other)
    await db.commit()
    await db.refresh(other)

    register = await create_bulking_register(db, admin_user, taxonomy_item.id, target_quantity=500)
    with pytest.raises(ValueError, match="does not match the register's item"):
        await submit_bid(db, admin_user, register.id, quantity=100, unit_price=2.0, item_id=other.id)


@pytest.mark.asyncio
async def test_bid_transitions_and_final_state(db: AsyncSession, admin_user, taxonomy_item):
    register = await create_bulking_register(db, admin_user, taxonomy_item.id, target_quantity=500)
    bid = await submit_bid(db, admin_user, register.id, quantity=100, unit_price=2.0)
    assert bid.status == BidStatus.PENDING

    bid = await commerce_service.accept_bid(db, admin_user, bid.id)
    assert bid.status == BidStatus.ACCEPTED

    with pytest.raises(ValueError, match="Cannot transition bid"):
        await commerce_service.accept_bid(db, admin_user, bid.id)


@pytest.mark.asyncio
async def test_submit_bid_on_closed_register(db: AsyncSession, admin_user, taxonomy_item):
    register = await create_bulking_register(db, admin_user, taxonomy_item.id, target_quantity=500)
    await update_register_status(db, admin_user, register.id, RegisterStatus.CLOSED)
    with pytest.raises(ValueError, match="Cannot bid"):
        await submit_bid(db, admin_user, register.id, quantity=100, unit_price=2.0)


# ── Warehousing & courier ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_warehouse_booking_and_transition(db: AsyncSession, admin_user, taxonomy_item):
    wh = await _make_warehouse(db, "WH-TEST-1")
    register = await create_bulking_register(db, admin_user, taxonomy_item.id, target_quantity=500)

    booking = await book_warehouse(db, admin_user, register.id, wh.id, quantity=200)
    assert booking.status == WarehouseBookingStatus.REQUESTED

    booking = await update_warehouse_booking_status(db, admin_user, booking.id, WarehouseBookingStatus.CONFIRMED)
    assert booking.status == WarehouseBookingStatus.CONFIRMED

    with pytest.raises(ValueError, match="Cannot transition warehouse booking"):
        await update_warehouse_booking_status(db, admin_user, booking.id, WarehouseBookingStatus.REQUESTED)

    booking = await update_warehouse_booking_status(db, admin_user, booking.id, WarehouseBookingStatus.IN_USE)
    assert booking.status == WarehouseBookingStatus.IN_USE


@pytest.mark.asyncio
async def test_book_warehouse_inactive_denied(db: AsyncSession, admin_user, taxonomy_item):
    wh = await _make_warehouse(db, "WH-INACTIVE", is_active=False)
    register = await create_bulking_register(db, admin_user, taxonomy_item.id, target_quantity=500)
    with pytest.raises(ValueError, match="not active"):
        await book_warehouse(db, admin_user, register.id, wh.id, quantity=200)


@pytest.mark.asyncio
async def test_courier_job_workflow(db: AsyncSession, admin_user, taxonomy_item):
    register = await create_bulking_register(db, admin_user, taxonomy_item.id, target_quantity=500)
    job = await post_courier_job(db, admin_user, register.id, pickup_location="Nairobi")
    assert job.status == CourierJobStatus.POSTED
    assert job.tracking_code

    job = await update_courier_job_status(db, admin_user, job.id, CourierJobStatus.ASSIGNED)
    assert job.status == CourierJobStatus.ASSIGNED

    with pytest.raises(ValueError, match="Cannot transition courier job"):
        await update_courier_job_status(db, admin_user, job.id, CourierJobStatus.DELIVERED)

    job = await update_courier_job_status(db, admin_user, job.id, CourierJobStatus.IN_TRANSIT)
    job = await update_courier_job_status(db, admin_user, job.id, CourierJobStatus.DELIVERED)
    assert job.status == CourierJobStatus.DELIVERED
    assert job.delivered_at is not None


# ── Deals & credential exchange ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_close_deal_stays_agreed_until_exchange(db: AsyncSession, admin_user, taxonomy_item):
    register = await create_bulking_register(db, admin_user, taxonomy_item.id, target_quantity=500)
    result = await close_deal(db, admin_user, register.id, quantity=100, unit_price=3.0)

    deal_id = result["deal"]["id"]
    assert result["deal"]["status"] == DealStatus.AGREED.value
    assert result["deal"]["credentials_exchanged"] is False
    assert result["settlement_created"] is True
    assert Decimal(str(result["deal"]["total_value"])) == Decimal("300.00")

    deal = await db.get(Deal, deal_id)
    assert deal.status == DealStatus.AGREED
    assert deal.credentials_exchanged is False

    ex = await exchange_credentials(db, admin_user, deal_id)
    assert ex["credentials_exchanged"] is True

    deal = await db.get(Deal, deal_id)
    assert deal.status == DealStatus.CLOSED
    assert deal.credentials_exchanged is True
    assert deal.closed_at is not None

    # Second exchange is idempotent
    ex2 = await exchange_credentials(db, admin_user, deal_id)
    assert ex2["credentials_exchanged"] is True


# ── Settlements ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_settlement_dedupe_by_deal(db: AsyncSession, admin_user, taxonomy_item):
    register = await create_bulking_register(db, admin_user, taxonomy_item.id, target_quantity=500)
    await close_deal(db, admin_user, register.id, quantity=100, unit_price=3.0)

    # close_deal already created the settlement; recalculating must not duplicate
    result = await calculate_settlements(db, admin_user, register.id)
    assert result["settlements_created"] == 0

    settlements = await list_settlements(db, admin_user, register.id)
    assert len(settlements) == 1
    assert settlements[0]["deal_id"] is not None
    assert settlements[0]["bid_id"] is None
    assert settlements[0]["status"] == SettlementStatus.PENDING.value


@pytest.mark.asyncio
async def test_settlement_dedupe_by_bid(db: AsyncSession, admin_user, taxonomy_item):
    register = await create_bulking_register(db, admin_user, taxonomy_item.id, target_quantity=500)
    bid = await submit_bid(db, admin_user, register.id, quantity=100, unit_price=2.0)
    await commerce_service.accept_bid(db, admin_user, bid.id)

    result = await calculate_settlements(db, admin_user, register.id)
    assert result["settlements_created"] == 1

    # Second run must not duplicate the bid settlement
    result = await calculate_settlements(db, admin_user, register.id)
    assert result["settlements_created"] == 0

    settlements = await list_settlements(db, admin_user, register.id)
    assert len(settlements) == 1
    assert settlements[0]["bid_id"] == bid.id
    assert settlements[0]["deal_id"] is None
    assert Decimal(str(settlements[0]["gross_amount"])) == Decimal("200.00")
    assert Decimal(str(settlements[0]["platform_fee"])) == Decimal("5.00")
    assert Decimal(str(settlements[0]["net_amount"])) == Decimal("195.00")


@pytest.mark.asyncio
async def test_pending_bid_does_not_create_settlement(db: AsyncSession, admin_user, taxonomy_item):
    register = await create_bulking_register(db, admin_user, taxonomy_item.id, target_quantity=500)
    await submit_bid(db, admin_user, register.id, quantity=100, unit_price=2.0)
    result = await calculate_settlements(db, admin_user, register.id)
    assert result["settlements_created"] == 0


# ── Payments ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_payment_workflow_and_settlement_linkage(db: AsyncSession, admin_user, taxonomy_item):
    register = await create_bulking_register(db, admin_user, taxonomy_item.id, target_quantity=500)
    await close_deal(db, admin_user, register.id, quantity=100, unit_price=3.0)
    settlements = await list_settlements(db, admin_user, register.id)
    settlement_id = settlements[0]["id"]

    payment = await initiate_payment(
        db, admin_user, amount=300.0, currency="USD", method=PaymentMethod.STRIPE,
        register_id=register.id,
    )
    assert payment.status == PaymentStatus.PENDING
    assert payment.provider_reference.startswith("STRIPE-")

    # Cannot settle with a non-succeeded payment
    with pytest.raises(ValueError, match="Only succeeded payments"):
        await mark_settlement_paid(db, admin_user, settlement_id, payment_id=payment.id)

    payment = await confirm_payment(db, admin_user, payment.id)
    assert payment.status == PaymentStatus.SUCCEEDED

    # Confirming twice is an invalid transition
    with pytest.raises(ValueError, match="Cannot transition payment"):
        await confirm_payment(db, admin_user, payment.id)

    settled = await mark_settlement_paid(db, admin_user, settlement_id, payment_id=payment.id)
    assert settled.status == SettlementStatus.PAID
    assert settled.payment_id == payment.id
    assert settled.settled_at is not None


@pytest.mark.asyncio
async def test_payment_register_mismatch_rejected(db: AsyncSession, admin_user, taxonomy_item):
    r1 = await create_bulking_register(db, admin_user, taxonomy_item.id, target_quantity=500)
    r2 = await create_bulking_register(db, admin_user, taxonomy_item.id, target_quantity=600)
    await close_deal(db, admin_user, r1.id, quantity=100, unit_price=3.0)
    settlements = await list_settlements(db, admin_user, r1.id)
    settlement_id = settlements[0]["id"]

    payment = await initiate_payment(
        db, admin_user, amount=300.0, currency="USD", method=PaymentMethod.CASH,
        register_id=r2.id,
    )
    await confirm_payment(db, admin_user, payment.id)
    with pytest.raises(ValueError, match="does not belong to the settlement's register"):
        await mark_settlement_paid(db, admin_user, settlement_id, payment_id=payment.id)


# ── Auto-aggregation ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_auto_aggregate_register(db: AsyncSession, admin_user, taxonomy_item):
    register = await create_bulking_register(
        db, admin_user, taxonomy_item.id, target_quantity=1000,
        target_price=1.5, region="Nairobi", auto_generate=True,
    )
    assert register.status == RegisterStatus.AGGREGATED
    assert register.generated is True

    bids = (await db.execute(select(BulkingBid).where(BulkingBid.register_id == register.id))).scalars().all()
    assert len(bids) == 5
    assert all(b.status == BidStatus.PENDING for b in bids)


# ── Pipeline jobs (Clerks, Verifiers, Couriers) ─────────────────────────────

@pytest.mark.asyncio
async def test_create_job_assignment_and_candidates(db: AsyncSession, admin_user, enterprise_user, viewer_user, taxonomy_item):
    register = await create_bulking_register(db, admin_user, taxonomy_item.id, target_quantity=500)

    candidates = await list_job_candidates(db, admin_user, register.id)
    ids = {c["id"] for c in candidates}
    assert enterprise_user.id in ids
    assert viewer_user.id in ids
    assert admin_user.id not in ids  # buyer excluded

    assignment = await create_job_assignment(
        db, admin_user, register.id, BulkingJobRole.VERIFIER,
        assignee_id=enterprise_user.id, notes="Inspect quality grade",
    )
    assert assignment.status == BulkingJobStatus.ASSIGNED
    assert assignment.role == BulkingJobRole.VERIFIER
    assert assignment.assignee_name == enterprise_user.full_name
    assert assignment.item_id == taxonomy_item.id

    rows = await list_job_assignments(db, admin_user, register.id)
    assert len(rows) == 1
    assert rows[0]["assignee_id"] == enterprise_user.id


@pytest.mark.asyncio
async def test_create_job_assignment_requires_name(db: AsyncSession, admin_user, taxonomy_item):
    register = await create_bulking_register(db, admin_user, taxonomy_item.id, target_quantity=500)
    with pytest.raises(ValueError, match="assignee_name"):
        await create_job_assignment(db, admin_user, register.id, BulkingJobRole.CLERK)


@pytest.mark.asyncio
async def test_job_assignment_foreign_register_denied(db: AsyncSession, admin_user, viewer_user, enterprise_user, taxonomy_item):
    register = await create_bulking_register(db, admin_user, taxonomy_item.id, target_quantity=500)
    with pytest.raises(PermissionError):
        await create_job_assignment(db, viewer_user, register.id, BulkingJobRole.COURIER)


@pytest.mark.asyncio
async def test_job_assignment_transitions(db: AsyncSession, admin_user, enterprise_user, taxonomy_item):
    register = await create_bulking_register(db, admin_user, taxonomy_item.id, target_quantity=500)
    assignment = await create_job_assignment(
        db, admin_user, register.id, BulkingJobRole.COURIER,
        assignee_id=enterprise_user.id,
    )

    # ASSIGNED -> COMPLETED is invalid (must pass through IN_PROGRESS)
    with pytest.raises(ValueError, match="Cannot transition job assignment"):
        await update_job_assignment_status(db, admin_user, assignment.id, BulkingJobStatus.COMPLETED)

    assignment = await update_job_assignment_status(db, admin_user, assignment.id, BulkingJobStatus.IN_PROGRESS)
    assert assignment.status == BulkingJobStatus.IN_PROGRESS

    assignment = await update_job_assignment_status(db, admin_user, assignment.id, BulkingJobStatus.COMPLETED)
    assert assignment.status == BulkingJobStatus.COMPLETED
    assert assignment.completed_at is not None


# ── Packing & certification ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_and_certify_packing_record(db: AsyncSession, admin_user, taxonomy_item):
    register = await create_bulking_register(db, admin_user, taxonomy_item.id, target_quantity=500)
    record = await create_packing_record(
        db, admin_user, register.id, quantity=450, unit="kg",
        package_type="carton", package_count=90, total_weight_kg=510,
    )
    assert record.status == PackingStatus.PACKED
    assert record.packed_by_name == admin_user.full_name

    cert = await issue_packing_certificate(db, admin_user, taxonomy_item.id)
    record = await update_packing_status(
        db, admin_user, record.id, PackingStatus.CERTIFIED,
        certificate_id=cert.certificate_id,
    )
    assert record.status == PackingStatus.CERTIFIED
    assert record.certificate_id == cert.certificate_id


@pytest.mark.asyncio
async def test_create_packing_record_validation(db: AsyncSession, admin_user, taxonomy_item):
    register = await create_bulking_register(db, admin_user, taxonomy_item.id, target_quantity=500)
    with pytest.raises(ValueError, match="quantity"):
        await create_packing_record(db, admin_user, register.id, quantity=0)


@pytest.mark.asyncio
async def test_certify_packing_without_certificate_rejected(db: AsyncSession, admin_user, taxonomy_item):
    register = await create_bulking_register(db, admin_user, taxonomy_item.id, target_quantity=500)
    record = await create_packing_record(db, admin_user, register.id, quantity=450)
    with pytest.raises(ValueError, match="certificate_id"):
        await update_packing_status(db, admin_user, record.id, PackingStatus.CERTIFIED)


@pytest.mark.asyncio
async def test_packing_records_listed(db: AsyncSession, admin_user, taxonomy_item):
    register = await create_bulking_register(db, admin_user, taxonomy_item.id, target_quantity=500)
    await create_packing_record(db, admin_user, register.id, quantity=100)
    await create_packing_record(db, admin_user, register.id, quantity=150)
    rows = await list_packing_records(db, admin_user, register.id)
    assert len(rows) == 2


from app.services.certificate_service import issue_certificate as _issue_certificate


async def issue_packing_certificate(db, user, item_id) -> "Certificate":
    cert = await _issue_certificate(
        db, user, product_id=None, cert_type=CertificateType.QUALITY,
        issuing_body="FoodTrack Labs", recipient_entity="Bulked Stock",
        description="Quality certificate for bulked lot",
        expiry_date=None, document_url=None, metadata_json=None,
        item_id=item_id,
    )
    return cert
