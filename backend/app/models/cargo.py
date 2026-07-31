from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import relationship
import enum

from app.database import Base


class CargoStatus(str, enum.Enum):
    DRAFT = "draft"
    REGISTERED = "registered"
    CERTIFIED = "certified"
    IN_TRANSIT = "in_transit"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class CargoRegistration(Base):
    __tablename__ = "cargo_registrations"

    id = Column(Integer, primary_key=True, index=True)
    item_id = Column(Integer, ForeignKey("taxonomy_items.id"), nullable=False, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True, index=True)
    quantity = Column(Integer, nullable=False)
    unit = Column(String(50), nullable=True)
    origin_location = Column(String(255), nullable=True)
    destination_location = Column(String(255), nullable=True)
    mode = Column(String(50), nullable=True)
    status = Column(SAEnum(CargoStatus), default=CargoStatus.DRAFT)
    carrier_name = Column(String(255), nullable=True)
    carrier_ref = Column(String(255), nullable=True)
    tracking_number = Column(String(255), nullable=True)
    estimated_departure = Column(DateTime(timezone=True), nullable=True)
    estimated_arrival = Column(DateTime(timezone=True), nullable=True)
    weight_kg = Column(Float, nullable=True)
    volume_m3 = Column(Float, nullable=True)
    notes = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    item = relationship("TaxonomyItem")
    creator = relationship("User")
    tenant = relationship("Tenant", back_populates="cargo_registrations")
