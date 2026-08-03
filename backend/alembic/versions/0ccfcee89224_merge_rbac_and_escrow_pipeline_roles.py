"""merge rbac and escrow pipeline roles

Revision ID: 0ccfcee89224
Revises: a4b5c6d7e8f9, a5b6c7d8e9f0
Create Date: 2026-08-03 23:27:03.465689

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0ccfcee89224'
down_revision: Union[str, None] = ('a4b5c6d7e8f9', 'a5b6c7d8e9f0')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
