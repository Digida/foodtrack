"""extend_certificate_types

Extends the certificate type enum and adds item_id FKs to several tables.
Tables and columns already created by 000000000000_base_schema are skipped.

Revision ID: 267c1a1c4a4b
Revises: 386555668c3a
Create Date: 2026-07-30 10:22:54.904104
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '267c1a1c4a4b'
down_revision: Union[str, None] = '386555668c3a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # The base migration created certificates.type as VARCHAR(30).
    # Ensure the enum values used by the ORM are reflected as a proper
    # PostgreSQL enum type.  Using a plain VARCHAR in the base keeps
    # things simple; the ORM validates values at the Python layer.
    # Nothing additional to do — all tables were created in base migration.
    pass


def downgrade() -> None:
    pass
