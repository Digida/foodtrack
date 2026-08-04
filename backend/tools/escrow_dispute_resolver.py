"""Escrow Dispute Resolver Tool — recommends how to resolve escrow disputes.

Disputes arise when the buyer claims non-delivery/defective goods and the seller
claims fulfilment. The resolver maps the scenario + evidence level to a
recommended action (release / hold / partial / refund) with a rationale, so the
AI can propose a resolution that a human admin can approve.
"""
from __future__ import annotations

import json
import logging
from typing import Any

from agent.base_tool import BaseTool

logger = logging.getLogger(__name__)

# Evidence level scoring: how much objective evidence each side has.
EVIDENCE_WEIGHTS = {
    "none": 0.0,
    "weak": 0.25,
    "moderate": 0.5,
    "strong": 0.75,
    "documented": 1.0,
}


def _evidence_level(value: str | None) -> str:
    value = (value or "none").lower()
    return value if value in EVIDENCE_WEIGHTS else "none"


def resolve_dispute(
    scenario: str = "non_delivery",
    escrow_status: str = "held",
    buyer_claim: str = "none",
    seller_claim: str = "none",
    buyer_evidence: str = "none",
    seller_evidence: str = "none",
    escrow_amount: float = 0.0,
    currency: str = "USD",
) -> dict:
    """Recommend an escrow resolution action for a dispute."""
    scenario = (scenario or "non_delivery").lower()
    status = (escrow_status or "held").lower()
    buyer_evidence = _evidence_level(buyer_evidence)
    seller_evidence = _evidence_level(seller_evidence)

    buyer_score = EVIDENCE_WEIGHTS[buyer_evidence] + (0.1 if (buyer_claim or "none").lower() != "none" else 0)
    seller_score = EVIDENCE_WEIGHTS[seller_evidence] + (0.1 if (seller_claim or "none").lower() != "none" else 0)

    if status in ("released", "refunded"):
        return {
            "status": "ok",
            "scenario": scenario,
            "escrow_status": status,
            "recommendation": "no_action",
            "message": f"Escrow already {status}; dispute is moot.",
            "escrow_amount": escrow_amount,
            "currency": currency,
        }

    # Decisive evidence tips the outcome.
    if seller_evidence in ("strong", "documented") and buyer_evidence == "none":
        action, reason = "release", "seller has documented fulfilment; buyer presented no evidence."
    elif buyer_evidence in ("strong", "documented") and seller_evidence == "none":
        action, reason = "refund", "buyer has documented non-receipt; seller presented no evidence."
    elif buyer_evidence == seller_evidence:
        if buyer_score > seller_score:
            action, reason = "partial", "buyer evidence outweighs seller; recommend partial release to the seller."
        elif seller_score > buyer_score:
            action, reason = "partial", "seller evidence outweighs buyer; recommend partial refund to the buyer."
        else:
            action, reason = "hold", "evidence is balanced; hold escrow pending further documentation."
    elif buyer_score > seller_score:
        action, reason = "partial", "buyer's case is stronger; recommend partial refund with remainder released on delivery proof."
    else:
        action, reason = "hold", "seller's case is stronger but not conclusive; hold for admin review."

    partial_pct = 0.5 if action == "partial" else 1.0
    action_amount = round(escrow_amount * partial_pct, 2) if action in ("release", "partial") else 0.0

    return {
        "status": "ok",
        "scenario": scenario,
        "escrow_status": status,
        "buyer_evidence": buyer_evidence,
        "seller_evidence": seller_evidence,
        "recommendation": action,
        "action_amount": action_amount,
        "currency": currency,
        "rationale": reason,
        "note": "Final resolution requires admin approval — this is a decision aid, not an execution.",
    }


class EscrowDisputeResolverTool(BaseTool):
    name = "escrow_dispute_resolver"
    description = (
        "Recommend an escrow dispute resolution (release/hold/partial/refund) "
        "based on buyer and seller evidence."
    )
    parameters = {
        "type": "object",
        "properties": {
            "scenario": {"type": "string", "description": "Dispute scenario (non_delivery/defective/other)"},
            "escrow_status": {"type": "string", "description": "Current escrow status"},
            "buyer_claim": {"type": "string", "description": "Buyer's claim summary"},
            "seller_claim": {"type": "string", "description": "Seller's claim summary"},
            "buyer_evidence": {
                "type": "string",
                "enum": ["none", "weak", "moderate", "strong", "documented"],
                "description": "Buyer evidence level",
            },
            "seller_evidence": {
                "type": "string",
                "enum": ["none", "weak", "moderate", "strong", "documented"],
                "description": "Seller evidence level",
            },
            "escrow_amount": {"type": "number", "description": "Amount under escrow"},
            "currency": {"type": "string", "description": "Currency code (default USD)"},
        },
        "required": [],
    }

    @classmethod
    def check_available(cls) -> bool:
        return True

    def execute(self, **kwargs: Any) -> str:
        result = resolve_dispute(
            kwargs.get("scenario", "non_delivery"),
            kwargs.get("escrow_status", "held"),
            kwargs.get("buyer_claim", "none"),
            kwargs.get("seller_claim", "none"),
            kwargs.get("buyer_evidence", "none"),
            kwargs.get("seller_evidence", "none"),
            kwargs.get("escrow_amount", 0),
            kwargs.get("currency", "USD"),
        )
        return json.dumps(result, ensure_ascii=False)
