"""add ai_memories table for the MAG memory tier

Persists resolved-task episodes (strategy, tool recipe, summary) so the
orchestrator's memory-augmented generation tier can replay them on similar
tasks across restarts. strategy is stored lowercase (mag/dag/rag/fallback) to
match the app's enum-value contract.

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-08-04
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ai_memories",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("task", sa.String(length=1000), nullable=False),
        sa.Column("strategy", sa.String(length=20), nullable=False),
        sa.Column("recipe", sa.JSON(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("tags", sa.JSON(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("hits", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_ai_memories_id", "ai_memories", ["id"])
    op.create_index("ix_ai_memories_user_id", "ai_memories", ["user_id"])
    op.create_index("ix_ai_memories_created_at", "ai_memories", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_ai_memories_created_at", table_name="ai_memories")
    op.drop_index("ix_ai_memories_user_id", table_name="ai_memories")
    op.drop_index("ix_ai_memories_id", table_name="ai_memories")
    op.drop_table("ai_memories")
