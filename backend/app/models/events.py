from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
import enum

from app.database import Base


class WebhookEvent(str, enum.Enum):
    ITEM_TRACKING_UPDATED = "item.tracking.updated"
    ITEM_INVENTORY_CHANGED = "item.inventory.changed"
    CARGO_STATUS_CHANGED = "cargo.status.changed"
    CERTIFICATE_EXPIRING = "certificate.expiring"
    BATCH_RECALLED = "batch.recalled"
    TELEMETRY_ALERT = "telemetry.alert"


class WebhookSubscription(Base):
    __tablename__ = "webhook_subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True, index=True)
    url = Column(String(512), nullable=False)
    secret = Column(String(128), nullable=True)
    events = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    tenant = relationship("Tenant", back_populates="webhook_subscriptions")
    creator = relationship("User")


class EventLog(Base):
    __tablename__ = "event_logs"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True, index=True)
    event_type = Column(String(50), nullable=False, index=True)
    channel = Column(String(255), nullable=True)
    payload_json = Column(Text, nullable=True)
    source_ip = Column(String(45), nullable=True)
    published_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    tenant = relationship("Tenant", back_populates="event_logs")
    publisher = relationship("User")
