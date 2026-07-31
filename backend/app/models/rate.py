from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, ForeignKey
from sqlalchemy.orm import relationship
import enum

from app.database import Base


class RateMode(str, enum.Enum):
    COURIER = "courier"
    FERRY = "ferry"
    TRUCK = "truck"
    AIR = "air"
    RAIL = "rail"
    MULTIMODAL = "multimodal"


class ItemRate(Base):
    __tablename__ = "item_rates"

    id = Column(Integer, primary_key=True, index=True)
    item_id = Column(Integer, ForeignKey("taxonomy_items.id"), nullable=False, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True, index=True)
    origin_region = Column(String(255), nullable=False)
    destination_region = Column(String(255), nullable=False)
    mode = Column(String(50), nullable=False)
    carrier = Column(String(255), nullable=True)
    price_per_kg = Column(Float, nullable=False)
    currency = Column(String(3), default="USD")
    transit_days_min = Column(Integer, nullable=True)
    transit_days_max = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)
    is_active = Column(String(1), default="Y")
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    item = relationship("TaxonomyItem")
    tenant = relationship("Tenant", back_populates="item_rates")
