from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey, Boolean, JSON, Index
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from app.database import Base


class ClaimStatus(str, enum.Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    PAID = "paid"


class CargoPolicy(Base):
    __tablename__ = "cargo_policies"
    __table_args__ = (
        Index("ix_cargo_policies_item_active", "item_id", "is_active"),
    )

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True, index=True)
    item_id = Column(Integer, ForeignKey("taxonomy_items.id"), nullable=False, index=True)
    carrier = Column(String(255), nullable=True)
    policy_number = Column(String(100), nullable=False)
    coverage_amount = Column(Float, nullable=False)
    premium = Column(Float, nullable=True)
    currency = Column(String(3), default="USD")
    valid_from = Column(DateTime(timezone=True), nullable=False)
    valid_until = Column(DateTime(timezone=True), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    tenant = relationship("Tenant", back_populates="cargo_policies")
    item = relationship("TaxonomyItem")
    creator = relationship("User")


class InsuranceClaim(Base):
    __tablename__ = "insurance_claims"
    __table_args__ = (
        # Index on status for filtering claims by lifecycle state
        Index("ix_insurance_claims_status", "status"),
    )

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True, index=True)
    policy_id = Column(Integer, ForeignKey("cargo_policies.id"), nullable=False, index=True)
    incident_type = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    claim_amount = Column(Float, nullable=False)
    currency = Column(String(3), default="USD")
    status = Column(SAEnum(ClaimStatus, native_enum=False), default=ClaimStatus.DRAFT, nullable=False)
    # Fixed: was Text — now JSON so documents are stored/returned as a proper array
    documents_json = Column(JSON, nullable=True)
    filed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    tenant = relationship("Tenant", back_populates="insurance_claims")
    policy = relationship("CargoPolicy")
    filer = relationship("User")
