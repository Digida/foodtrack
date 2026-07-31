from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, Text, DateTime, Float, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import relationship
import enum

from app.database import Base


class MovementType(str, enum.Enum):
    INBOUND = "inbound"
    OUTBOUND = "outbound"
    TRANSFER = "transfer"
    ADJUSTMENT = "adjustment"
    WRITE_OFF = "write_off"


class MovementReference(str, enum.Enum):
    SHIPMENT = "shipment"
    RECEIPT = "receipt"
    TRANSFER_ORDER = "transfer_order"
    AUDIT = "audit"
    MANUAL = "manual"


class ItemInventory(Base):
    __tablename__ = "item_inventory"

    id = Column(Integer, primary_key=True, index=True)
    item_id = Column(Integer, ForeignKey("taxonomy_items.id"), nullable=False, index=True)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=False, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True, index=True)
    total_quantity = Column(Integer, nullable=False, default=0)
    available_quantity = Column(Integer, nullable=False, default=0)
    reserved_quantity = Column(Integer, nullable=False, default=0)
    avg_temperature_celsius = Column(Float, nullable=True)
    avg_humidity_percent = Column(Float, nullable=True)
    last_stocked_at = Column(DateTime(timezone=True), nullable=True)
    last_counted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    item = relationship("TaxonomyItem")
    warehouse = relationship("Warehouse")
    tenant = relationship("Tenant", back_populates="inventory_records")


class InventoryMovement(Base):
    __tablename__ = "inventory_movements"

    id = Column(Integer, primary_key=True, index=True)
    item_id = Column(Integer, ForeignKey("taxonomy_items.id"), nullable=False, index=True)
    batch_id = Column(Integer, ForeignKey("batches.id"), nullable=True)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=True)
    movement_type = Column(SAEnum(MovementType, native_enum=False), nullable=False)
    quantity = Column(Integer, nullable=False)
    reference_type = Column(SAEnum(MovementReference, native_enum=False), nullable=True)
    reference_id = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)
    moved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    moved_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    item = relationship("TaxonomyItem")
    batch = relationship("Batch")
    warehouse = relationship("Warehouse")
