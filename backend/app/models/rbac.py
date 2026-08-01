"""Role-Based Access Control (RBAC) models plus refresh-token storage.

RBAC is the backbone that lets the platform grant the right privileges to
Clerks, Verifiers, Couriers, Admins and Users across the entities they
operate on. A user has a primary `role` (see UserRole) plus any number of
extra `roles` via the user_roles join table. Permissions are attached to
roles through role_permissions and enforced centrally by
`dependencies.require_permission`.
"""
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean, Column, DateTime, ForeignKey, Integer, String, Table, Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.database import Base


role_permissions = Table(
    "role_permissions",
    Base.metadata,
    Column("role_id", Integer, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    Column("permission_id", Integer, ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True),
)


user_roles = Table(
    "user_roles",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("role_id", Integer, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
)


class Role(Base):
    """A named set of permissions (e.g. clerk, verifier, courier, admin).

    System roles (`is_system=True`, `tenant_id=None`) carry the platform's
    default permission matrix and are seeded at startup. Tenant admins can
    create custom roles (`tenant_id=<tenant>`) for their own operations.
    """
    __tablename__ = "roles"
    __table_args__ = (
        UniqueConstraint("code", "tenant_id", name="uq_roles_code_tenant"),
    )

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    is_system = Column(Boolean, default=True, nullable=False)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    permissions = relationship("Permission", secondary=role_permissions, back_populates="roles", lazy="selectin")


class Permission(Base):
    """A single action granted to a role, e.g. `certificates.approve`."""
    __tablename__ = "permissions"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(100), unique=True, nullable=False, index=True)
    resource = Column(String(50), nullable=False)
    action = Column(String(50), nullable=False)
    description = Column(Text, nullable=True)

    roles = relationship("Role", secondary=role_permissions, back_populates="permissions")


class RefreshToken(Base):
    """A stored, revocable refresh token (only the SHA-256 hash is persisted).

    Refresh tokens rotate on every use: a consumed token is revoked and a new
    one is issued, so a leaked token cannot be replayed.
    """
    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash = Column(String(64), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    user_agent = Column(String(255), nullable=True)
    ip_address = Column(String(45), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="refresh_tokens")
