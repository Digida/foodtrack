from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Boolean, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import relationship
import enum

from app.database import Base


class BatchStatus(str, enum.Enum):
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    RECALLED = "recalled"
    EXPIRED = "expired"


class ShipmentStatus(str, enum.Enum):
    CREATED = "created"
    PICKED_UP = "picked_up"
    IN_TRANSIT = "in_transit"
    AT_FERRY = "at_ferry"
    ON_FERRY = "on_ferry"
    ARRIVED_PORT = "arrived_port"
    OUT_FOR_DELIVERY = "out_for_delivery"
    DELIVERED = "delivered"
    EXCEPTION = "exception"


class ShipmentMode(str, enum.Enum):
    COURIER = "courier"
    FERRY = "ferry"
    TRUCK = "truck"
    AIR = "air"
    RAIL = "rail"
    MULTIMODAL = "multimodal"


class ItemShipmentStatus(str, enum.Enum):
    PENDING = "pending"
    LOADED = "loaded"
    IN_TRANSIT = "in_transit"
    DELIVERED = "delivered"
    EXCEPTION = "exception"


class Batch(Base):
    __tablename__ = "batches"

    id = Column(Integer, primary_key=True, index=True)
    batch_number = Column(String(100), unique=True, index=True, nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    item_id = Column(Integer, ForeignKey("taxonomy_items.id"), nullable=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True, index=True)
    quantity = Column(Integer, nullable=False, default=0)
    serial_number = Column(String(255), nullable=True, index=True)
    manufacturer_part_number = Column(String(255), nullable=True)
    status = Column(SAEnum(BatchStatus), default=BatchStatus.PENDING)
    production_date = Column(DateTime(timezone=True), nullable=True)
    expiry_date = Column(DateTime(timezone=True), nullable=True)
    notes = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    tenant = relationship("Tenant", back_populates="batches")
    product = relationship("Product")
    warehouse_items = relationship("WarehouseItem", back_populates="batch", cascade="all, delete-orphan")
    tracking_events = relationship("TrackingEvent", back_populates="batch", cascade="all, delete-orphan")


class Warehouse(Base):
    __tablename__ = "warehouses"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, nullable=False)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True, index=True)
    name = Column(String(255), nullable=False)
    address = Column(Text, nullable=True)
    city = Column(String(255), nullable=True)
    country = Column(String(100), nullable=True)
    lat = Column(Float, nullable=True)
    lng = Column(Float, nullable=True)
    contact_name = Column(String(255), nullable=True)
    contact_phone = Column(String(50), nullable=True)
    capacity_items = Column(Integer, nullable=True)
    temperature_celsius = Column(Float, nullable=True)
    humidity_percent = Column(Float, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    tenant = relationship("Tenant", back_populates="warehouses")
    items = relationship("WarehouseItem", back_populates="warehouse", cascade="all, delete-orphan")


class WarehouseItem(Base):
    __tablename__ = "warehouse_items"

    id = Column(Integer, primary_key=True, index=True)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=False)
    batch_id = Column(Integer, ForeignKey("batches.id"), nullable=False)
    item_id = Column(Integer, ForeignKey("taxonomy_items.id"), nullable=True, index=True)
    quantity = Column(Integer, nullable=False, default=0)
    location_zone = Column(String(100), nullable=True)
    location_rack = Column(String(100), nullable=True)
    location_bin = Column(String(100), nullable=True)
    last_counted_at = Column(DateTime(timezone=True), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    warehouse = relationship("Warehouse", back_populates="items")
    batch = relationship("Batch", back_populates="warehouse_items")
    item = relationship("TaxonomyItem", foreign_keys=[item_id])


class Shipment(Base):
    __tablename__ = "shipments"

    id = Column(Integer, primary_key=True, index=True)
    shipment_number = Column(String(100), unique=True, index=True, nullable=False)
    mode = Column(SAEnum(ShipmentMode), nullable=False)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True, index=True)
    status = Column(SAEnum(ShipmentStatus), default=ShipmentStatus.CREATED)
    origin_id = Column(Integer, ForeignKey("warehouses.id"), nullable=True)
    destination_id = Column(Integer, ForeignKey("warehouses.id"), nullable=True)
    carrier_name = Column(String(255), nullable=True)
    carrier_ref = Column(String(255), nullable=True)
    vessel_name = Column(String(255), nullable=True)
    ferry_route = Column(String(255), nullable=True)
    courier_tracking_code = Column(String(255), nullable=True)
    courier_url = Column(String(500), nullable=True)
    estimated_departure = Column(DateTime(timezone=True), nullable=True)
    estimated_arrival = Column(DateTime(timezone=True), nullable=True)
    actual_departure = Column(DateTime(timezone=True), nullable=True)
    actual_arrival = Column(DateTime(timezone=True), nullable=True)
    total_weight_kg = Column(Float, nullable=True)
    total_volume_m3 = Column(Float, nullable=True)
    notes = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    tenant = relationship("Tenant", back_populates="shipments")
    origin = relationship("Warehouse", foreign_keys=[origin_id])
    destination = relationship("Warehouse", foreign_keys=[destination_id])
    batches = relationship("ShipmentBatch", back_populates="shipment", cascade="all, delete-orphan")
    tracking_events = relationship("ShipmentTrackingEvent", back_populates="shipment", cascade="all, delete-orphan")


