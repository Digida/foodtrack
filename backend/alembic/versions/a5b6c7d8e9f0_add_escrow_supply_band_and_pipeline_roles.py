"""add escrow, supply band and expanded pipeline roles

Adds investor escrow on bulking registers (30% abundant / 65% rare), the item
supply band that drives it, the sourcing entity on a register (for the
same-company-no-self-certify rule) and the buyer-delivery courier flag.

Revision ID: a5b6c7d8e9f0
Revises: f2e3d4a5b6c7
Create Date: 2026-08-03
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "a5b6c7d8e9f0"
down_revision: Union[str, None] = "f2e3d4a5b6c7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── taxonomy_items: supply_band ─────────────────────────────────────────
    # NOTE: SAEnum(str-mixin enum) persists the member NAME (uppercase), so the
    # column must be declared with uppercase values and backfilled uppercase to
    # avoid a LookupError on load ("'abundant' is not among the defined enum
    # values ... Possible values: ABUNDANT, RARE").
    op.add_column(
        "taxonomy_items",
        sa.Column("supply_band", sa.Enum("ABUNDANT", "RARE", name="itemsupplyband", native_enum=False), nullable=True),
    )
    # Existing catalog items default to the abundant band (rare is opted-in per item)
    op.execute("UPDATE taxonomy_items SET supply_band = 'ABUNDANT' WHERE supply_band IS NULL")

    # ── bulking_registers: sourcing entity ──────────────────────────────────
    # batch mode keeps this migration runnable on SQLite (dev/scratch); on
    # PostgreSQL it executes the same ops directly.
    with op.batch_alter_table("bulking_registers") as batch_op:
        batch_op.add_column(
            sa.Column(
                "sourcing_entity_id",
                sa.Integer,
                sa.ForeignKey("users.id", name="fk_bulking_registers_sourcing_entity_id_users"),
                nullable=True,
            ),
        )
        batch_op.create_index(
            "ix_bulking_registers_sourcing_entity_id", ["sourcing_entity_id"]
        )
        batch_op.add_column(
            sa.Column("sourcing_entity_name", sa.String(255), nullable=True),
        )

    # ── courier_jobs: buyer delivery flag ───────────────────────────────────
    with op.batch_alter_table("courier_jobs") as batch_op:
        batch_op.add_column(
            sa.Column("deliver_to_buyer", sa.Boolean, nullable=False, server_default=sa.text("0")),
        )

    # ── bulking_escrows ─────────────────────────────────────────────────────
    op.create_table(
        "bulking_escrows",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("register_id", sa.Integer, sa.ForeignKey("bulking_registers.id"), nullable=False, index=True),
        sa.Column("item_id", sa.Integer, sa.ForeignKey("taxonomy_items.id"), nullable=False, index=True),
        sa.Column("tenant_id", sa.Integer, sa.ForeignKey("tenants.id"), nullable=True, index=True),
        sa.Column("payer_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("percentage", sa.Numeric(5, 2), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("currency", sa.String(10), nullable=True),
        sa.Column("status", sa.Enum("REQUIRED", "DEPOSITED", "HELD", "RELEASED", "REFUNDED", name="escrowstatus", native_enum=False), default="REQUIRED"),
        sa.Column("payment_id", sa.Integer, sa.ForeignKey("commerce_payments.id"), nullable=True, index=True),
        sa.Column("deposited_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("bulking_escrows")
    with op.batch_alter_table("courier_jobs") as batch_op:
        batch_op.drop_column("deliver_to_buyer")
    with op.batch_alter_table("bulking_registers") as batch_op:
        batch_op.drop_column("sourcing_entity_name")
        batch_op.drop_column("sourcing_entity_id")
    op.drop_column("taxonomy_items", "supply_band")
