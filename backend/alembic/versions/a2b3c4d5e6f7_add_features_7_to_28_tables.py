"""add_features_7_to_28_tables

Revision ID: a2b3c4d5e6f7
Revises: f1e2d3c4b5a6
Create Date: 2026-07-30 14:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a2b3c4d5e6f7'
down_revision: Union[str, None] = 'f1e2d3c4b5a6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Event / Webhook tables
    op.create_table('webhook_subscriptions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=True),
        sa.Column('url', sa.String(length=512), nullable=False),
        sa.Column('secret', sa.String(length=128), nullable=True),
        sa.Column('events', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_webhook_subscriptions_id'), 'webhook_subscriptions', ['id'], unique=False)
    op.create_index(op.f('ix_webhook_subscriptions_tenant_id'), 'webhook_subscriptions', ['tenant_id'], unique=False)

    op.create_table('event_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=True),
        sa.Column('event_type', sa.String(length=50), nullable=False),
        sa.Column('channel', sa.String(length=255), nullable=True),
        sa.Column('payload_json', sa.Text(), nullable=True),
        sa.Column('source_ip', sa.String(length=45), nullable=True),
        sa.Column('published_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.ForeignKeyConstraint(['published_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_event_logs_id'), 'event_logs', ['id'], unique=False)
    op.create_index(op.f('ix_event_logs_tenant_id'), 'event_logs', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_event_logs_event_type'), 'event_logs', ['event_type'], unique=False)

    # Telemetry tables
    op.create_table('telemetry_readings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=True),
        sa.Column('device_id', sa.String(length=100), nullable=False),
        sa.Column('telemetry_type', sa.String(length=50), nullable=False),
        sa.Column('item_id', sa.Integer(), nullable=True),
        sa.Column('batch_id', sa.Integer(), nullable=True),
        sa.Column('value_float', sa.Float(), nullable=True),
        sa.Column('value_str', sa.String(length=255), nullable=True),
        sa.Column('unit', sa.String(length=50), nullable=True),
        sa.Column('location_lat', sa.Float(), nullable=True),
        sa.Column('location_lng', sa.Float(), nullable=True),
        sa.Column('metadata_json', sa.Text(), nullable=True),
        sa.Column('recorded_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.ForeignKeyConstraint(['item_id'], ['taxonomy_items.id'], ),
        sa.ForeignKeyConstraint(['batch_id'], ['batches.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_telemetry_readings_id'), 'telemetry_readings', ['id'], unique=False)
    op.create_index(op.f('ix_telemetry_readings_tenant_id'), 'telemetry_readings', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_telemetry_readings_device_id'), 'telemetry_readings', ['device_id'], unique=False)
    op.create_index(op.f('ix_telemetry_readings_item_id'), 'telemetry_readings', ['item_id'], unique=False)
    op.create_index(op.f('ix_telemetry_readings_batch_id'), 'telemetry_readings', ['batch_id'], unique=False)

    op.create_table('telemetry_alerts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=True),
        sa.Column('device_id', sa.String(length=100), nullable=False),
        sa.Column('telemetry_type', sa.String(length=50), nullable=False),
        sa.Column('rule_name', sa.String(length=100), nullable=False),
        sa.Column('threshold', sa.Float(), nullable=True),
        sa.Column('actual_value', sa.Float(), nullable=True),
        sa.Column('message', sa.Text(), nullable=True),
        sa.Column('severity', sa.String(length=20), nullable=True),
        sa.Column('acknowledged', sa.Boolean(), nullable=True),
        sa.Column('acknowledged_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.ForeignKeyConstraint(['acknowledged_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_telemetry_alerts_id'), 'telemetry_alerts', ['id'], unique=False)
    op.create_index(op.f('ix_telemetry_alerts_tenant_id'), 'telemetry_alerts', ['tenant_id'], unique=False)

    # API Keys
    op.create_table('api_keys',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=True),
        sa.Column('key_prefix', sa.String(length=8), nullable=False),
        sa.Column('key_hash', sa.String(length=128), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('rate_limit', sa.Integer(), nullable=True),
        sa.Column('rate_limit_window', sa.Integer(), nullable=True),
        sa.Column('scopes', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('last_used_at', sa.DateTime(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_api_keys_id'), 'api_keys', ['id'], unique=False)
    op.create_index(op.f('ix_api_keys_tenant_id'), 'api_keys', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_api_keys_key_prefix'), 'api_keys', ['key_prefix'], unique=False)

    # Archive Policies
    op.create_table('archive_policies',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=True),
        sa.Column('entity_type', sa.String(length=50), nullable=False),
        sa.Column('retention_days', sa.Integer(), nullable=False),
        sa.Column('archive_to_table', sa.String(length=100), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_archive_policies_id'), 'archive_policies', ['id'], unique=False)
    op.create_index(op.f('ix_archive_policies_tenant_id'), 'archive_policies', ['tenant_id'], unique=False)

    # ESG / Carbon Footprint
    op.create_table('item_carbon_footprints',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=True),
        sa.Column('item_id', sa.Integer(), nullable=False),
        sa.Column('kg_co2e_per_kg', sa.Float(), nullable=False),
        sa.Column('water_usage_l_per_kg', sa.Float(), nullable=True),
        sa.Column('source', sa.String(length=255), nullable=True),
        sa.Column('methodology', sa.String(length=100), nullable=True),
        sa.Column('confidence', sa.String(length=20), nullable=True),
        sa.Column('metadata_json', sa.Text(), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.ForeignKeyConstraint(['item_id'], ['taxonomy_items.id'], ),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_item_carbon_footprints_id'), 'item_carbon_footprints', ['id'], unique=False)
    op.create_index(op.f('ix_item_carbon_footprints_tenant_id'), 'item_carbon_footprints', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_item_carbon_footprints_item_id'), 'item_carbon_footprints', ['item_id'], unique=False)

    # Recall tables
    op.create_table('recalls',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=True),
        sa.Column('batch_id', sa.Integer(), nullable=False),
        sa.Column('item_id', sa.Integer(), nullable=True),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('severity', sa.Enum('LOW', 'MEDIUM', 'HIGH', 'CRITICAL', name='recallseverity'), nullable=True),
        sa.Column('status', sa.Enum('INITIATED', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED', name='recallstatus'), nullable=True),
        sa.Column('affected_region', sa.String(length=255), nullable=True),
        sa.Column('notified_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.ForeignKeyConstraint(['batch_id'], ['batches.id'], ),
        sa.ForeignKeyConstraint(['item_id'], ['taxonomy_items.id'], ),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_recalls_id'), 'recalls', ['id'], unique=False)
    op.create_index(op.f('ix_recalls_tenant_id'), 'recalls', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_recalls_batch_id'), 'recalls', ['batch_id'], unique=False)
    op.create_index(op.f('ix_recalls_item_id'), 'recalls', ['item_id'], unique=False)

    op.create_table('recall_events',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('recall_id', sa.Integer(), nullable=False),
        sa.Column('action', sa.String(length=50), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('performed_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['recall_id'], ['recalls.id'], ),
        sa.ForeignKeyConstraint(['performed_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_recall_events_id'), 'recall_events', ['id'], unique=False)
    op.create_index(op.f('ix_recall_events_recall_id'), 'recall_events', ['recall_id'], unique=False)

    # Supplier tables
    op.create_table('suppliers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('contact_name', sa.String(length=255), nullable=True),
        sa.Column('contact_email', sa.String(length=255), nullable=True),
        sa.Column('contact_phone', sa.String(length=50), nullable=True),
        sa.Column('address', sa.Text(), nullable=True),
        sa.Column('regions', sa.Text(), nullable=True),
        sa.Column('certifications', sa.Text(), nullable=True),
        sa.Column('is_active', sa.String(length=1), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_suppliers_id'), 'suppliers', ['id'], unique=False)
    op.create_index(op.f('ix_suppliers_tenant_id'), 'suppliers', ['tenant_id'], unique=False)

    op.create_table('supplier_scorecards',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=True),
        sa.Column('supplier_id', sa.Integer(), nullable=False),
        sa.Column('period', sa.String(length=20), nullable=False),
        sa.Column('on_time_delivery_pct', sa.Float(), nullable=True),
        sa.Column('quality_score', sa.Float(), nullable=True),
        sa.Column('cert_compliance_pct', sa.Float(), nullable=True),
        sa.Column('audit_result', sa.String(length=50), nullable=True),
        sa.Column('overall_score', sa.Float(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.ForeignKeyConstraint(['supplier_id'], ['suppliers.id'], ),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_supplier_scorecards_id'), 'supplier_scorecards', ['id'], unique=False)
    op.create_index(op.f('ix_supplier_scorecards_tenant_id'), 'supplier_scorecards', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_supplier_scorecards_supplier_id'), 'supplier_scorecards', ['supplier_id'], unique=False)

    # Insurance tables
    op.create_table('cargo_policies',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=True),
        sa.Column('item_id', sa.Integer(), nullable=False),
        sa.Column('carrier', sa.String(length=255), nullable=True),
        sa.Column('policy_number', sa.String(length=100), nullable=False),
        sa.Column('coverage_amount', sa.Float(), nullable=False),
        sa.Column('premium', sa.Float(), nullable=True),
        sa.Column('currency', sa.String(length=3), nullable=True),
        sa.Column('valid_from', sa.DateTime(), nullable=False),
        sa.Column('valid_until', sa.DateTime(), nullable=False),
        sa.Column('is_active', sa.String(length=1), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.ForeignKeyConstraint(['item_id'], ['taxonomy_items.id'], ),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_cargo_policies_id'), 'cargo_policies', ['id'], unique=False)
    op.create_index(op.f('ix_cargo_policies_tenant_id'), 'cargo_policies', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_cargo_policies_item_id'), 'cargo_policies', ['item_id'], unique=False)

    op.create_table('insurance_claims',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=True),
        sa.Column('policy_id', sa.Integer(), nullable=False),
        sa.Column('incident_type', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('claim_amount', sa.Float(), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=True),
        sa.Column('status', sa.Enum('DRAFT', 'SUBMITTED', 'UNDER_REVIEW', 'APPROVED', 'REJECTED', 'PAID', name='claimstatus'), nullable=True),
        sa.Column('documents_json', sa.Text(), nullable=True),
        sa.Column('filed_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.ForeignKeyConstraint(['policy_id'], ['cargo_policies.id'], ),
        sa.ForeignKeyConstraint(['filed_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_insurance_claims_id'), 'insurance_claims', ['id'], unique=False)
    op.create_index(op.f('ix_insurance_claims_tenant_id'), 'insurance_claims', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_insurance_claims_policy_id'), 'insurance_claims', ['policy_id'], unique=False)


def downgrade() -> None:
    op.drop_table('insurance_claims')
    op.drop_table('cargo_policies')
    op.drop_table('supplier_scorecards')
    op.drop_table('suppliers')
    op.drop_table('recall_events')
    op.drop_table('recalls')
    op.drop_table('item_carbon_footprints')
    op.drop_table('archive_policies')
    op.drop_table('api_keys')
    op.drop_table('telemetry_alerts')
    op.drop_table('telemetry_readings')
    op.drop_table('event_logs')
    op.drop_table('webhook_subscriptions')
    op.execute('DROP TYPE IF EXISTS claimstatus')
    op.execute('DROP TYPE IF EXISTS recallstatus')
    op.execute('DROP TYPE IF EXISTS recallseverity')
