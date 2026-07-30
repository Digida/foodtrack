from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
import enum

from app.database import Base


class TelemetryType(str, enum.Enum):
    TEMPERATURE = "temperature"
    HUMIDITY = "humidity"
    SHOCK = "shock"
    LIGHT = "light"
    PRESSURE = "pressure"
    GPS = "gps"


class TelemetryReading(Base):
    __tablename__ = "telemetry_readings"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True, index=True)
    device_id = Column(String(100), nullable=False, index=True)
    telemetry_type = Column(String(50), nullable=False)
    item_id = Column(Integer, ForeignKey("taxonomy_items.id"), nullable=True, index=True)
    batch_id = Column(Integer, ForeignKey("batches.id"), nullable=True, index=True)
    value_float = Column(Float, nullable=True)
    value_str = Column(String(255), nullable=True)
    unit = Column(String(50), nullable=True)
    location_lat = Column(Float, nullable=True)
    location_lng = Column(Float, nullable=True)
    metadata_json = Column(Text, nullable=True)
    recorded_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    tenant = relationship("Tenant", back_populates="telemetry_readings")
    item = relationship("TaxonomyItem")
    batch = relationship("Batch")


class TelemetryAlert(Base):
    __tablename__ = "telemetry_alerts"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True, index=True)
    device_id = Column(String(100), nullable=False)
    telemetry_type = Column(String(50), nullable=False)
    rule_name = Column(String(100), nullable=False)
    threshold = Column(Float, nullable=True)
    actual_value = Column(Float, nullable=True)
    message = Column(Text, nullable=True)
    severity = Column(String(20), default="warning")
    acknowledged = Column(Boolean, default=False)
    acknowledged_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    tenant = relationship("Tenant", back_populates="telemetry_alerts")
    ack_user = relationship("User")
