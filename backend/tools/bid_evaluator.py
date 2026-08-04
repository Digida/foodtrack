"""Bid Evaluator Tool — scores and ranks bulking bids against a register target.

Evaluates a single bid or a batch of bids against the register's target price
and target quantity, producing a verdict (accept / counter / reject), a score
and a reason. This is the decision helper for the buyer before accepting bids
on an aggregation register.
"""
from __future__ import annotations

import json
import logging
from typing import Any

from agent.base_tool import BaseTool

logger = logging.getLogger(__name__)

MIN_VIABLE_PRICE_RATIO = 0.5
MAX_REALISTIC_PRICE_RATIO = 2.0
QUALITY_BONUS = 0.05
QUALITY_PENALTY = 0.10


def _money(value: Any) -> float:
    try:
        return round(float(value), 2)
    except (TypeError, ValueError):
        return 0.0


def _normalise_quality(quality_grade: str | None) -> str:
    if not quality_grade:
        return "unrated"
    return quality_grade.strip().lower()


def evaluate_bid(
    unit_price: float,
    target_price: float,
    quantity: float = 0.0,
    target_quantity: float = 0.0,
    quality_grade: str | None = None,
    item_name: str | None = None,
    currency: str = "USD",
) -> dict:
    """Score a single bid relative to the register target.

    Verdicts:
    - accept   — price at or below target, quality in order
    - counter  — within the acceptance window but above target
    - reject   — outside the window, or mis-priced
    """
    unit_price = _money(unit_price)
    target_price = _money(target_price)
    quantity = float(quantity or 0)

    if target_price <= 0:
        return {
            "status": "error",
            "item_name": item_name,
            "message": "target_price must be greater than 0 to evaluate a bid",
        }

    price_ratio = unit_price / target_price
    quality = _normalise_quality(quality_grade)
    quality_note = "unrated" if quality == "unrated" else quality

    score = 1.0
    reasons = []

    if price_ratio <= 1.0:
        score -= (price_ratio - 1.0) * 0.0  # at-or-below target is good
        reasons.append("price at or below target")
    else:
        excess = price_ratio - 1.0
        score -= excess * 1.5
        reasons.append(f"price {excess * 100:.1f}% above target")

    if quality == "grade_a" or quality in ("a", "premium", "organic"):
        score += QUALITY_BONUS
        reasons.append(f"quality grade '{quality}' adds confidence")
    elif quality in ("b", "standard"):
        score -= QUALITY_PENALTY * 0.5
        reasons.append(f"quality grade '{quality}' adds risk")
    elif quality in ("c", "reject"):
        score -= QUALITY_PENALTY * 2.0
        reasons.append(f"quality grade '{quality}' is below specification")

    if quantity > 0 and target_quantity > 0:
        coverage = quantity / target_quantity
        if coverage >= 1.0:
            reasons.append("bid covers the full target quantity")
        elif coverage >= 0.5:
            score -= 0.05
            reasons.append(f"bid covers {coverage * 100:.0f}% of target quantity")
        else:
            score -= 0.15
            reasons.append(f"bid covers only {coverage * 100:.0f}% of target quantity")

    score = max(0.0, min(1.0, round(score, 3)))

    if price_ratio <= 1.0:
        verdict = "accept"
    elif price_ratio <= MAX_REALISTIC_PRICE_RATIO:
        verdict = "counter"
    else:
        verdict = "reject"

    if verdict == "reject":
        reasons.append("price exceeds the realistic acceptance ceiling")

    return {
        "status": "ok",
        "item_name": item_name,
        "unit_price": unit_price,
        "target_price": target_price,
        "currency": currency,
        "price_ratio": round(price_ratio, 3),
        "quality_grade": quality_note,
        "score": score,
        "verdict": verdict,
        "reasons": reasons,
    }


def rank_bids(bids: list[dict], target_price: float, currency: str = "USD") -> dict:
    """Score and rank a batch of bids (each a dict with unit_price, quantity,
    quality_grade, contact_name)."""
    target_price = _money(target_price)
    if target_price <= 0:
        return {"status": "error", "message": "target_price must be greater than 0"}

    scored = []
    for bid in bids:
        result = evaluate_bid(
            unit_price=bid.get("unit_price", 0),
            target_price=target_price,
            quantity=bid.get("quantity", 0),
            quality_grade=bid.get("quality_grade"),
            item_name=bid.get("item_name"),
            currency=currency,
        )
        if result.get("status") == "ok":
            scored.append({
                "id": bid.get("id"),
                "contact_name": bid.get("contact_name"),
                **result,
            })

    scored.sort(key=lambda b: (b["score"], -b["unit_price"]), reverse=True)
    for rank, b in enumerate(scored, start=1):
        b["rank"] = rank

    return {
        "status": "ok",
        "target_price": target_price,
        "currency": currency,
        "evaluated_count": len(scored),
        "ranked_bids": scored,
        "best_bid": scored[0] if scored else None,
    }


class BidEvaluatorTool(BaseTool):
    name = "bid_evaluator"
    description = (
        "Score and rank bulking bids against a register target price: verdicts "
        "accept/counter/reject with an explainable score."
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {"type": "string", "enum": ["evaluate", "rank"], "description": "Action to perform"},
            "unit_price": {"type": "number", "description": "Single bid unit price"},
            "target_price": {"type": "number", "description": "Register target unit price"},
            "quantity": {"type": "number", "description": "Bid quantity"},
            "target_quantity": {"type": "number", "description": "Register target quantity"},
            "quality_grade": {"type": "string", "description": "Bid quality grade (A/B/C/premium/organic)"},
            "item_name": {"type": "string", "description": "Item name"},
            "bids": {
                "type": "array",
                "items": {"type": "object"},
                "description": "Batch of bids for ranking: [{id, contact_name, unit_price, quantity, quality_grade}]",
            },
            "currency": {"type": "string", "description": "Currency code (default USD)"},
        },
        "required": ["action"],
    }

    @classmethod
    def check_available(cls) -> bool:
        return True

    def execute(self, **kwargs: Any) -> str:
        action = kwargs.get("action", "")
        if action == "evaluate":
            result = evaluate_bid(
                kwargs.get("unit_price", 0),
                kwargs.get("target_price", 0),
                kwargs.get("quantity", 0),
                kwargs.get("target_quantity", 0),
                kwargs.get("quality_grade"),
                kwargs.get("item_name"),
                kwargs.get("currency", "USD"),
            )
        elif action == "rank":
            result = rank_bids(
                kwargs.get("bids", []),
                kwargs.get("target_price", 0),
                kwargs.get("currency", "USD"),
            )
        else:
            result = {"status": "error", "message": f"Unknown action: {action}"}
        return json.dumps(result, ensure_ascii=False)
