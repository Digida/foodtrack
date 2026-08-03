"""Commerce & Bulking Pipeline models.

Covers the buyer-facing aggregation layer that sits on top of the item-centric
supply chain: appointment bookings, bulking registers (contacts + bids), warehouse
bookings, courier jobs, deal closing with credential exchange, settlements and
multi-provider payments.

Every record resolves back to a TaxonomyItem so the item-first architecture is
preserved: a register, bid, deal, courier job and settlement all reference the
food item they move.
"""
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Boolean, Numeric, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import relationship
import enum

from app.database import Base

MONEY = Numeric(18, 2)


class AppointmentStatus(str, enum.Enum):
    REQUESTED = "requested"
    CONFIRMED = "confirmed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class SourcingMode(str, enum.Enum):
    SELF = "self"
    COOPERATIVE = "cooperative"
    AGGREGATOR_NETWORK = "aggregator_network"
    MARKETPLACE = "marketplace"


class RegisterStatus(str, enum.Enum):
    DRAFT = "draft"
    SOURCING = "sourcing"
    AGGREGATED = "aggregated"
    CLOSED = "closed"
    CANCELLED = "cancelled"


class ContactType(str, enum.Enum):
    FARMER = "farmer"
    COOPERATIVE = "cooperative"
    AGGREGATOR = "aggregator"
    TRADER = "trader"


class BidStatus(str, enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


class DealStatus(str, enum.Enum):
    NEGOTIATING = "negotiating"
    AGREED = "agreed"
    CLOSED = "closed"
    CANCELLED = "cancelled"


class WarehouseBookingStatus(str, enum.Enum):
    REQUESTED = "requested"
    CONFIRMED = "confirmed"
    IN_USE = "in_use"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class CourierJobStatus(str, enum.Enum):
    POSTED = "posted"
    ASSIGNED = "assigned"
    IN_TRANSIT = "in_transit"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class PaymentMethod(str, enum.Enum):
    STRIPE = "stripe"
    MPESA = "mpesa"
    AIRTEL_MONEY = "airtel_money"
    MTN_MOMO = "mtn_momo"
    VISA = "visa"
    MASTERCARD = "mastercard"
    BANK_TRANSFER = "bank_transfer"
    CASH = "cash"


class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    REFUNDED = "refunded"


class SettlementStatus(str, enum.Enum):
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    CANCELLED = "cancelled"


class BulkingJobRole(str, enum.Enum):
    """Pipeline roles assumed by users in the item's locus. Clerks collate and
    receive goods, Verifiers inspect and certify quality, Packers package the
    aggregated lot, Certifiers issue the quality certificate and Couriers move
    stock to the buyer."""
    CLERK = "clerk"
    VERIFIER = "verifier"
    PACKER = "packer"
    CERTIFIER = "certifier"
    COURIER = "courier"


class BulkingJobStatus(str, enum.Enum):
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class PackingStatus(str, enum.Enum):
    PACKED = "packed"
    CERTIFIED = "certified"
    CANCELLED = "cancelled"


class EscrowStatus(str, enum.Enum):
    """Investor escrow lifecycle. The buyer deposits a percentage of the deal
    value up front (30% for abundant items, 65% for rare items); the funds are
    held until the buyer receives the goods, then released to the seller."""
    REQUIRED = "required"
    DEPOSITED = "deposited"
    HELD = "held"
    RELEASED = "released"
    REFUNDED = "refunded"


class Appointment(Base):
    """Booking for an appointment (e.g. a buyer meeting a farmer/cooperative to
    close a deal on aggregated stock)."""
    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True, index=True)
    buyer_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True, index=True)
    participant_type = Column(String(50), nullable=True)
    participant_name = Column(String(255), nullable=False)
    participant_phone = Column(String(50), nullable=True)
    participant_email = Column(String(255), nullable=True)
    purpose = Column(String(500), nullable=True)
    scheduled_at = Column(DateTime(timezone=True), nullable=False)
    duration_minutes = Column(Integer, default=60)
    channel = Column(String(50), nullable=True)
    location = Column(String(255), nullable=True)
    status = Column(SAEnum(AppointmentStatus, native_enum=False), default=AppointmentStatus.REQUESTED)
    notes = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    buyer = relationship("User", foreign_keys=[buyer_id])
    tenant = relationship("Tenant", back_populates="appointments")


