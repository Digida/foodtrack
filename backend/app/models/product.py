from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Boolean, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from app.database import Base


class ProductCategory(str, enum.Enum):
    FRESH_PRODUCE = "fresh_produce"
    MEAT_POULTRY = "meat_poultry"
    SEAFOOD = "seafood"
    DAIRY = "dairy"
    GRAINS = "grains"
    BEVERAGES = "beverages"
    PROCESSED = "processed"
    OTHER = "other"


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String(100), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    category = Column(SAEnum(ProductCategory), default=ProductCategory.OTHER)
    item_id = Column(Integer, ForeignKey("taxonomy_items.id"), nullable=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True, index=True)
    description = Column(Text, nullable=True)
    origin_country = Column(String(100), nullable=True)
    origin_region = Column(String(255), nullable=True)
    producer_id = Column(Integer, nullable=False)
    producer_name = Column(String(255), nullable=True)
    weight_kg = Column(Float, nullable=True)
    harvest_date = Column(DateTime(timezone=True), nullable=True)
    expiry_date = Column(DateTime(timezone=True), nullable=True)
    storage_requirements = Column(String(500), nullable=True)
    qr_code = Column(Text, nullable=True)
    barcode = Column(Text, nullable=True)
    nfc_tag_id = Column(String(255), nullable=True)
    metadata_json = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    taxonomy_item = relationship("TaxonomyItem", foreign_keys=[item_id])
    tenant = relationship("Tenant", back_populates="products")
