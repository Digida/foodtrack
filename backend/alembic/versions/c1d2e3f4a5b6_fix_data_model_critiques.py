"""Fix data model critiques:
- Supplier.is_active String(1) -> Boolean
- CargoPolicy.is_active String(1) -> Boolean
- InsuranceClaim.documents_json Text -> JSON
- User.updated_at add server_default
- User.mfa_otp_token new column for OTP MFA
- Add indexes: certificates.expiry_date, telemetry_alerts.acknowledged,
               recalls.status, supplier_scorecards.overall_score,
               insurance_claims.status

Revision ID: c1d2e3f4a5b6
Revises: a2b3c4d5e6f7
Create Date: 2026-07-30
"""
from alembic import op
import sqlalchemy as sa

revision = "c1d2e3f4a5b6"
down_revision = "a2b3c4d5e6f7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── suppliers: is_active String(1) -> Boolean ─────────────────────────
    with op.batch_alter_table("suppliers") as batch_op:
        # Convert "Y"/"N" string values to true/false before altering type
        op.execute("UPDATE suppliers SET is_active = 'true' WHERE is_active = 'Y'")
        op.execute("UPDATE suppliers SET is_active = 'false' WHERE is_active != 'true'")
        batch_op.alter_column(
            "is_active",
            type_=sa.Boolean(),
            existing_type=sa.String(1),
            postgresql_using="is_active::boolean",
        )

    # ── cargo_policies: is_active String(1) -> Boolean ────────────────────
    with op.batch_alter_table("cargo_policies") as batch_op:
        op.execute("UPDATE cargo_policies SET is_active = 'true' WHERE is_active = 'Y'")
        op.execute("UPDATE cargo_policies SET is_active = 'false' WHERE is_active != 'true'")
        batch_op.alter_column(
            "is_active",
            type_=sa.Boolean(),
            existing_type=sa.String(1),
            postgresql_using="is_active::boolean",
        )

    # ── insurance_claims: documents_json Text -> JSON ─────────────────────
    with op.batch_alter_table("insurance_claims") as batch_op:
        batch_op.alter_column(
            "documents_json",
            type_=sa.JSON(),
            existing_type=sa.Text(),
            postgresql_using="documents_json::json",
        )

    # ── users: add server_default to updated_at + new mfa_otp_token column ─
    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column(
            "updated_at",
            server_default=sa.text("now()"),
            existing_type=sa.DateTime(timezone=True),
            existing_nullable=True,
        )
        batch_op.add_column(sa.Column("mfa_otp_token", sa.Text(), nullable=True))

    # ── indexes ────────────────────────────────────────────────────────────
    op.create_index("ix_certificates_expiry_date", "certificates", ["expiry_date"])
    op.create_index("ix_telemetry_alerts_acknowledged", "telemetry_alerts", ["acknowledged"])
    op.create_index("ix_recalls_status", "recalls", ["status"])
    op.create_index("ix_supplier_scorecards_overall_score", "supplier_scorecards", ["overall_score"])
    op.create_index("ix_supplier_scorecards_supplier_score", "supplier_scorecards", ["supplier_id", "overall_score"])
    op.create_index("ix_insurance_claims_status", "insurance_claims", ["status"])


def downgrade() -> None:
    op.drop_index("ix_insurance_claims_status", table_name="insurance_claims")
    op.drop_index("ix_supplier_scorecards_supplier_score", table_name="supplier_scorecards")
    op.drop_index("ix_supplier_scorecards_overall_score", table_name="supplier_scorecards")
    op.drop_index("ix_recalls_status", table_name="recalls")
    op.drop_index("ix_telemetry_alerts_acknowledged", table_name="telemetry_alerts")
    op.drop_index("ix_certificates_expiry_date", table_name="certificates")

    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("mfa_otp_token")
        batch_op.alter_column(
            "updated_at",
            server_default=None,
            existing_type=sa.DateTime(timezone=True),
        )

    with op.batch_alter_table("insurance_claims") as batch_op:
        batch_op.alter_column(
            "documents_json",
            type_=sa.Text(),
            existing_type=sa.JSON(),
        )

    with op.batch_alter_table("cargo_policies") as batch_op:
        batch_op.alter_column(
            "is_active",
            type_=sa.String(1),
            existing_type=sa.Boolean(),
        )

    with op.batch_alter_table("suppliers") as batch_op:
        batch_op.alter_column(
            "is_active",
            type_=sa.String(1),
            existing_type=sa.Boolean(),
        )
