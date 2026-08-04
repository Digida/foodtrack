"""Escrow Calculator Tool — computes investor escrow requirements.

Investor escrow on a bulking register: the buyer deposits a percentage of the
deal value up front — 30% for abundant items, 65% for rare items. This tool
computes the percentage, the escrow basis (closed deals, else accepted bid
volume, else register target) and the required deposit. Mirrors the
service-layer rule so AI proposals are accepted by the pipeline.
"""
from __future__ import annotations

import json
import logging
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from agent.base_tool import BaseTool

logger = logging.getLogger(__name__)

ESCROW_PCT_ABUNDANT = Decimal("0.30")
ESCROW_PCT_RARE = Decimal("0.65")
HUNDREDTH = Decimal("0.01")


def _dec(value: Any) -> Decimal:
    try:
        return Decimal(str(value))
    except (TypeError, ValueError):
        return Decimal("0")


def _money(value: Decimal) -> float:
    return float(value.quantize(HUNDREDTH, rounding=ROUND_HALF_UP))


def escrow_percentage(supply_band: str | None = None) -> dict:
    """The required up-front deposit percentage for an item."""
    band = (supply_band or "abundant").lower()
    if band not in ("abundant", "rare"):
        return {"status": "error", "message": "supply_band must be 'abundant' or 'rare'"}
    pct = ESCROW_PCT_RARE if band == "rare" else ESCROW_PCT_ABUNDANT
    return {
        "status": "ok",
        "supply_band": band,
        "escrow_percentage": _money(pct * 100),
        "escrow_rate": float(pct),
    }


def escrow_amount(
    supply_band: str | None = None,
    deal_value: float | None = None,
    accepted_bid_value: float | None = None,
    target_price: float | None = None,
    target_quantity: float | None = None,
    currency: str = "USD",
) -> dict:
    """Compute the required escrow amount.

    Basis precedence (matches the service layer): closed-deal value, then
    accepted-bid value, then register target price x target quantity.
    """
    band = (supply_band or "abundant").lower()
    if band not in ("abundant", "rare"):
        return {"status": "error", "message": "supply_band must be 'abundant' or 'rare'"}
    pct = ESCROW_PCT_RARE if band == "rare" else ESCROW_PCT_ABUNDANT

    if deal_value is not None:
        basis = _dec(deal_value)
        basis_source = "deal_value"
    elif accepted_bid_value is not None:
        basis = _dec(accepted_bid_value)
        basis_source = "accepted_bid_value"
    elif target_price is not None and target_quantity is not None:
        basis = _dec(target_price) * _dec(target_quantity)
        basis_source = "target_price_x_quantity"
    else:
        return {
            "status": "error",
            "message": "Provide deal_value, accepted_bid_value, or target_price + target_quantity",
        }

    required = basis * pct
    return {
        "status": "ok",
        "supply_band": band,
        "escrow_percentage": _money(pct * 100),
        "basis_amount": _money(basis),
        "basis_source": basis_source,
        "required_amount": _money(required),
        "currency": currency,
    }


class EscrowCalculatorTool(BaseTool):
    name = "escrow_calculator"
    description = (
        "Compute investor escrow requirements for a bulking register: 30% for "
        "abundant items, 65% for rare items, over deal/bid/target value."
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {"type": "string", "enum": ["percentage", "amount"], "description": "Action to perform"},
            "supply_band": {"type": "string", "enum": ["abundant", "rare"], "description": "Item supply band"},
            "deal_value": {"type": "number", "description": "Closed-deal value (basis)"},
            "accepted_bid_value": {"type": "number", "description": "Accepted-bid volume value (basis)"},
            "target_price": {"type": "number", "description": "Register target price (basis)"},
            "target_quantity": {"type": "number", "description": "Register target quantity (basis)"},
            "currency": {"type": "string", "description": "Currency code (default USD)"},
        },
        "required": ["action"],
    }

    @classmethod
    def check_available(cls) -> bool:
        return True

    def execute(self, **kwargs: Any) -> str:
        action = kwargs.get("action", "")
        if action == "percentage":
            result = escrow_percentage(kwargs.get("supply_band"))
        elif action == "amount":
            result = escrow_amount(
                kwargs.get("supply_band"),
                kwargs.get("deal_value"),
                kwargs.get("accepted_bid_value"),
                kwargs.get("target_price"),
                kwargs.get("target_quantity"),
                kwargs.get("currency", "USD"),
            )
        else:
            result = {"status": "error", "message": f"Unknown action: {action}"}
        return json.dumps(result, ensure_ascii=False)