class BulkingRegister(Base):
    """A buyer's aggregation campaign: an item, a target volume/price, the sourcing
    strategy and the pipeline state. Contacts, bids, warehouse bookings, courier
    jobs, deals, settlements and payments all hang off a register."""
    __tablename__ = "bulking_registers"

    id = Column(Integer, primary_key=True, index=True)
    register_number = Column(String(50), unique=True, index=True, nullable=False)
    buyer_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True, index=True)
    item_id = Column(Integer, ForeignKey("taxonomy_items.id"), nullable=False, index=True)
    title = Column(String(255), nullable=True)
    target_quantity = Column(Float, nullable=False)
    unit = Column(String(50), nullable=True)
    target_price = Column(MONEY, nullable=True)
    currency = Column(String(10), default="USD")
    region = Column(String(255), nullable=True)
    sourcing_mode = Column(SAEnum(SourcingMode, native_enum=False), default=SourcingMode.SELF)
    # The entity (cooperative / company) that supplies the item through its member
    # users. Used to block same-company self-certification during the pipeline.
    sourcing_entity_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    sourcing_entity_name = Column(String(255), nullable=True)
    status = Column(SAEnum(RegisterStatus, native_enum=False), default=RegisterStatus.DRAFT)
    generated = Column(Boolean, default=False)
    notes = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    buyer = relationship("User", foreign_keys=[buyer_id])
    sourcing_entity = relationship("User", foreign_keys=[sourcing_entity_id])
    item = relationship("TaxonomyItem")
    tenant = relationship("Tenant", back_populates="bulking_registers")
    contacts = relationship("BulkingContact", back_populates="register", cascade="all, delete-orphan")
    bids = relationship("BulkingBid", back_populates="register", cascade="all, delete-orphan")
    warehouse_bookings = relationship("WarehouseBooking", back_populates="register", cascade="all, delete-orphan")
    courier_jobs = relationship("CourierJob", back_populates="register", cascade="all, delete-orphan")
    deals = relationship("Deal", back_populates="register", cascade="all, delete-orphan")
    settlements = relationship("Settlement", back_populates="register", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="register")
    escrows = relationship("BulkingEscrow", back_populates="register", cascade="all, delete-orphan")
    job_assignments = relationship("BulkingJobAssignment", back_populates="register", cascade="all, delete-orphan")
    packing_records = relationship("PackingRecord", back_populates="register", cascade="all, delete-orphan")


class BulkingContact(Base):
    """A farmer, cooperative or aggregator contacted as part of a register's sourcing."""
    __tablename__ = "bulking_contacts"

    id = Column(Integer, primary_key=True, index=True)
    register_id = Column(Integer, ForeignKey("bulking_registers.id"), nullable=False, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True, index=True)
    contact_type = Column(SAEnum(ContactType, native_enum=False), default=ContactType.FARMER)
    name = Column(String(255), nullable=False)
    phone = Column(String(50), nullable=True)
    email = Column(String(255), nullable=True)
    location = Column(String(255), nullable=True)
    is_primary = Column(Boolean, default=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    register = relationship("BulkingRegister", back_populates="contacts")
    tenant = relationship("Tenant", back_populates="bulking_contacts")
    bids = relationship("BulkingBid", back_populates="contact")


class BulkingBid(Base):
    """A bid submitted by a contact (or the platform's auto-aggregation) to sell a
    quantity of an item at a unit price."""
    __tablename__ = "bulking_bids"

    id = Column(Integer, primary_key=True, index=True)
    register_id = Column(Integer, ForeignKey("bulking_registers.id"), nullable=False, index=True)
    contact_id = Column(Integer, ForeignKey("bulking_contacts.id"), nullable=True, index=True)
    item_id = Column(Integer, ForeignKey("taxonomy_items.id"), nullable=False, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True, index=True)
    quantity = Column(Float, nullable=False)
    unit = Column(String(50), nullable=True)
    unit_price = Column(MONEY, nullable=False)
    currency = Column(String(10), default="USD")
    quality_grade = Column(String(100), nullable=True)
    status = Column(SAEnum(BidStatus, native_enum=False), default=BidStatus.PENDING)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    register = relationship("BulkingRegister", back_populates="bids")
    contact = relationship("BulkingContact", back_populates="bids")
    item = relationship("TaxonomyItem")
    tenant = relationship("Tenant", back_populates="bulking_bids")


class WarehouseBooking(Base):
    """Warehousing booked for the aggregated stock of a register."""
    __tablename__ = "warehouse_bookings"

    id = Column(Integer, primary_key=True, index=True)
    register_id = Column(Integer, ForeignKey("bulking_registers.id"), nullable=False, index=True)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=False, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True, index=True)
    start_date = Column(DateTime(timezone=True), nullable=True)
    end_date = Column(DateTime(timezone=True), nullable=True)
    quantity = Column(Float, nullable=True)
    unit = Column(String(50), nullable=True)
    storage_cost = Column(MONEY, nullable=True)
    currency = Column(String(10), default="USD")
    status = Column(SAEnum(WarehouseBookingStatus, native_enum=False), default=WarehouseBookingStatus.REQUESTED)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    register = relationship("BulkingRegister", back_populates="warehouse_bookings")
    warehouse = relationship("Warehouse")
    tenant = relationship("Tenant", back_populates="warehouse_bookings")


