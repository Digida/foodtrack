from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import relationship
import enum

from app.database import Base


class EnrichmentSource(str, enum.Enum):
    WEB_SEARCH = "web_search"
    WEB_READER = "web_reader"
    RSS_FEED = "rss_feed"
    NUTRITION_API = "nutrition_api"
    PRICE_API = "price_api"
    TRANSLATOR = "translator"
    MANUAL = "manual"


class EnrichmentStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class EnrichmentLog(Base):
    __tablename__ = "enrichment_logs"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True, index=True)
    source = Column(SAEnum(EnrichmentSource), default=EnrichmentSource.WEB_SEARCH)
    status = Column(SAEnum(EnrichmentStatus), default=EnrichmentStatus.PENDING)
    entity_type = Column(String(50), nullable=True)
    entity_id = Column(Integer, nullable=True)
    summary = Column(Text, nullable=True)
    details = Column(Text, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    triggered_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime(timezone=True), nullable=True)

    tenant = relationship("Tenant", back_populates="enrichment_logs")
    trigger_user = relationship("User")


class EnrichmentSuggestion(Base):
    __tablename__ = "enrichment_suggestions"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True, index=True)
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(Integer, nullable=True)
    suggestion_type = Column(String(50), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    confidence = Column(String(20), default="medium")
    source = Column(String(255), nullable=True)
    payload_json = Column(Text, nullable=True)
    status = Column(String(20), default="open")
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    tenant = relationship("Tenant", back_populates="enrichment_suggestions")
    creator = relationship("User")
