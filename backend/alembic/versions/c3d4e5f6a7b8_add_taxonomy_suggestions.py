"""add taxonomy_suggestions community faucet table

Authed users propose taxonomy info (multilingual names, attributes, item-field
corrections, missing items) which admins accept (applied to the catalog) or
reject. status is persisted lowercase (pending/accepted/rejected) to match the
app's enum-value contract.

Revision ID: c3d4e5f6a7b8
Revises: c7d8e9f0a1b2
Create Date: 2026-08-04
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, None] = "c7d8e9f0a1b2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "taxonomy_suggestions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("item_id", sa.Integer(), sa.ForeignKey("taxonomy_items.id"), nullable=True),
        sa.Column("node_id", sa.Integer(), sa.ForeignKey("taxonomy_nodes.id"), nullable=True),
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.Column("language", sa.String(length=10), nullable=True),
        sa.Column("key", sa.String(length=255), nullable=True),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("unit", sa.String(length=100), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("suggested_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("reviewed_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("review_note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_taxonomy_suggestions_id", "taxonomy_suggestions", ["id"])
    op.create_index("ix_taxonomy_suggestions_item_id", "taxonomy_suggestions", ["item_id"])
    op.create_index("ix_taxonomy_suggestions_node_id", "taxonomy_suggestions", ["node_id"])
    op.create_index("ix_taxonomy_suggestions_suggested_by", "taxonomy_suggestions", ["suggested_by"])
    op.create_index("ix_taxonomy_suggestions_status", "taxonomy_suggestions", ["status"])


def downgrade() -> None:
    op.drop_index("ix_taxonomy_suggestions_status", table_name="taxonomy_suggestions")
    op.drop_index("ix_taxonomy_suggestions_suggested_by", table_name="taxonomy_suggestions")
    op.drop_index("ix_taxonomy_suggestions_node_id", table_name="taxonomy_suggestions")
    op.drop_index("ix_taxonomy_suggestions_item_id", table_name="taxonomy_suggestions")
    op.drop_index("ix_taxonomy_suggestions_id", table_name="taxonomy_suggestions")
    op.drop_table("taxonomy_suggestions")
