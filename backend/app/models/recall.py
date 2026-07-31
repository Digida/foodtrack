from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Index
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import relationship
import enum

from app.database import Base


class RecallSeverity(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RecallStatus(str, enum.Enum):
    INITIATED = "initiated"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class Recall(Base):
    __tablename__ = "recalls"
    __table_args__ = (
        Index("ix_recalls_status", "status"),
    )

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True, index=True)
    batch_id = Column(Integer, ForeignKey("batches.id"), nullable=False, index=True)
    item_id = Column(Integer, ForeignKey("taxonomy_items.id"), nullable=True, index=True)
    reason = Column(Text, nullable=False)
    severity = Column(SAEnum(RecallSeverity, native_enum=False), default=RecallSeverity.MEDIUM)
    status = Column(SAEnum(RecallStatus, native_enum=False), default=RecallStatus.INITIATED)
    affected_region = Column(String(255), nullable=True)
    notified_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    tenant = relationship("Tenant", back_populates="recalls")
    batch = relationship("Batch")
    item = relationship("TaxonomyItem")
    creator = relationship("User")
    events = relationship("RecallEvent", back_populates="recall")


class RecallEvent(Base):
    __tablename__ = "recall_events"

    id = Column(Integer, primary_key=True, index=True)
    recall_id = Column(Integer, ForeignKey("recalls.id"), nullable=False, index=True)
    action = Column(String(50), nullable=False)
    description = Column(Text, nullable=True)
    performed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    recall = relationship("Recall", back_populates="events")
    performer = relationship("User")