class CourierJob(Base):
    """A posted courier job moving aggregated stock from a pickup point to a warehouse."""
    __tablename__ = "courier_jobs"

    id = Column(Integer, primary_key=True, index=True)
    register_id = Column(Integer, ForeignKey("bulking_registers.id"), nullable=False, index=True)
    item_id = Column(Integer, ForeignKey("taxonomy_items.id"), nullable=False, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True, index=True)
    pickup_location = Column(String(255), nullable=True)
    dropoff_warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=True, index=True)
    # Final leg: when True the stock is moved directly to the investing buyer
    # ("received the items they paid for"). Reaching DELIVERED releases escrow.
    deliver_to_buyer = Column(Boolean, default=False)
    quantity = Column(Float, nullable=True)
    unit = Column(String(50), nullable=True)
    weight_kg = Column(Float, nullable=True)
    budget = Column(MONEY, nullable=True)
    currency = Column(String(10), default="USD")
    status = Column(SAEnum(CourierJobStatus, native_enum=False), default=CourierJobStatus.POSTED)
    courier_name = Column(String(255), nullable=True)
    tracking_code = Column(String(255), nullable=True, index=True)
    posted_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    register = relationship("BulkingRegister", back_populates="courier_jobs")
    item = relationship("TaxonomyItem")
    dropoff_warehouse = relationship("Warehouse")
    tenant = relationship("Tenant", back_populates="courier_jobs")


class Deal(Base):
    """A deal closed on aggregated food stock. When a deal closes the two parties
    exchange credentials (emails) so they can transact directly."""
    __tablename__ = "commerce_deals"

    id = Column(Integer, primary_key=True, index=True)
    register_id = Column(Integer, ForeignKey("bulking_registers.id"), nullable=False, index=True)
    buyer_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    seller_contact_id = Column(Integer, ForeignKey("bulking_contacts.id"), nullable=True, index=True)
    item_id = Column(Integer, ForeignKey("taxonomy_items.id"), nullable=False, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True, index=True)
    quantity = Column(Float, nullable=False)
    unit = Column(String(50), nullable=True)
    unit_price = Column(MONEY, nullable=False)
    total_value = Column(MONEY, nullable=False)
    currency = Column(String(10), default="USD")
    status = Column(SAEnum(DealStatus, native_enum=False), default=DealStatus.CLOSED)
    credentials_exchanged = Column(Boolean, default=False)
    closed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    register = relationship("BulkingRegister", back_populates="deals")
    buyer = relationship("User", foreign_keys=[buyer_id])
    seller_contact = relationship("BulkingContact")
    item = relationship("TaxonomyItem")
    tenant = relationship("Tenant", back_populates="deals")
    settlements = relationship("Settlement", back_populates="deal")
    payments = relationship("Payment", back_populates="deal")


class Payment(Base):
    """A payment initiated through a supported provider: Stripe, MPesa, Airtel
    Money, MTN MoMo, Visa, Mastercard, bank transfer or cash."""
    __tablename__ = "commerce_payments"

    id = Column(Integer, primary_key=True, index=True)
    register_id = Column(Integer, ForeignKey("bulking_registers.id"), nullable=True, index=True)
    deal_id = Column(Integer, ForeignKey("commerce_deals.id"), nullable=True, index=True)
    payer_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    payee_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True, index=True)
    amount = Column(MONEY, nullable=False)
    currency = Column(String(10), default="USD")
    method = Column(SAEnum(PaymentMethod, native_enum=False), nullable=False)
    provider_reference = Column(String(255), nullable=True, index=True)
    status = Column(SAEnum(PaymentStatus, native_enum=False), default=PaymentStatus.PENDING)
    paid_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    register = relationship("BulkingRegister", back_populates="payments")
    deal = relationship("Deal", back_populates="payments")
    payer = relationship("User", foreign_keys=[payer_id])
    payee = relationship("User", foreign_keys=[payee_id])
    tenant = relationship("Tenant", back_populates="commerce_payments")
    settlement = relationship("Settlement", back_populates="payment")


