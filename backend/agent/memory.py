"""MAG — Memory-Augmented Generation store.

The memory layer gives the orchestrator personalised continuity: it records the
outcome of every resolved task (the tool recipe used, key arguments, result
summary and user context) and, on a new query, recalls the most relevant past
episodes. When a recalled episode scores above the confidence threshold the
orchestrator can replay its recipe directly — the first step of the
``MAG -> DAG -> RAG -> fallback`` regression.
"""
from __future__ import annotations

import re
import threading
import uuid
from datetime import datetime, timezone


def _tokens(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9_]{2,}", (text or "").lower())}


def _score(query_tokens: set[str], record: dict) -> float:
    """Cosine-ish overlap between query tokens and memory text + tags."""
    body_tokens = _tokens(record["task"]) | _tokens(record["summary"])
    tag_tokens = {t.lower() for t in record.get("tags", [])}
    relevant = body_tokens | tag_tokens
    if not relevant:
        return 0.0
    hit = len(query_tokens & relevant)
    if hit == 0:
        return 0.0
    coverage = hit / max(len(query_tokens), 1)
    precision = hit / len(relevant)
    return 0.7 * coverage + 0.3 * precision


class MemoryStore:
    """In-process, thread-safe episodic memory with relevance recall."""

    def __init__(self, limit: int = 500) -> None:
        self._records: list[dict] = []
        self._limit = limit
        self._lock = threading.Lock()

    def remember(
        self,
        task: str,
        strategy: str,
        recipe: list[dict],
        summary: str,
        tags: list[str] | None = None,
        user_id: str | int | None = None,
        context: dict | None = None,
    ) -> dict:
        record = {
            "id": uuid.uuid4().hex[:12],
            "task": task,
            "strategy": strategy,
            "recipe": recipe,
            "summary": summary,
            "tags": list(tags or []),
            "user_id": user_id,
            "context": context or {},
            "created_at": datetime.now(timezone.utc).isoformat(),
            "hits": 0,
        }
        with self._lock:
            self._records.insert(0, record)
            if len(self._records) > self._limit:
                self._records = self._records[: self._limit]
        return record

    def recall(self, query: str, limit: int = 5) -> list[dict]:
        q = _tokens(query)
        with self._lock:
            scored = []
            for rec in self._records:
                score = _score(q, rec)
                if score > 0:
                    scored.append({"score": round(score, 4), "record": rec})
            scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:limit]

    def best_memory(self, query: str, threshold: float = 0.35) -> dict | None:
        hits = self.recall(query, limit=1)
        if not hits:
            return None
        entry = hits[0]
        if entry["score"] < threshold:
            return None
        record = entry["record"]
        record["hits"] = int(record.get("hits", 0)) + 1
        return {"score": entry["score"], "record": record}

    def count(self) -> int:
        with self._lock:
            return len(self._records)

    def clear(self) -> None:
        with self._lock:
            self._records.clear()


memory_store = MemoryStore()
