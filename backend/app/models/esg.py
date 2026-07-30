from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship

from app.database import Base


class ItemCarbonFootprint(Base):
    __tablename__ = "item_carbon_footprints"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True, index=True)
    item_id = Column(Integer, ForeignKey("taxonomy_items.id"), nullable=False, index=True)
    kg_co2e_per_kg = Column(Float, nullable=False)
    water_usage_l_per_kg = Column(Float, nullable=True)
    source = Column(String(255), nullable=True)
    methodology = Column(String(100), nullable=True)
    confidence = Column(String(20), default="medium")
    metadata_json = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    tenant = relationship("Tenant", back_populates="carbon_footprints")
    item = relationship("TaxonomyItem")
    creator = relationship("User")
