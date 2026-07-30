"""add_enrichment_tables

Revision ID: f1e2d3c4b5a6
Revises: 054afe0f5822
Create Date: 2026-07-30 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f1e2d3c4b5a6'
down_revision: Union[str, None] = '054afe0f5822'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('enrichment_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=True),
        sa.Column('source', sa.Enum('WEB_SEARCH', 'WEB_READER', 'RSS_FEED', 'NUTRITION_API', 'PRICE_API', 'TRANSLATOR', 'MANUAL', name='enrichmentsource'), nullable=True),
        sa.Column('status', sa.Enum('PENDING', 'RUNNING', 'COMPLETED', 'FAILED', name='enrichmentstatus'), nullable=True),
        sa.Column('entity_type', sa.String(length=50), nullable=True),
        sa.Column('entity_id', sa.Integer(), nullable=True),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('details', sa.Text(), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('triggered_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.ForeignKeyConstraint(['triggered_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_enrichment_logs_id'), 'enrichment_logs', ['id'], unique=False)
    op.create_index(op.f('ix_enrichment_logs_tenant_id'), 'enrichment_logs', ['tenant_id'], unique=False)

    op.create_table('enrichment_suggestions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=True),
        sa.Column('entity_type', sa.String(length=50), nullable=False),
        sa.Column('entity_id', sa.Integer(), nullable=True),
        sa.Column('suggestion_type', sa.String(length=50), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('confidence', sa.String(length=20), nullable=True),
        sa.Column('source', sa.String(length=255), nullable=True),
        sa.Column('payload_json', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_enrichment_suggestions_id'), 'enrichment_suggestions', ['id'], unique=False)
    op.create_index(op.f('ix_enrichment_suggestions_tenant_id'), 'enrichment_suggestions', ['tenant_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_enrichment_suggestions_tenant_id'), table_name='enrichment_suggestions')
    op.drop_index(op.f('ix_enrichment_suggestions_id'), table_name='enrichment_suggestions')
    op.drop_table('enrichment_suggestions')
    op.drop_index(op.f('ix_enrichment_logs_tenant_id'), table_name='enrichment_logs')
    op.drop_index(op.f('ix_enrichment_logs_id'), table_name='enrichment_logs')
    op.drop_table('enrichment_logs')
    op.execute('DROP TYPE IF EXISTS enrichmentsource')
    op.execute('DROP TYPE IF EXISTS enrichmentstatus')
