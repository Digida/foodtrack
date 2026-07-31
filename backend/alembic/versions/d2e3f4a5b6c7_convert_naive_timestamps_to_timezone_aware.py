"""Convert remaining naive TIMESTAMP columns to TIMESTAMPTZ.

Revision d1e2f3a4b5c6 intended to do this but its guard used
"TIME ZONE" not in col_type, which is always False for the string
"TIMESTAMP WITHOUT TIME ZONE" (the substring "TIME ZONE" is present),
so it silently converted nothing.  On databases where that revision is
already stamped this migration performs the actual conversion; on fresh
databases (base_schema now creates DateTime(timezone=True)) it finds no
naive columns and is a no-op.

The application and all models now write timezone-aware UTC datetimes
and declare DateTime(timezone=True), so columns must be TIMESTAMPTZ for
asyncpg to accept them.

Revision ID: d2e3f4a5b6c7
Revises: d1e2f3a4b5c6
Create Date: 2026-07-31
"""
import sqlalchemy as sa
from alembic import op

revision = "d2e3f4a5b6c7"
down_revision = "d1e2f3a4b5c6"
branch_labels = None
depends_on = None


def _quote(identifier: str) -> str:
    return f'"{identifier.replace(chr(34), chr(34) + chr(34))}"'


def _is_naive_timestamp(col_type: str) -> bool:
    return col_type.startswith("TIMESTAMP") and "WITHOUT TIME ZONE" in col_type


def _is_aware_timestamp(col_type: str) -> bool:
    return col_type.startswith("TIMESTAMP") and "WITH TIME ZONE" in col_type


def upgrade() -> None:
    bind = op.get_bind()

    # SQLite has no real timestamp type — nothing to convert there.
    if bind.dialect.name == "sqlite":
        return

    inspector = sa.inspect(bind)
    for table in inspector.get_table_names():
        for col in inspector.get_columns(table):
            col_type = str(col["type"]).upper()
            if _is_naive_timestamp(col_type):
                col_name = col["name"]
                op.execute(
                    f"ALTER TABLE {_quote(table)} "
                    f"ALTER COLUMN {_quote(col_name)} "
                    f"TYPE TIMESTAMPTZ USING {_quote(col_name)} AT TIME ZONE 'UTC'"
                )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        return

    inspector = sa.inspect(bind)
    for table in inspector.get_table_names():
        for col in inspector.get_columns(table):
            col_type = str(col["type"]).upper()
            if _is_aware_timestamp(col_type):
                col_name = col["name"]
                op.execute(
                    f"ALTER TABLE {_quote(table)} "
                    f"ALTER COLUMN {_quote(col_name)} "
                    f"TYPE TIMESTAMP USING {_quote(col_name)} AT TIME ZONE 'UTC'"
                )
