from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Index
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from app.database import Base


class CertificateStatus(str, enum.Enum):
    DRAFT = "draft"
    ISSUED = "issued"
    VERIFIED = "verified"
    ACTIVE = "active"
    REVOKED = "revoked"
    EXPIRED = "expired"


class CertificateRequestStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class CertificateType(str, enum.Enum):
    ORIGIN = "origin"
    ORGANIC = "organic"
    HALAL = "halal"
    QUALITY = "quality"
    SAFETY = "safety"
    FAIR_TRADE = "fair_trade"
    GLOBALGAP = "globalgap"
    GRASP = "grasp"
    SMETA = "smeta"
    BRC = "brc"
    IFS = "ifs"
    FSSC22000 = "fssc22000"
    ISO22000 = "iso22000"
    RAINFOREST_ALLIANCE = "rainforest_alliance"
    UTZ = "utz"
    MSC = "msc"
    ASC = "asc"
    CUSTOM = "custom"


class Certificate(Base):
    __tablename__ = "certificates"
    __table_args__ = (
        # Index on expiry_date: used by notify_expiring_certificates and get_metrics
        Index("ix_certificates_expiry_date", "expiry_date"),
    )

    id = Column(Integer, primary_key=True, index=True)
    certificate_id = Column(String(100), unique=True, index=True, nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True)
    item_id = Column(Integer, ForeignKey("taxonomy_items.id"), nullable=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True, index=True)
    type = Column(SAEnum(CertificateType, native_enum=False), nullable=False)
    status = Column(SAEnum(CertificateStatus, native_enum=False), default=CertificateStatus.DRAFT)
    issuer_id = Column(Integer, nullable=False)
    issuer_name = Column(String(255), nullable=False)
    issuing_body = Column(String(255), nullable=True)
    recipient_entity = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    issued_date = Column(DateTime(timezone=True), server_default=func.now())
    expiry_date = Column(DateTime(timezone=True), nullable=True)
    verified_date = Column(DateTime(timezone=True), nullable=True)
    verified_by = Column(Integer, nullable=True)
    digital_signature = Column(Text, nullable=True)
    blockchain_hash = Column(String(255), nullable=True)
    document_url = Column(String(500), nullable=True)
    metadata_json = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    tenant = relationship("Tenant", back_populates="certificates")


class CertificateRequest(Base):
    __tablename__ = "certificate_requests"

    id = Column(Integer, primary_key=True, index=True)
    cargo_id = Column(Integer, ForeignKey("cargo_registrations.id"), nullable=True, index=True)
    item_id = Column(Integer, ForeignKey("taxonomy_items.id"), nullable=False, index=True)
    requested_type = Column(SAEnum(CertificateType, native_enum=False), nullable=False)
    status = Column(SAEnum(CertificateRequestStatus, native_enum=False), default=CertificateRequestStatus.PENDING)
    applicant_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    applicant_notes = Column(Text, nullable=True)
    target_market = Column(String(100), nullable=True)
    reviewer_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    reviewer_notes = Column(Text, nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    cargo = relationship("CargoRegistration")
    item = relationship("TaxonomyItem")
    applicant = relationship("User", foreign_keys=[applicant_id])
    reviewer = relationship("User", foreign_keys=[reviewer_id])
