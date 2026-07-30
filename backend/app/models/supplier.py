from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey, Boolean, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class Supplier(Base):
    __tablename__ = "suppliers"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True, index=True)
    name = Column(String(255), nullable=False)
    contact_name = Column(String(255), nullable=True)
    contact_email = Column(String(255), nullable=True)
    contact_phone = Column(String(50), nullable=True)
    address = Column(Text, nullable=True)
    regions = Column(Text, nullable=True)
    certifications = Column(Text, nullable=True)
    # Fixed: was String(1) defaulting to "Y" — now a proper Boolean
    is_active = Column(Boolean, default=True, nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    tenant = relationship("Tenant", back_populates="suppliers")
    creator = relationship("User")


class SupplierScorecard(Base):
    __tablename__ = "supplier_scorecards"
    __table_args__ = (
        # Composite index: fastest path for per-supplier ranking queries
        Index("ix_supplier_scorecards_supplier_score", "supplier_id", "overall_score"),
    )

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True, index=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=False, index=True)
    # Period enforced to YYYY-QN or YYYY-MM format at the service/route layer
    period = Column(String(20), nullable=False)
    on_time_delivery_pct = Column(Float, nullable=True)
    quality_score = Column(Float, nullable=True)
    cert_compliance_pct = Column(Float, nullable=True)
    audit_result = Column(String(50), nullable=True)
    overall_score = Column(Float, nullable=True, index=True)
    notes = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    tenant = relationship("Tenant", back_populates="supplier_scorecards")
    supplier = relationship("Supplier")
    creator = relationship("User")
