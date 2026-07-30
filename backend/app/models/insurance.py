from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import relationship
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

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True, index=True)
    item_id = Column(Integer, ForeignKey("taxonomy_items.id"), nullable=False, index=True)
    carrier = Column(String(255), nullable=True)
    policy_number = Column(String(100), nullable=False)
    coverage_amount = Column(Float, nullable=False)
    premium = Column(Float, nullable=True)
    currency = Column(String(3), default="USD")
    valid_from = Column(DateTime, nullable=False)
    valid_until = Column(DateTime, nullable=False)
    is_active = Column(String(1), default="Y")
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    tenant = relationship("Tenant", back_populates="cargo_policies")
    item = relationship("TaxonomyItem")
    creator = relationship("User")


class InsuranceClaim(Base):
    __tablename__ = "insurance_claims"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True, index=True)
    policy_id = Column(Integer, ForeignKey("cargo_policies.id"), nullable=False, index=True)
    incident_type = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    claim_amount = Column(Float, nullable=False)
    currency = Column(String(3), default="USD")
    status = Column(SAEnum(ClaimStatus), default=ClaimStatus.DRAFT)
    documents_json = Column(Text, nullable=True)
    filed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    tenant = relationship("Tenant", back_populates="insurance_claims")
    policy = relationship("CargoPolicy")
    filer = relationship("User")
