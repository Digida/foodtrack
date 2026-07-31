"""Fix data model critiques:
- Supplier.is_active String(1) -> Boolean
- CargoPolicy.is_active String(1) -> Boolean  (if table exists)
- InsuranceClaim.documents_json Text -> JSON   (if table exists)
- User.updated_at add server_default
- User.mfa_otp_token new column for OTP MFA
- Add indexes: certificates.expiry_date, telemetry_alerts.acknowledged,
               recalls.status, supplier_scorecards.overall_score,
               insurance_claims.status

Dialect-aware: uses batch mode for SQLite compatibility and skips
postgresql_using casts on SQLite.

Revision ID: c1d2e3f4a5b6
Revises: a2b3c4d5e6f7
Create Date: 2026-07-30
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "c1d2e3f4a5b6"
down_revision = "a2b3c4d5e6f7"
branch_labels = None
depends_on = None


def _is_sqlite() -> bool:
    bind = op.get_bind()
    return bind.dialect.name == "sqlite"


def _table_exists(name: str) -> bool:
    bind = op.get_bind()
    return inspect(bind).has_table(name)


def _column_exists(table: str, column: str) -> bool:
    bind = op.get_bind()
    cols = [c["name"] for c in inspect(bind).get_columns(table)]
    return column in cols


def _index_exists(name: str, table: str) -> bool:
    bind = op.get_bind()
    return any(i["name"] == name for i in inspect(bind).get_indexes(table))


def _column_is_string(table: str, column: str) -> bool:
    bind = op.get_bind()
    if not _table_exists(table):
        return False
    cols = {c["name"]: c for c in inspect(bind).get_columns(table)}
    if column not in cols:
        return False
    col_type = str(cols[column]["type"]).lower()
    return "char" in col_type or "text" in col_type


def upgrade() -> None:
    sqlite = _is_sqlite()

    # ── suppliers: is_active String(1) -> Boolean ─────────────────────────
    # Only needed on legacy DBs where the column is still String(1).
    # base_schema already creates it as Boolean — skip entirely there,
    # otherwise "UPDATE ... SET is_active = 1" fails on a boolean column.
    if _table_exists("suppliers") and _column_is_string("suppliers", "is_active"):
        # Normalise existing "Y"/"N" strings to "1"/"0" first
        op.execute("UPDATE suppliers SET is_active = '1' WHERE is_active IN ('Y', 'y', 'true', '1')")
        op.execute(
            "UPDATE suppliers SET is_active = '0' "
            "WHERE is_active IS NOT NULL AND is_active NOT IN ('Y', 'y', 'true', '1')"
        )
        with op.batch_alter_table("suppliers", recreate="always" if sqlite else "auto") as batch_op:
            batch_op.alter_column(
                "is_active",
                type_=sa.Boolean(),
                existing_type=sa.String(1),
                existing_nullable=True,
            )

    # ── cargo_policies: is_active String(1) -> Boolean ────────────────────
    if _table_exists("cargo_policies") and _column_is_string("cargo_policies", "is_active"):
        op.execute("UPDATE cargo_policies SET is_active = '1' WHERE is_active IN ('Y', 'y', 'true', '1')")
        op.execute(
            "UPDATE cargo_policies SET is_active = '0' "
            "WHERE is_active IS NOT NULL AND is_active NOT IN ('Y', 'y', 'true', '1')"
        )
        with op.batch_alter_table("cargo_policies", recreate="always" if sqlite else "auto") as batch_op:
            batch_op.alter_column(
                "is_active",
                type_=sa.Boolean(),
                existing_type=sa.String(1),
                existing_nullable=True,
            )

    # ── insurance_claims: documents_json Text -> JSON ─────────────────────
    # SQLite's JSON and Text are stored identically; only the type annotation changes.
    if _table_exists("insurance_claims") and _column_exists("insurance_claims", "documents_json"):
        with op.batch_alter_table("insurance_claims", recreate="always" if sqlite else "auto") as batch_op:
            batch_op.alter_column(
                "documents_json",
                type_=sa.JSON(),
                existing_type=sa.Text(),
                existing_nullable=True,
            )

    # ── users: add mfa_otp_token column + server_default on updated_at ────
    if not _column_exists("users", "mfa_otp_token"):
        with op.batch_alter_table("users") as batch_op:
            batch_op.add_column(sa.Column("mfa_otp_token", sa.Text(), nullable=True))

    # server_default on updated_at — only meaningful for PostgreSQL
    if not sqlite:
        with op.batch_alter_table("users") as batch_op:
            batch_op.alter_column(
                "updated_at",
                server_default=sa.text("now()"),
                existing_type=sa.DateTime(timezone=True),
                existing_nullable=True,
            )

    # ── indexes ────────────────────────────────────────────────────────────
    if _table_exists("certificates") and not _index_exists("ix_certificates_expiry_date", "certificates"):
        op.create_index("ix_certificates_expiry_date", "certificates", ["expiry_date"])

    if _table_exists("telemetry_alerts") and not _index_exists("ix_telemetry_alerts_acknowledged", "telemetry_alerts"):
        op.create_index("ix_telemetry_alerts_acknowledged", "telemetry_alerts", ["acknowledged"])

    if _table_exists("recalls") and not _index_exists("ix_recalls_status", "recalls"):
        op.create_index("ix_recalls_status", "recalls", ["status"])

    if _table_exists("supplier_scorecards"):
        if not _index_exists("ix_supplier_scorecards_overall_score", "supplier_scorecards"):
            op.create_index("ix_supplier_scorecards_overall_score", "supplier_scorecards", ["overall_score"])
        if not _index_exists("ix_supplier_scorecards_supplier_score", "supplier_scorecards"):
            op.create_index("ix_supplier_scorecards_supplier_score", "supplier_scorecards", ["supplier_id", "overall_score"])

    if _table_exists("insurance_claims") and not _index_exists("ix_insurance_claims_status", "insurance_claims"):
        op.create_index("ix_insurance_claims_status", "insurance_claims", ["status"])


def downgrade() -> None:
    for idx, tbl in [
        ("ix_insurance_claims_status", "insurance_claims"),
        ("ix_supplier_scorecards_supplier_score", "supplier_scorecards"),
        ("ix_supplier_scorecards_overall_score", "supplier_scorecards"),
        ("ix_recalls_status", "recalls"),
        ("ix_telemetry_alerts_acknowledged", "telemetry_alerts"),
        ("ix_certificates_expiry_date", "certificates"),
    ]:
        if _table_exists(tbl) and _index_exists(idx, tbl):
            op.drop_index(idx, table_name=tbl)

    if _column_exists("users", "mfa_otp_token"):
        with op.batch_alter_table("users") as batch_op:
            batch_op.drop_column("mfa_otp_token")

    if _table_exists("insurance_claims") and _column_exists("insurance_claims", "documents_json"):
        with op.batch_alter_table("insurance_claims") as batch_op:
            batch_op.alter_column("documents_json", type_=sa.Text(), existing_type=sa.JSON())

    if _table_exists("suppliers") and _column_exists("suppliers", "is_active"):
        with op.batch_alter_table("suppliers") as batch_op:
            batch_op.alter_column("is_active", type_=sa.String(1), existing_type=sa.Boolean())

    if _table_exists("cargo_policies") and _column_exists("cargo_policies", "is_active"):
        with op.batch_alter_table("cargo_policies") as batch_op:
            batch_op.alter_column("is_active", type_=sa.String(1), existing_type=sa.Boolean())
