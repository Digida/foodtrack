"""Workflow Engine Tool — validates the bulking pipeline state machine.

Encodes the legal state transitions for registers, bids, deals, warehouse
bookings, courier jobs, job assignments, escrow and settlements. The AI uses it
to check whether a proposed action is legal before calling the service layer —
mirroring the service-layer transition maps so proposals fail fast.
"""
from __future__ import annotations

import json
import logging
from typing import Any

from agent.base_tool import BaseTool

logger = logging.getLogger(__name__)

# Entity → legal transition map. Any pair not listed is illegal.
TRANSITIONS: dict[str, dict[str, list[str]]] = {
    "register": {
        "draft": ["sourcing"],
        "sourcing": ["aggregated", "cancelled"],
        "aggregated": ["closed", "cancelled"],
        "closed": [],
        "cancelled": [],
    },
    "bid": {
        "pending": ["accepted", "rejected", "withdrawn"],
        "accepted": [],
        "rejected": [],
        "withdrawn": [],
    },
    "deal": {
        "negotiating": ["agreed", "cancelled"],
        "agreed": ["closed", "cancelled"],
        "closed": [],
        "cancelled": [],
    },
    "warehouse_booking": {
        "requested": ["confirmed", "cancelled"],
        "confirmed": ["in_use", "cancelled"],
        "in_use": ["completed", "cancelled"],
        "completed": [],
        "cancelled": [],
    },
    "courier_job": {
        "posted": ["assigned", "cancelled"],
        "assigned": ["in_transit", "cancelled"],
        "in_transit": ["delivered", "cancelled"],
        "delivered": [],
        "cancelled": [],
    },
    "job_assignment": {
        "assigned": ["in_progress", "cancelled"],
        "in_progress": ["completed", "cancelled"],
        "completed": [],
        "cancelled": [],
    },
    "escrow": {
        "required": ["deposited"],
        "deposited": ["held", "refunded"],
        "held": ["released", "refunded"],
        "released": [],
        "refunded": [],
    },
    "settlement": {
        "pending": ["paid", "failed", "cancelled"],
        "paid": [],
        "failed": ["pending"],
        "cancelled": [],
    },
}


def validate_transition(entity: str, current: str, target: str) -> dict:
    """Check whether target is a legal transition from current for an entity."""
    entity = (entity or "").lower().replace("-", "_")
    current = (current or "").lower()
    target = (target or "").lower()

    if entity not in TRANSITIONS:
        return {"status": "error", "message": f"Unknown entity '{entity}'", "allowed": False}

    allowed_targets = TRANSITIONS[entity]
    if current not in allowed_targets:
        return {
            "status": "error",
            "message": f"'{current}' is not a known state for {entity}",
            "allowed": False,
            "known_states": list(allowed_targets),
        }

    legal = target in allowed_targets[current]
    return {
        "status": "ok",
        "entity": entity,
        "current": current,
        "target": target,
        "allowed": legal,
        "allowed_transitions": allowed_targets[current],
        "message": "Transition allowed." if legal else f"Transition '{current}' -> '{target}' is not allowed for {entity}.",
    }


def pipeline_stage(register_status: str, entity_statuses: dict | None = None) -> dict:
    """Compute the current bulking pipeline stage and the next actions."""
    register_status = (register_status or "draft").lower()
    entity_statuses = entity_statuses or {}

    stage_order = ["sourcing", "aggregation", "escrow", "fulfilment", "settlement"]
    register_stage = {
        "draft": "planning",
        "sourcing": "sourcing",
        "aggregated": "aggregation",
        "closed": "settlement",
        "cancelled": "cancelled",
    }.get(register_status, "planning")

    next_actions = []
    if register_stage == "planning":
        next_actions.append("Set a target price and move the register to sourcing.")
    if register_stage == "sourcing":
        next_actions.append("Evaluate bids and accept the ones inside the acceptance window.")
    if register_stage == "aggregation":
        if not entity_statuses.get("warehouse_booking"):
            next_actions.append("Confirm a warehouse booking for the aggregated stock.")
        if not entity_statuses.get("courier_job"):
            next_actions.append("Post a courier job to move stock to the warehouse or buyer.")
        if not entity_statuses.get("escrow"):
            next_actions.append("Deposit the investor escrow before the pipeline continues.")
        next_actions.append("Close deals to lock prices and exchange credentials.")
    if register_stage == "settlement":
        if entity_statuses.get("escrow") != "released":
            next_actions.append("Confirm buyer delivery to release escrow to the seller.")
        next_actions.append("Run settlements and mark them paid.")

    return {
        "status": "ok",
        "register_status": register_status,
        "stage": register_stage,
        "stage_index": stage_order.index(register_stage) if register_stage in stage_order else -1,
        "next_actions": next_actions,
    }


class WorkflowEngineTool(BaseTool):
    name = "workflow_engine"
    description = (
        "Validate bulking pipeline state-machine transitions and compute the current "
        "pipeline stage with next actions."
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {"type": "string", "enum": ["validate", "stage"], "description": "Action to perform"},
            "entity": {
                "type": "string",
                "enum": list(TRANSITIONS.keys()),
                "description": "Entity whose state machine to check",
            },
            "current": {"type": "string", "description": "Current status"},
            "target": {"type": "string", "description": "Proposed target status"},
            "register_status": {"type": "string", "description": "Register status for stage computation"},
            "entity_statuses": {"type": "object", "description": "Map of entity -> status for stage computation"},
        },
        "required": ["action"],
    }

    @classmethod
    def check_available(cls) -> bool:
        return True

    def execute(self, **kwargs: Any) -> str:
        action = kwargs.get("action", "")
        if action == "validate":
            result = validate_transition(
                kwargs.get("entity", ""),
                kwargs.get("current", ""),
                kwargs.get("target", ""),
            )
        elif action == "stage":
            result = pipeline_stage(
                kwargs.get("register_status", "draft"),
                kwargs.get("entity_statuses"),
            )
        else:
            result = {"status": "error", "message": f"Unknown action: {action}"}
        return json.dumps(result, ensure_ascii=False)
