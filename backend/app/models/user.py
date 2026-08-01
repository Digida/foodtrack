from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum

from app.database import Base


class UserRole(str, enum.Enum):
    SUPERUSER = "superuser"
    ADMIN = "admin"
    ENTERPRISE = "enterprise"
    VERIFIER = "verifier"
    VIEWER = "viewer"
    CLERK = "clerk"
    COURIER = "courier"
    AUDITOR = "auditor"
    GOVERNMENT_AGENT = "government_agent"


class UserType(str, enum.Enum):
    """Account category — who the user is, orthogonal to what they can do (roles).

    - ORGANIZATION: company accounts (admins, enterprise buyers, staff)
    - OPERATIONS:    field operators on the ground (clerks, verifiers, couriers)
    - GOVERNMENT:    regulator / customs / municipality accounts
    - CONSUMER:      public portal accounts (scan-and-verify)
    - SYSTEM:        internal platform / system accounts
    """
    ORGANIZATION = "organization"
    OPERATIONS = "operations"
    GOVERNMENT = "government"
    CONSUMER = "consumer"
    SYSTEM = "system"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    phone = Column(String(50), unique=True, nullable=True)
    full_name = Column(String(255), nullable=False)
    company = Column(String(255), nullable=True)
    role = Column(SAEnum(UserRole, native_enum=False), default=UserRole.VIEWER, nullable=False)
    user_type = Column(SAEnum(UserType, native_enum=False), default=UserType.ORGANIZATION, nullable=False)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True, index=True)
    hashed_password = Column(String(255), nullable=False)
    # Secondary contact details (used for e.g. alternate email / alternate phone)
    alternate_email = Column(String(255), nullable=True)
    alternate_phone = Column(String(50), nullable=True)
    email_verified = Column(Boolean, default=False)
    phone_verified = Column(Boolean, default=False)
    totp_secret = Column(String(64), nullable=True)
    totp_enabled = Column(Boolean, default=False)
    # OTP token for email/phone MFA — consumed (set to NULL) after successful verification
    mfa_otp_token = Column(Text, nullable=True)
    biometric_credential_id = Column(String(255), nullable=True)
    biometric_public_key = Column(String(1024), nullable=True)
    sso_provider = Column(String(50), nullable=True)
    sso_id = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    # Fixed: added server_default so updated_at is set on INSERT, not just on UPDATE
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    tenant = relationship("Tenant", back_populates="users")
    # Additional roles beyond the primary `role` column (RBAC). Always eagerly
    # loaded so sync accessors (e.g. serialize_user) never trigger lazy loads.
    roles = relationship("Role", secondary="user_roles", lazy="selectin")
    refresh_tokens = relationship("RefreshToken", back_populates="user", lazy="select")
