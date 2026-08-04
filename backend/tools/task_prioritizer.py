"""Task Prioritizer Tool — ranks a user's pending pipeline tasks.

Orders tasks by due date, severity, stage dependency and assignment age so the
AI can tell a user what to do next. Tasks are plain dicts; the tool is
deterministic and side-effect free.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from agent.base_tool import BaseTool

logger = logging.getLogger(__name__)

SEVERITY_WEIGHT = {"critical": 100, "high": 60, "medium": 30, "low": 10}
STAGE_PRIORITY = {"escrow": 5, "settlement": 4, "certification": 4, "delivery": 3, "sourcing": 2, "admin": 1}


def _priority_score(task: dict, now: datetime) -> float:
    severity = SEVERITY_WEIGHT.get(str(task.get("severity", "medium")).lower(), 30)
    stage = STAGE_PRIORITY.get(str(task.get("stage", "admin")).lower(), 1)
    due = task.get("due_at")
    due_bonus = 0.0
    if due:
        try:
            due_dt = datetime.fromisoformat(str(due).replace("Z", "+00:00"))
            delta_days = (due_dt - now).total_seconds() / 86400.0
            if delta_days < 0:
                due_bonus = 40.0  # overdue
            elif delta_days <= 1:
                due_bonus = 25.0
            elif delta_days <= 3:
                due_bonus = 10.0
        except (ValueError, TypeError):
            due_bonus = 0.0
    return severity + stage * 5 + due_bonus


def prioritize_tasks(tasks: list[dict]) -> dict:
    """Rank tasks by urgency, returning a work order with reasons."""
    if not tasks:
        return {"status": "ok", "task_count": 0, "work_order": []}

    now = datetime.now(timezone.utc)
    scored = []
    for task in tasks:
        score = _priority_score(task, now)
        scored.append({
            "id": task.get("id"),
            "title": task.get("title") or task.get("task") or f"task-{task.get('id')}",
            "entity": task.get("entity"),
            "entity_id": task.get("entity_id"),
            "severity": task.get("severity", "medium"),
            "stage": task.get("stage", "admin"),
            "due_at": task.get("due_at"),
            "priority_score": round(score, 1),
        })

    scored.sort(key=lambda t: t["priority_score"], reverse=True)
    for rank, t in enumerate(scored, start=1):
        t["rank"] = rank

    return {
        "status": "ok",
        "task_count": len(scored),
        "work_order": scored,
        "next_task": scored[0] if scored else None,
    }


class TaskPrioritizerTool(BaseTool):
    name = "task_prioritizer"
    description = "Rank a user's pending bulking/escrow/settlement tasks into a work order by urgency."
    parameters = {
        "type": "object",
        "properties": {
            "tasks": {
                "type": "array",
                "items": {"type": "object"},
                "description": "Tasks: [{id, title, entity, entity_id, severity, stage, due_at}]",
            }
        },
        "required": ["tasks"],
    }

    @classmethod
    def check_available(cls) -> bool:
        return True

    def execute(self, **kwargs: Any) -> str:
        result = prioritize_tasks(kwargs.get("tasks", []))
        return json.dumps(result, ensure_ascii=False)
