"""Add alternate_email and alternate_phone to users.

Adds secondary contact columns used for the Superuser demo account
(primary email for login, alternate email + alternate phone as
additional verified contacts) and for generic user profiles.

The users.role column is stored as String(20), so the new SUPERUSER
role value requires no enum/type migration.

Revision ID: a1b2c3d4e5f6
Revises: d2e3f4a5b6c7
Create Date: 2026-08-01
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "d2e3f4a5b6c7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    cols = {c["name"] for c in inspector.get_columns("users")}
    if "alternate_email" not in cols:
        op.add_column("users", sa.Column("alternate_email", sa.String(255), nullable=True))
    if "alternate_phone" not in cols:
        op.add_column("users", sa.Column("alternate_phone", sa.String(50), nullable=True))
    if bind.dialect.name != "sqlite":
        cert_cols = {c["name"] for c in inspector.get_columns("certificates")}
        if "product_id" in cert_cols:
            op.alter_column(
                "certificates",
                "product_id",
                existing_type=sa.Integer(),
                existing_nullable=False,
                nullable=True,
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    cols = {c["name"] for c in inspector.get_columns("users")}
    if "alternate_email" in cols:
        op.drop_column("users", "alternate_email")
    if "alternate_phone" in cols:
        op.drop_column("users", "alternate_phone")
