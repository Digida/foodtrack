"""add RBAC tables, refresh tokens and user_type

Adds the Role-Based Access Control layer (roles, permissions, role↔permission
and user↔role links), refresh-token storage for the access/refresh token pair,
and a `user_type` column describing the account category (organization,
operations, government, consumer, system).

The `role` column on users stays a plain string, so the new UserRole values
(clerk, courier, auditor, government_agent) need no enum migration.

Revision ID: a4b5c6d7e8f9
Revises: f2e3d4a5b6c7
Create Date: 2026-08-01
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a4b5c6d7e8f9"
down_revision: Union[str, None] = "f2e3d4a5b6c7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("user_type", sa.String(30), server_default="organization", nullable=False),
    )

    op.create_table(
        "permissions",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("code", sa.String(100), unique=True, nullable=False, index=True),
        sa.Column("resource", sa.String(50), nullable=False),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
    )

    op.create_table(
        "roles",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("code", sa.String(50), nullable=False, index=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("is_system", sa.Boolean, server_default=sa.true(), nullable=False),
        sa.Column("tenant_id", sa.Integer, sa.ForeignKey("tenants.id"), nullable=True, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("code", "tenant_id", name="uq_roles_code_tenant"),
    )

    op.create_table(
        "role_permissions",
        sa.Column("role_id", sa.Integer, sa.ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("permission_id", sa.Integer, sa.ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True),
    )

    op.create_table(
        "user_roles",
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("role_id", sa.Integer, sa.ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    )

    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("token_hash", sa.String(64), unique=True, nullable=False, index=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("user_agent", sa.String(255), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("refresh_tokens")
    op.drop_table("user_roles")
    op.drop_table("role_permissions")
    op.drop_table("roles")
    op.drop_table("permissions")
    op.drop_column("users", "user_type")
