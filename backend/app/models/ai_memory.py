import enum
from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, Text, DateTime, Float, JSON, ForeignKey
from sqlalchemy import Enum as SAEnum

from app.database import Base
from app.models.user import enum_values


class MemoryStrategy(str, enum.Enum):
    """Which regression tier resolved the task."""
    MAG = "mag"
    DAG = "dag"
    RAG = "rag"
    FALLBACK = "fallback"


class AiMemory(Base):
    """Persisted episodic memory for the MAG tier.

    Records how a task was resolved (strategy, tool recipe, outcome) so the
    orchestrator can replay the same recipe on future, similar tasks instead of
    re-deriving it. Mirrors the in-process MemoryStore but survives restarts.
    """

    __tablename__ = "ai_memories"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    task = Column(String(1000), nullable=False)
    strategy = Column(
        SAEnum(MemoryStrategy, native_enum=False, values_callable=enum_values),
        nullable=False,
    )
    # [{tool, args}] — the exact recipe that resolved the task.
    recipe = Column(JSON, nullable=False)
    summary = Column(Text, nullable=True)
    # e.g. ["dag", "bulking_sourcing"]
    tags = Column(JSON, nullable=True)
    # match confidence recorded when this episode was used.
    confidence = Column(Float, nullable=True)
    hits = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
