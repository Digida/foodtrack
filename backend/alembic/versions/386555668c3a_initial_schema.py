"""initial_schema — no-op.

The tables this migration originally tried to create and alter
are now handled by the base migration (000000000000_base_schema).
This file is kept as a chain link so subsequent migrations
can reference it as their down_revision without breaking the chain.

Revision ID: 386555668c3a
Revises: 000000000000
Create Date: 2026-07-30 10:09:53.279832
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '386555668c3a'
down_revision: Union[str, None] = '000000000000'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # All DDL from this migration was moved to 000000000000_base_schema.
    # Nothing to do here — the base migration already created all tables
    # and columns that were originally generated into this file.
    pass


def downgrade() -> None:
    pass