class Settlement(Base):
    """Settlement record: what a seller (farmer/cooperative/aggregator) is owed for
    accepted bids/closed deals, net of platform fee."""
    __tablename__ = "commerce_settlements"

    id = Column(Integer, primary_key=True, index=True)
    register_id = Column(Integer, ForeignKey("bulking_registers.id"), nullable=False, index=True)
    deal_id = Column(Integer, ForeignKey("commerce_deals.id"), nullable=True, index=True)
    bid_id = Column(Integer, ForeignKey("bulking_bids.id"), nullable=True, index=True)
    payee_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    payee_name = Column(String(255), nullable=True)
    item_id = Column(Integer, ForeignKey("taxonomy_items.id"), nullable=False, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True, index=True)
    quantity = Column(Float, nullable=False)
    unit_price = Column(MONEY, nullable=False)
    gross_amount = Column(MONEY, nullable=False)
    platform_fee = Column(MONEY, default=0.0)
    net_amount = Column(MONEY, nullable=False)
    currency = Column(String(10), default="USD")
    status = Column(SAEnum(SettlementStatus, native_enum=False), default=SettlementStatus.PENDING)
    payment_id = Column(Integer, ForeignKey("commerce_payments.id"), nullable=True, index=True)
    settled_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    register = relationship("BulkingRegister", back_populates="settlements")
    deal = relationship("Deal", back_populates="settlements")
    bid = relationship("BulkingBid")
    item = relationship("TaxonomyItem")
    tenant = relationship("Tenant", back_populates="settlements")
    payment = relationship("Payment", back_populates="settlement")


class BulkingJobAssignment(Base):
    """A user from the item's locus assigned a pipeline role — Clerk, Verifier,
    Packer, Certifier or Courier — for a bulking register. Job assignments drive
    the receiving, inspection, packing, certification and transport stages of
    the bulking pipeline."""
    __tablename__ = "bulking_job_assignments"

    id = Column(Integer, primary_key=True, index=True)
    register_id = Column(Integer, ForeignKey("bulking_registers.id"), nullable=False, index=True)
    item_id = Column(Integer, ForeignKey("taxonomy_items.id"), nullable=False, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True, index=True)
    role = Column(SAEnum(BulkingJobRole, native_enum=False), nullable=False)
    assignee_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    assignee_name = Column(String(255), nullable=False)
    assignee_location = Column(String(255), nullable=True)
    status = Column(SAEnum(BulkingJobStatus, native_enum=False), default=BulkingJobStatus.ASSIGNED)
    notes = Column(Text, nullable=True)
    assigned_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    register = relationship("BulkingRegister", back_populates="job_assignments")
    item = relationship("TaxonomyItem")
    tenant = relationship("Tenant", back_populates="bulking_job_assignments")
    assignee = relationship("User")


class PackingRecord(Base):
    """Packing record for aggregated (bulked) stock. Goods are packed into
    containers (cartons, crates, pallets) and, once quality is verified, linked
    to a certificate that certifies the packed lot."""
    __tablename__ = "bulking_packing_records"

    id = Column(Integer, primary_key=True, index=True)
    register_id = Column(Integer, ForeignKey("bulking_registers.id"), nullable=False, index=True)
    item_id = Column(Integer, ForeignKey("taxonomy_items.id"), nullable=False, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True, index=True)
    quantity = Column(Float, nullable=False)
    unit = Column(String(50), nullable=True)
    package_type = Column(String(100), nullable=True)
    package_count = Column(Integer, nullable=True)
    total_weight_kg = Column(Float, nullable=True)
    certificate_id = Column(String(100), nullable=True, index=True)
    status = Column(SAEnum(PackingStatus, native_enum=False), default=PackingStatus.PACKED)
    packed_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    packed_by_name = Column(String(255), nullable=True)
    notes = Column(Text, nullable=True)
    packed_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    register = relationship("BulkingRegister", back_populates="packing_records")
    item = relationship("TaxonomyItem")
    tenant = relationship("Tenant", back_populates="packing_records")
    packed_by = relationship("User")


class BulkingEscrow(Base):
    """Investor escrow on a bulking register. The investing buyer deposits a
    percentage of the deal value up front — 30% for abundant items, 65% for
    rare items — before the pipeline runs. Funds are released to the seller
    once the buyer receives the goods (buyer-delivery courier job DELIVERED)."""
    __tablename__ = "bulking_escrows"

    id = Column(Integer, primary_key=True, index=True)
    register_id = Column(Integer, ForeignKey("bulking_registers.id"), nullable=False, index=True)
    item_id = Column(Integer, ForeignKey("taxonomy_items.id"), nullable=False, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True, index=True)
    payer_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    percentage = Column(Numeric(5, 2), nullable=False)
    amount = Column(MONEY, nullable=False)
    currency = Column(String(10), default="USD")
    status = Column(SAEnum(EscrowStatus, native_enum=False), default=EscrowStatus.REQUIRED)
    payment_id = Column(Integer, ForeignKey("commerce_payments.id"), nullable=True, index=True)
    deposited_at = Column(DateTime(timezone=True), nullable=True)
    released_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    register = relationship("BulkingRegister", back_populates="escrows")
    item = relationship("TaxonomyItem")
    payer = relationship("User", foreign_keys=[payer_id])
    tenant = relationship("Tenant", back_populates="bulking_escrows")
    payment = relationship("Payment", foreign_keys=[payment_id])
