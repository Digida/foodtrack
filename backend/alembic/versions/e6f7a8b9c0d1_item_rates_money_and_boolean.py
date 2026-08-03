"""item_rates: price_per_kg Float -> Numeric(18,2), is_active String(1) -> Boolean

Revision ID: e6f7a8b9c0d1
Revises: b1c2d3e4f5a6
Create Date: 2026-08-01
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "e6f7a8b9c0d1"
down_revision: Union[str, None] = "b1c2d3e4f5a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    # Normalize legacy string flags to 1/0 before the column type changes.
    # Values must fit the existing VARCHAR(1) column (Postgres enforces length,
    # unlike SQLite, so 'true'/'false' would be truncated).
    op.execute("UPDATE item_rates SET is_active = '1' WHERE is_active IN ('Y', 'y', '1', 'true', 't')")
    op.execute(
        "UPDATE item_rates SET is_active = '0' "
        "WHERE is_active IS NOT NULL AND is_active NOT IN ('Y', 'y', '1', 'true', 't')"
    )
    if dialect == "postgresql":
        # PostgreSQL cannot auto-cast the legacy server_default ('Y') to boolean,
        # so drop it first, then re-add a proper boolean default after the type change.
        op.execute("ALTER TABLE item_rates ALTER COLUMN is_active DROP DEFAULT")
        with op.batch_alter_table("item_rates", schema=None) as batch_op:
            batch_op.alter_column(
                "price_per_kg",
                type_=sa.Numeric(18, 2),
                existing_type=sa.Float(),
                existing_nullable=False,
            )
            batch_op.alter_column(
                "is_active",
                type_=sa.Boolean(),
                existing_type=sa.String(1),
                existing_nullable=True,
                server_default=sa.text("true"),
                postgresql_using="is_active::boolean",
            )
    else:
        with op.batch_alter_table("item_rates", schema=None) as batch_op:
            batch_op.alter_column(
                "price_per_kg",
                type_=sa.Numeric(18, 2),
                existing_type=sa.Float(),
                existing_nullable=False,
            )
            batch_op.alter_column(
                "is_active",
                type_=sa.Boolean(),
                existing_type=sa.String(1),
                existing_nullable=True,
                server_default=sa.text("1"),
            )


def downgrade() -> None:
    with op.batch_alter_table("item_rates", schema=None) as batch_op:
        batch_op.alter_column(
            "price_per_kg",
            type_=sa.Float(),
            existing_type=sa.Numeric(18, 2),
            existing_nullable=False,
        )
        batch_op.alter_column(
            "is_active",
            type_=sa.String(1),
            existing_type=sa.Boolean(),
            existing_nullable=True,
        )
