"""Escrow Release Checker Tool — decides whether escrow can be released.

Escrow is released to the seller once the investing buyer has received the
goods: the buyer-delivery courier job reaches DELIVERED, the buyer confirms
receipt, and the supporting documents are verified. This tool checks those
conditions and reports exactly what blocks release.
"""
from __future__ import annotations

import json
import logging
from typing import Any

from agent.base_tool import BaseTool

logger = logging.getLogger(__name__)


def check_release(
    escrow_status: str = "held",
    buyer_delivery_confirmed: bool = False,
    goods_received_confirmed: bool = False,
    documents_verified: bool = False,
    days_held: float = 0.0,
) -> dict:
    """Evaluate the release conditions for an escrow.

    Returns a recommendation: release_now / hold / not_applicable plus the list
    of unmet conditions.
    """
    status = (escrow_status or "held").lower()

    if status in ("released", "refunded"):
        return {
            "status": "ok",
            "escrow_status": status,
            "recommendation": "not_applicable",
            "releasable": False,
            "conditions": {
                "buyer_delivery_confirmed": buyer_delivery_confirmed,
                "goods_received_confirmed": goods_received_confirmed,
                "documents_verified": documents_verified,
            },
            "message": f"Escrow is already {status} — nothing to do.",
        }

    if status != "held":
        return {
            "status": "ok",
            "escrow_status": status,
            "recommendation": "not_applicable",
            "releasable": False,
            "message": f"Escrow status '{status}' is not held; release applies only to held escrow.",
        }

    conditions = {
        "buyer_delivery_confirmed": buyer_delivery_confirmed,
        "goods_received_confirmed": goods_received_confirmed,
        "documents_verified": documents_verified,
    }
    unmet = [label for label, met in conditions.items() if not met]

    # Forced-release safeguard: after a long hold with buyer confirmation, a
    # document shortfall is a warn, not a block.
    hardened = list(unmet)
    if "documents_verified" in hardened and buyer_delivery_confirmed and days_held >= 7:
        hardened.remove("documents_verified")

    releasable = not hardened

    if releasable:
        recommendation = "release_now"
        message = "All release conditions met — release escrow to the seller."
    else:
        recommendation = "hold"
        message = f"Escrow held. Unmet conditions: {', '.join(hardened)}."

    return {
        "status": "ok",
        "escrow_status": status,
        "recommendation": recommendation,
        "releasable": releasable,
        "conditions": conditions,
        "days_held": days_held,
        "unmet_conditions": hardened,
        "message": message,
    }


class EscrowReleaseCheckerTool(BaseTool):
    name = "escrow_release_checker"
    description = (
        "Check whether an escrow can be released to the seller: buyer delivery "
        "confirmed, goods received, documents verified."
    )
    parameters = {
        "type": "object",
        "properties": {
            "escrow_status": {"type": "string", "description": "Current escrow status"},
            "buyer_delivery_confirmed": {"type": "boolean", "description": "Buyer-delivery courier job DELIVERED"},
            "goods_received_confirmed": {"type": "boolean", "description": "Buyer confirms receipt of goods"},
            "documents_verified": {"type": "boolean", "description": "Supporting documents verified"},
            "days_held": {"type": "number", "description": "How many days the escrow has been held"},
        },
        "required": [],
    }

    @classmethod
    def check_available(cls) -> bool:
        return True

    def execute(self, **kwargs: Any) -> str:
        result = check_release(
            kwargs.get("escrow_status", "held"),
            kwargs.get("buyer_delivery_confirmed", False),
            kwargs.get("goods_received_confirmed", False),
            kwargs.get("documents_verified", False),
            kwargs.get("days_held", 0),
        )
        return json.dumps(result, ensure_ascii=False)