class ShipmentBatch(Base):
    __tablename__ = "shipment_batches"

    id = Column(Integer, primary_key=True, index=True)
    shipment_id = Column(Integer, ForeignKey("shipments.id"), nullable=False)
    batch_id = Column(Integer, ForeignKey("batches.id"), nullable=False)
    item_id = Column(Integer, ForeignKey("taxonomy_items.id"), nullable=True, index=True)
    quantity = Column(Integer, nullable=False)
    item_shipment_status = Column(SAEnum(ItemShipmentStatus), default=ItemShipmentStatus.PENDING, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    shipment = relationship("Shipment", back_populates="batches")
    batch = relationship("Batch")
    item = relationship("TaxonomyItem", foreign_keys=[item_id])


class TrackingEvent(Base):
    __tablename__ = "tracking_events"

    id = Column(Integer, primary_key=True, index=True)
    batch_id = Column(Integer, ForeignKey("batches.id"), nullable=False)
    event_type = Column(String(100), nullable=False)
    location_name = Column(String(255), nullable=True)
    lat = Column(Float, nullable=True)
    lng = Column(Float, nullable=True)
    temperature_celsius = Column(Float, nullable=True)
    humidity_percent = Column(Float, nullable=True)
    recorded_by = Column(String(255), nullable=True)
    notes = Column(Text, nullable=True)
    event_timestamp = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    batch = relationship("Batch", back_populates="tracking_events")


class ShipmentTrackingEvent(Base):
    __tablename__ = "shipment_tracking_events"

    id = Column(Integer, primary_key=True, index=True)
    shipment_id = Column(Integer, ForeignKey("shipments.id"), nullable=False)
    item_id = Column(Integer, ForeignKey("taxonomy_items.id"), nullable=True, index=True)
    status = Column(String(100), nullable=False)
    location_name = Column(String(255), nullable=True)
    lat = Column(Float, nullable=True)
    lng = Column(Float, nullable=True)
    message = Column(Text, nullable=True)
    carrier_status = Column(String(255), nullable=True)
    estimated_next_update = Column(DateTime(timezone=True), nullable=True)
    event_timestamp = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    shipment = relationship("Shipment", back_populates="tracking_events")


class Collection(Base):
    __tablename__ = "collections"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, nullable=False)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True, index=True)
    description = Column(Text, nullable=True)
    image_url = Column(String(500), nullable=True)
    is_ai_generated = Column(Boolean, default=False)
    feed_source_id = Column(Integer, ForeignKey("feed_sources.id"), nullable=True)
    is_active = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    tenant = relationship("Tenant", back_populates="collections")
    feed_source = relationship("FeedSource")
    items = relationship("CollectionItem", back_populates="collection", cascade="all, delete-orphan")


class CollectionItem(Base):
    __tablename__ = "collection_items"

    id = Column(Integer, primary_key=True, index=True)
    collection_id = Column(Integer, ForeignKey("collections.id"), nullable=False)
    item_id = Column(Integer, ForeignKey("taxonomy_items.id"), nullable=False)
    sort_order = Column(Integer, default=0)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    collection = relationship("Collection", back_populates="items")
    item = relationship("TaxonomyItem")


class FeedSource(Base):
    __tablename__ = "feed_sources"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    url = Column(String(500), nullable=True)
    feed_type = Column(String(50), default="rss")
    taxonomy_target_id = Column(Integer, ForeignKey("taxonomies.id"), nullable=True)
    node_target_id = Column(Integer, ForeignKey("taxonomy_nodes.id"), nullable=True)
    schedule_minutes = Column(Integer, default=1440)
    last_fetched_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True)
    api_key = Column(String(500), nullable=True)
    config_json = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    taxonomy_target = relationship("Taxonomy")
