"""Job Availability Tool — checks whether an assignee is available.

Detects conflicts between an assignee's existing job slots and a requested
window, and finds the next free slot. Used by the Job Assigner and by the AI
when proposing courier/verifier/packer assignments.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from agent.base_tool import BaseTool

logger = logging.getLogger(__name__)


def _parse_dt(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def check_availability(
    assignee_id: Any,
    job_slots: list[dict],
    requested_start: str | None = None,
    requested_end: str | None = None,
    minimum_gap_minutes: int = 60,
) -> dict:
    """Check an assignee's availability in a requested window.

    job_slots: [{id, start, end}] — existing assignments for the assignee.
    requested_start/end: ISO datetimes. When omitted, checks against all slots
    and returns the next free window.
    """
    slots = []
    for s in job_slots or []:
        start = _parse_dt(s.get("start") or s.get("start_at") or s.get("scheduled_at"))
        end = _parse_dt(s.get("end") or s.get("end_at") or s.get("scheduled_at"))
        if start and end:
            slots.append({"id": s.get("id"), "start": start, "end": end})

    if not slots:
        return {
            "status": "ok",
            "assignee_id": assignee_id,
            "available": True,
            "conflicts": [],
            "next_free": "immediately",
        }

    req_start = _parse_dt(requested_start)
    req_end = _parse_dt(requested_end)

    conflicts = []
    if req_start and req_end:
        gap = timedelta(minutes=minimum_gap_minutes)
        for s in slots:
            busy_start = s["start"] - gap
            busy_end = s["end"] + gap
            if req_start < busy_end and req_end > busy_start:
                conflicts.append({
                    "slot_id": s["id"],
                    "busy_start": s["start"].isoformat(),
                    "busy_end": s["end"].isoformat(),
                })
        available = not conflicts
    else:
        available = True
        conflicts = []

    # Next free slot = one hour after the latest busy window.
    latest_end = max((s["end"] for s in slots), default=datetime.now(timezone.utc))
    next_free = latest_end + timedelta(hours=1)

    return {
        "status": "ok",
        "assignee_id": assignee_id,
        "available": available,
        "conflicts": conflicts,
        "busy_slot_count": len(slots),
        "next_free": next_free.isoformat(),
    }


class JobAvailabilityTool(BaseTool):
    name = "job_availability"
    description = (
        "Check an assignee's availability for a job slot, detecting conflicts and "
        "returning the next free window."
    )
    parameters = {
        "type": "object",
        "properties": {
            "assignee_id": {"type": ["integer", "string"], "description": "Assignee identifier"},
            "job_slots": {
                "type": "array",
                "items": {"type": "object"},
                "description": "Existing slots: [{id, start, end}]",
            },
            "requested_start": {"type": "string", "description": "Requested start (ISO datetime)"},
            "requested_end": {"type": "string", "description": "Requested end (ISO datetime)"},
            "minimum_gap_minutes": {"type": "integer", "description": "Required gap between slots"},
        },
        "required": ["assignee_id", "job_slots"],
    }

    @classmethod
    def check_available(cls) -> bool:
        return True

    def execute(self, **kwargs: Any) -> str:
        result = check_availability(
            kwargs.get("assignee_id"),
            kwargs.get("job_slots", []),
            kwargs.get("requested_start"),
            kwargs.get("requested_end"),
            kwargs.get("minimum_gap_minutes", 60),
        )
        return json.dumps(result, ensure_ascii=False)
