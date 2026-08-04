"""Bulking Planner Tool — plans a buyer aggregation campaign.

Given an item, a target volume and a target price, the planner computes a
feasibility assessment, a recommended sourcing strategy and the investor-escrow
basis the register will carry. This is the planning front-end of the Commerce
& Bulking Pipeline: it decides how the item gets aggregated before any contact
or bid is created.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from agent.base_tool import BaseTool

logger = logging.getLogger(__name__)

# Conservative per-mode aggregation overhead factors (fractional mark-up on top
# of the target unit price needed to make sourcing viable at that quantity).
SOURCE_MODE_OVERHEAD = {
    "self": 0.00,
    "cooperative": 0.03,
    "aggregator_network": 0.06,
    "marketplace": 0.09,
}

SOURCE_MODE_LABELS = {
    "self": "Direct sourcing from the buyer's own network",
    "cooperative": "A cooperative supplies through its member users",
    "aggregator_network": "Multiple aggregators collate farmer surplus",
    "marketplace": "Open marketplace listings from vetted traders",
}

# Minimum plausible bid unit price is half the target (a bid well under this is
# either mis-priced or a different commodity — flagged for manual review).
MIN_VIABLE_PRICE_RATIO = 0.5
MAX_REALISTIC_PRICE_RATIO = 2.0


def _money(value: Any) -> float:
    try:
        return round(float(value), 2)
    except (TypeError, ValueError):
        return 0.0


def plan_register(
    item_name: str,
    target_quantity: float,
    unit: str = "kg",
    target_price: float = 0.0,
    currency: str = "USD",
    region: str | None = None,
    sourcing_mode: str = "self",
    supply_band: str | None = None,
) -> dict:
    """Produce a bulking campaign plan for a register.

    Returns feasibility flags, a recommended sourcing strategy, expected bid
    spread and the escrow basis amount the investor will be asked to deposit.
    """
    target_quantity = float(target_quantity or 0)
    target_price = _money(target_price)

    if target_quantity <= 0:
        return {
            "status": "error",
            "item_name": item_name,
            "message": "target_quantity must be greater than 0",
        }

    mode = (sourcing_mode or "self").lower()
    if mode not in SOURCE_MODE_OVERHEAD:
        return {
            "status": "error",
            "item_name": item_name,
            "message": f"Unknown sourcing_mode '{mode}'. Use {sorted(SOURCE_MODE_OVERHEAD)}",
        }

    # Feasibility: an item with a real target price is always actionable; the
    # risk tier is a function of volume relative to a notional single-farm lot.
    notional_lot = 1000.0  # kg per farmer/cooperative member
    source_count = max(1, int(target_quantity / notional_lot) + 1)
    if target_quantity <= notional_lot * 0.25:
        risk_tier = "low"
    elif target_quantity <= notional_lot * 3:
        risk_tier = "medium"
    else:
        risk_tier = "high"

    overhead = SOURCE_MODE_OVERHEAD[mode]
    effective_price = _money(target_price * (1 + overhead)) if target_price else 0.0
    effective_basis = _money(target_price * target_quantity) if target_price else 0.0
    bid_floor = _money(target_price * MIN_VIABLE_PRICE_RATIO) if target_price else 0.0
    bid_ceiling = _money(target_price * MAX_REALISTIC_PRICE_RATIO) if target_price else 0.0

    # Investor escrow basis: closed-deal value when known, else target value.
    escrow_pct = 0.30 if supply_band != "rare" else 0.65
    escrow_basis = _money(effective_basis)
    escrow_required = _money(escrow_basis * escrow_pct)

    plan = {
        "status": "ok",
        "item_name": item_name,
        "region": region,
        "target_quantity": target_quantity,
        "unit": unit,
        "target_price": target_price,
        "currency": currency,
        "sourcing_mode": mode,
        "sourcing_strategy": SOURCE_MODE_LABELS[mode],
        "estimated_source_count": source_count,
        "effective_price_after_overhead": effective_price,
        "risk_tier": risk_tier,
        "feasible": True,
        "bid_acceptance_window": {"floor": bid_floor, "ceiling": bid_ceiling, "currency": currency},
        "escrow_percentage": escrow_pct,
        "escrow_basis": escrow_basis,
        "escrow_required": escrow_required,
        "recommendations": [
            "Register a warehouse booking for the aggregated lot before closing deals.",
            f"Source from at least {source_count} separate contacts to de-risk supply.",
            "Accept only bids inside the bid acceptance window to protect the target margin.",
        ],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    if not target_price:
        plan["feasible"] = False
        plan["recommendations"].append("A target price is required before bids can be evaluated.")
    return plan


class BulkingPlannerTool(BaseTool):
    name = "bulking_planner"
    description = (
        "Plan a bulking register campaign: feasibility, sourcing strategy, expected "
        "bid window and investor escrow basis for aggregating a food item."
    )
    parameters = {
        "type": "object",
        "properties": {
            "item_name": {"type": "string", "description": "The food item being aggregated"},
            "target_quantity": {"type": "number", "description": "Target volume to aggregate"},
            "unit": {"type": "string", "description": "Unit of measure (default kg)"},
            "target_price": {"type": "number", "description": "Target unit price"},
            "currency": {"type": "string", "description": "Currency code (default USD)"},
            "region": {"type": "string", "description": "Sourcing region (optional)"},
            "sourcing_mode": {
                "type": "string",
                "enum": ["self", "cooperative", "aggregator_network", "marketplace"],
                "description": "Sourcing strategy",
            },
            "supply_band": {"type": "string", "enum": ["abundant", "rare"], "description": "Item supply band"},
        },
        "required": ["item_name", "target_quantity"],
    }

    @classmethod
    def check_available(cls) -> bool:
        return True

    def execute(self, **kwargs: Any) -> str:
        result = plan_register(
            kwargs.get("item_name", ""),
            kwargs.get("target_quantity", 0),
            kwargs.get("unit", "kg"),
            kwargs.get("target_price", 0),
            kwargs.get("currency", "USD"),
            kwargs.get("region"),
            kwargs.get("sourcing_mode", "self"),
            kwargs.get("supply_band"),
        )
        return json.dumps(result, ensure_ascii=False)
