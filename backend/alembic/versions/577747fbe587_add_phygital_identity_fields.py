"""add_phygital_identity_fields

Revision ID: 577747fbe587
Revises: 267c1a1c4a4b
Create Date: 2026-07-30 10:35:35.383406

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '577747fbe587'
down_revision: Union[str, None] = '267c1a1c4a4b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('item_identifier_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('item_id', sa.Integer(), nullable=False),
        sa.Column('identifier_type', sa.String(length=20), nullable=False),
        sa.Column('identifier_value', sa.String(length=255), nullable=False),
        sa.Column('assigned_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.Column('assigned_by', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('metadata_json', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['item_id'], ['taxonomy_items.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_item_identifier_logs_id'), 'item_identifier_logs', ['id'], unique=False)
    op.create_index(op.f('ix_item_identifier_logs_identifier_value'), 'item_identifier_logs', ['identifier_value'], unique=False)
    op.create_index(op.f('ix_item_identifier_logs_item_id'), 'item_identifier_logs', ['item_id'], unique=False)
    op.add_column('taxonomy_items', sa.Column('qr_seed', sa.String(length=64), nullable=True))
    op.add_column('taxonomy_items', sa.Column('nfc_uid_template', sa.String(length=255), nullable=True))
    op.add_column('taxonomy_items', sa.Column('barcode_prefix', sa.String(length=12), nullable=True))
    op.create_index(op.f('ix_taxonomy_items_qr_seed'), 'taxonomy_items', ['qr_seed'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_taxonomy_items_qr_seed'), table_name='taxonomy_items')
    op.drop_column('taxonomy_items', 'barcode_prefix')
    op.drop_column('taxonomy_items', 'nfc_uid_template')
    op.drop_column('taxonomy_items', 'qr_seed')
    op.drop_index(op.f('ix_item_identifier_logs_item_id'), table_name='item_identifier_logs')
    op.drop_index(op.f('ix_item_identifier_logs_identifier_value'), table_name='item_identifier_logs')
    op.drop_index(op.f('ix_item_identifier_logs_id'), table_name='item_identifier_logs')
    op.drop_table('item_identifier_logs')
