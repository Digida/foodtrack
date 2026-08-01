"""add commerce & bulking pipeline tables

Revision ID: b1c2d3e4f5a6
Revises: a1b2c3d4e5f6
Create Date: 2026-08-01
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "b1c2d3e4f5a6"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

MONEY = sa.Numeric(18, 2)


def upgrade() -> None:
    # ── appointments ──────────────────────────────────────────────────────
    op.create_table(
        "appointments",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("buyer_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("tenant_id", sa.Integer, sa.ForeignKey("tenants.id"), nullable=True, index=True),
        sa.Column("participant_type", sa.String(50), nullable=True),
        sa.Column("participant_name", sa.String(255), nullable=False),
        sa.Column("participant_phone", sa.String(50), nullable=True),
        sa.Column("participant_email", sa.String(255), nullable=True),
        sa.Column("purpose", sa.String(500), nullable=True),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_minutes", sa.Integer, default=60),
        sa.Column("channel", sa.String(50), nullable=True),
        sa.Column("location", sa.String(255), nullable=True),
        sa.Column("status", sa.Enum("requested", "confirmed", "completed", "cancelled", name="appointmentstatus", native_enum=False), default="requested"),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_by", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )

    # ── bulking_registers ─────────────────────────────────────────────────
    op.create_table(
        "bulking_registers",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("register_number", sa.String(50), unique=True, index=True, nullable=False),
        sa.Column("buyer_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("tenant_id", sa.Integer, sa.ForeignKey("tenants.id"), nullable=True, index=True),
        sa.Column("item_id", sa.Integer, sa.ForeignKey("taxonomy_items.id"), nullable=False, index=True),
        sa.Column("title", sa.String(255), nullable=True),
        sa.Column("target_quantity", sa.Float, nullable=False),
        sa.Column("unit", sa.String(50), nullable=True),
        sa.Column("target_price", MONEY, nullable=True),
        sa.Column("currency", sa.String(10), default="USD"),
        sa.Column("region", sa.String(255), nullable=True),
        sa.Column("sourcing_mode", sa.Enum("self", "cooperative", "aggregator_network", "marketplace", name="sourcingmode", native_enum=False), default="self"),
        sa.Column("status", sa.Enum("draft", "sourcing", "aggregated", "closed", "cancelled", name="registerstatus", native_enum=False), default="draft"),
        sa.Column("generated", sa.Boolean, default=False),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_by", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )

    # ── bulking_contacts ──────────────────────────────────────────────────
    op.create_table(
        "bulking_contacts",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("register_id", sa.Integer, sa.ForeignKey("bulking_registers.id"), nullable=False, index=True),
        sa.Column("tenant_id", sa.Integer, sa.ForeignKey("tenants.id"), nullable=True, index=True),
        sa.Column("contact_type", sa.Enum("farmer", "cooperative", "aggregator", "trader", name="contacttype", native_enum=False), default="farmer"),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("phone", sa.String(50), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("location", sa.String(255), nullable=True),
        sa.Column("is_primary", sa.Boolean, default=False),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    )

    # ── bulking_bids ──────────────────────────────────────────────────────
    op.create_table(
        "bulking_bids",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("register_id", sa.Integer, sa.ForeignKey("bulking_registers.id"), nullable=False, index=True),
        sa.Column("contact_id", sa.Integer, sa.ForeignKey("bulking_contacts.id"), nullable=True, index=True),
        sa.Column("item_id", sa.Integer, sa.ForeignKey("taxonomy_items.id"), nullable=False, index=True),
        sa.Column("tenant_id", sa.Integer, sa.ForeignKey("tenants.id"), nullable=True, index=True),
        sa.Column("quantity", sa.Float, nullable=False),
        sa.Column("unit", sa.String(50), nullable=True),
        sa.Column("unit_price", MONEY, nullable=False),
        sa.Column("currency", sa.String(10), default="USD"),
        sa.Column("quality_grade", sa.String(100), nullable=True),
        sa.Column("status", sa.Enum("pending", "accepted", "rejected", "withdrawn", name="bidstatus", native_enum=False), default="pending"),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )

    # ── warehouse_bookings ────────────────────────────────────────────────
    op.create_table(
        "warehouse_bookings",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("register_id", sa.Integer, sa.ForeignKey("bulking_registers.id"), nullable=False, index=True),
        sa.Column("warehouse_id", sa.Integer, sa.ForeignKey("warehouses.id"), nullable=False, index=True),
        sa.Column("tenant_id", sa.Integer, sa.ForeignKey("tenants.id"), nullable=True, index=True),
        sa.Column("start_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("end_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("quantity", sa.Float, nullable=True),
        sa.Column("unit", sa.String(50), nullable=True),
        sa.Column("storage_cost", MONEY, nullable=True),
        sa.Column("currency", sa.String(10), default="USD"),
        sa.Column("status", sa.Enum("requested", "confirmed", "in_use", "completed", "cancelled", name="warehousebookingstatus", native_enum=False), default="requested"),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    )

    # ── courier_jobs ──────────────────────────────────────────────────────
    op.create_table(
        "courier_jobs",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("register_id", sa.Integer, sa.ForeignKey("bulking_registers.id"), nullable=False, index=True),
        sa.Column("item_id", sa.Integer, sa.ForeignKey("taxonomy_items.id"), nullable=False, index=True),
        sa.Column("tenant_id", sa.Integer, sa.ForeignKey("tenants.id"), nullable=True, index=True),
        sa.Column("pickup_location", sa.String(255), nullable=True),
        sa.Column("dropoff_warehouse_id", sa.Integer, sa.ForeignKey("warehouses.id"), nullable=True, index=True),
        sa.Column("quantity", sa.Float, nullable=True),
        sa.Column("unit", sa.String(50), nullable=True),
        sa.Column("weight_kg", sa.Float, nullable=True),
        sa.Column("budget", MONEY, nullable=True),
        sa.Column("currency", sa.String(10), default="USD"),
        sa.Column("status", sa.Enum("posted", "assigned", "in_transit", "delivered", "cancelled", name="courierjobstatus", native_enum=False), default="posted"),
        sa.Column("courier_name", sa.String(255), nullable=True),
        sa.Column("tracking_code", sa.String(255), nullable=True, index=True),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    )

    # ── commerce_deals ────────────────────────────────────────────────────
    op.create_table(
        "commerce_deals",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("register_id", sa.Integer, sa.ForeignKey("bulking_registers.id"), nullable=False, index=True),
        sa.Column("buyer_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("seller_contact_id", sa.Integer, sa.ForeignKey("bulking_contacts.id"), nullable=True, index=True),
        sa.Column("item_id", sa.Integer, sa.ForeignKey("taxonomy_items.id"), nullable=False, index=True),
        sa.Column("tenant_id", sa.Integer, sa.ForeignKey("tenants.id"), nullable=True, index=True),
        sa.Column("quantity", sa.Float, nullable=False),
        sa.Column("unit", sa.String(50), nullable=True),
        sa.Column("unit_price", MONEY, nullable=False),
        sa.Column("total_value", MONEY, nullable=False),
        sa.Column("currency", sa.String(10), default="USD"),
        sa.Column("status", sa.Enum("negotiating", "agreed", "closed", "cancelled", name="dealstatus", native_enum=False), default="closed"),
        sa.Column("credentials_exchanged", sa.Boolean, default=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )

    # ── commerce_payments ─────────────────────────────────────────────────
    op.create_table(
        "commerce_payments",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("register_id", sa.Integer, sa.ForeignKey("bulking_registers.id"), nullable=True, index=True),
        sa.Column("deal_id", sa.Integer, sa.ForeignKey("commerce_deals.id"), nullable=True, index=True),
        sa.Column("payer_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("payee_id", sa.Integer, sa.ForeignKey("users.id"), nullable=True, index=True),
        sa.Column("tenant_id", sa.Integer, sa.ForeignKey("tenants.id"), nullable=True, index=True),
        sa.Column("amount", MONEY, nullable=False),
        sa.Column("currency", sa.String(10), default="USD"),
        sa.Column("method", sa.Enum("stripe", "mpesa", "airtel_money", "mtn_momo", "visa", "mastercard", "bank_transfer", "cash", name="paymentmethod", native_enum=False), nullable=False),
        sa.Column("provider_reference", sa.String(255), nullable=True, index=True),
        sa.Column("status", sa.Enum("pending", "processing", "succeeded", "failed", "refunded", name="paymentstatus", native_enum=False), default="pending"),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    )

    # ── commerce_settlements ──────────────────────────────────────────────
    op.create_table(
        "commerce_settlements",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("register_id", sa.Integer, sa.ForeignKey("bulking_registers.id"), nullable=False, index=True),
        sa.Column("deal_id", sa.Integer, sa.ForeignKey("commerce_deals.id"), nullable=True, index=True),
        sa.Column("bid_id", sa.Integer, sa.ForeignKey("bulking_bids.id"), nullable=True, index=True),
        sa.Column("payee_id", sa.Integer, sa.ForeignKey("users.id"), nullable=True, index=True),
        sa.Column("payee_name", sa.String(255), nullable=True),
        sa.Column("item_id", sa.Integer, sa.ForeignKey("taxonomy_items.id"), nullable=False, index=True),
        sa.Column("tenant_id", sa.Integer, sa.ForeignKey("tenants.id"), nullable=True, index=True),
        sa.Column("quantity", sa.Float, nullable=False),
        sa.Column("unit_price", MONEY, nullable=False),
        sa.Column("gross_amount", MONEY, nullable=False),
        sa.Column("platform_fee", MONEY, default=0.0),
        sa.Column("net_amount", MONEY, nullable=False),
        sa.Column("currency", sa.String(10), default="USD"),
        sa.Column("status", sa.Enum("pending", "paid", "failed", "cancelled", name="settlementstatus", native_enum=False), default="pending"),
        sa.Column("payment_id", sa.Integer, sa.ForeignKey("commerce_payments.id"), nullable=True, index=True),
        sa.Column("settled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("commerce_settlements")
    op.drop_table("commerce_payments")
    op.drop_table("commerce_deals")
    op.drop_table("courier_jobs")
    op.drop_table("warehouse_bookings")
    op.drop_table("bulking_bids")
    op.drop_table("bulking_contacts")
    op.drop_table("bulking_registers")
    op.drop_table("appointments")
