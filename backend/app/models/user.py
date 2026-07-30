from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum

from app.database import Base


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    ENTERPRISE = "enterprise"
    VERIFIER = "verifier"
    VIEWER = "viewer"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    phone = Column(String(50), unique=True, nullable=True)
    full_name = Column(String(255), nullable=False)
    company = Column(String(255), nullable=True)
    role = Column(SAEnum(UserRole), default=UserRole.VIEWER, nullable=False)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True, index=True)
    hashed_password = Column(String(255), nullable=False)
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
