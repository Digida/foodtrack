from sqlalchemy import Column, Integer, String, Text, DateTime, Float, ForeignKey, Enum as SAEnum
from sqlalchemy.sql import func
import enum

from app.database import Base


class EventType(str, enum.Enum):
    HARVEST = "harvest"
    PROCESSING = "processing"
    PACKAGING = "packaging"
    STORAGE = "storage"
    SHIPPING = "shipping"
    IMPORT_CLEARANCE = "import_clearance"
    DISTRIBUTION = "distribution"
    DELIVERY = "delivery"
    RETAIL = "retail"
    VERIFICATION = "verification"


class TraceabilityEvent(Base):
    __tablename__ = "traceability_events"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(String(100), unique=True, index=True, nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    item_id = Column(Integer, ForeignKey("taxonomy_items.id"), nullable=True, index=True)
    event_type = Column(SAEnum(EventType), nullable=False)
    location_name = Column(String(255), nullable=True)
    location_lat = Column(Float, nullable=True)
    location_lng = Column(Float, nullable=True)
    country = Column(String(100), nullable=True)
    city = Column(String(255), nullable=True)
    handler_id = Column(Integer, nullable=False)
    handler_name = Column(String(255), nullable=False)
    handler_organization = Column(String(255), nullable=True)
    temperature_celsius = Column(Float, nullable=True)
    humidity_percent = Column(Float, nullable=True)
    notes = Column(Text, nullable=True)
    attachment_urls = Column(Text, nullable=True)
    qr_scan_id = Column(String(100), nullable=True)
    nfc_scan_id = Column(String(100), nullable=True)
    barcode_scan = Column(String(100), nullable=True)
    event_timestamp = Column(DateTime(timezone=True), nullable=False)
    recorded_at = Column(DateTime(timezone=True), server_default=func.now())
