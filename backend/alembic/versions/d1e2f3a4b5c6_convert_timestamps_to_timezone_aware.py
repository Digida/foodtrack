"""Convert all TIMESTAMP WITHOUT TIME ZONE columns to WITH TIME ZONE.

The application consistently writes timezone-aware UTC datetimes
(datetime.now(timezone.utc) in model defaults and service code), but the
columns were created as naive timestamps. asyncpg rejects aware datetimes
inserted into naive columns ("can't subtract offset-naive and offset-aware
datetimes"), which breaks every INSERT on PostgreSQL.

This migration finds every timestamp column without a time zone on the
current database and rewrites it to TIMESTAMP WITH TIME ZONE, interpreting
existing naive values as UTC (which is how the app has always written them).

Revision ID: d1e2f3a4b5c6
Revises: c1d2e3f4a5b6
Create Date: 2026-07-31
"""
import sqlalchemy as sa
from alembic import op

revision = "d1e2f3a4b5c6"
down_revision = "c1d2e3f4a5b6"
branch_labels = None
depends_on = None


def _quote(identifier: str) -> str:
    return f'"{identifier.replace(chr(34), chr(34) + chr(34))}"'


def upgrade() -> None:
    bind = op.get_bind()

    # SQLite has no real timestamp type — nothing to convert there.
    if bind.dialect.name == "sqlite":
        return

    inspector = sa.inspect(bind)
    converted = 0
    for table in inspector.get_table_names():
        for col in inspector.get_columns(table):
            col_type = str(col["type"]).upper()
            if col_type.startswith("TIMESTAMP") and "TIME ZONE" not in col_type:
                col_name = col["name"]
                op.execute(
                    f"ALTER TABLE {_quote(table)} "
                    f"ALTER COLUMN {_quote(col_name)} "
                    f"TYPE TIMESTAMPTZ USING {_quote(col_name)} AT TIME ZONE 'UTC'"
                )
                converted += 1

    # `converted` is informational — the ALTERs above are the work.


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        return

    inspector = sa.inspect(bind)
    for table in inspector.get_table_names():
        for col in inspector.get_columns(table):
            col_type = str(col["type"]).upper()
            if col_type.startswith("TIMESTAMP") and "TIME ZONE" in col_type:
                col_name = col["name"]
                op.execute(
                    f"ALTER TABLE {_quote(table)} "
                    f"ALTER COLUMN {_quote(col_name)} "
                    f"TYPE TIMESTAMP USING {_quote(col_name)} AT TIME ZONE 'UTC'"
                )
