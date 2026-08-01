"""merge commerce tables and item_rates branches

The commerce pipeline tables (b1c2d3e4f5a6) and the item_rates money/boolean
fix (e6f7a8b9c0d1) both branched from the same parent. This merge revision
unifies the two heads so `alembic upgrade head` resolves to a single revision.

Revision ID: f0f1f2f3f4f5
Revises: b1c2d3e4f5a6, e6f7a8b9c0d1
Create Date: 2026-08-01
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "f0f1f2f3f4f5"
down_revision: Union[str, Sequence[str], None] = ("b1c2d3e4f5a6", "e6f7a8b9c0d1")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
