"""add bulking job assignments and packing records

Adds the pipeline tables that let users in the item's locus assume roles
(Clerks, Verifiers, Couriers) and record the certification + packing stage
of the bulking pipeline.

Revision ID: f2e3d4a5b6c7
Revises: f0f1f2f3f4f5
Create Date: 2026-08-01
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "f2e3d4a5b6c7"
down_revision: Union[str, None] = "f0f1f2f3f4f5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── bulking_job_assignments ────────────────────────────────────────────
    op.create_table(
        "bulking_job_assignments",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("register_id", sa.Integer, sa.ForeignKey("bulking_registers.id"), nullable=False, index=True),
        sa.Column("item_id", sa.Integer, sa.ForeignKey("taxonomy_items.id"), nullable=False, index=True),
        sa.Column("tenant_id", sa.Integer, sa.ForeignKey("tenants.id"), nullable=True, index=True),
        sa.Column("role", sa.Enum("clerk", "verifier", "courier", name="bulkingjobrole", native_enum=False), nullable=False),
        sa.Column("assignee_id", sa.Integer, sa.ForeignKey("users.id"), nullable=True, index=True),
        sa.Column("assignee_name", sa.String(255), nullable=False),
        sa.Column("assignee_location", sa.String(255), nullable=True),
        sa.Column("status", sa.Enum("assigned", "in_progress", "completed", "cancelled", name="bulkingjobstatus", native_enum=False), default="assigned"),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )

    # ── bulking_packing_records ────────────────────────────────────────────
    op.create_table(
        "bulking_packing_records",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("register_id", sa.Integer, sa.ForeignKey("bulking_registers.id"), nullable=False, index=True),
        sa.Column("item_id", sa.Integer, sa.ForeignKey("taxonomy_items.id"), nullable=False, index=True),
        sa.Column("tenant_id", sa.Integer, sa.ForeignKey("tenants.id"), nullable=True, index=True),
        sa.Column("quantity", sa.Float, nullable=False),
        sa.Column("unit", sa.String(50), nullable=True),
        sa.Column("package_type", sa.String(100), nullable=True),
        sa.Column("package_count", sa.Integer, nullable=True),
        sa.Column("total_weight_kg", sa.Float, nullable=True),
        sa.Column("certificate_id", sa.String(100), nullable=True, index=True),
        sa.Column("status", sa.Enum("packed", "certified", "cancelled", name="packingstatus", native_enum=False), default="packed"),
        sa.Column("packed_by_id", sa.Integer, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("packed_by_name", sa.String(255), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("packed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("bulking_packing_records")
    op.drop_table("bulking_job_assignments")
