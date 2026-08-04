"""Deal Facilitator Tool — helps close a deal on aggregated stock.

Computes the full deal split (total value, escrow requirement, gross settlement,
platform fee, net payout) and runs a readiness checklist (credentials exchanged,
certificate present, warehouse confirmed, courier assigned) before the deal is
closed. Mirrors the service-layer escrow/settlement rules so the AI can propose
a deal that the service layer will accept.
"""
from __future__ import annotations

import json
import logging
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from agent.base_tool import BaseTool

logger = logging.getLogger(__name__)

DEFAULT_PLATFORM_FEE_RATE = Decimal("0.025")
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


def compute_deal_split(
    quantity: float,
    unit_price: float,
    platform_fee_rate: float = 0.025,
    escrow_pct: float | None = None,
    supply_band: str = "abundant",
    currency: str = "USD",
) -> dict:
    """Compute the financial split of a deal on aggregated stock.

    escrow_pct defaults from the supply band (30% abundant, 65% rare) when not
    given explicitly.
    """
    quantity = _dec(quantity)
    unit_price = _dec(unit_price)

    if quantity <= 0 or unit_price < 0:
        return {"status": "error", "message": "quantity must be positive and unit_price non-negative"}

    if escrow_pct is None:
        escrow_pct = ESCROW_PCT_RARE if supply_band == "rare" else ESCROW_PCT_ABUNDANT
    escrow_pct = _dec(escrow_pct)

    total_value = quantity * unit_price
    escrow_amount = total_value * escrow_pct
    gross_settlement = total_value * (Decimal("1") - _dec(platform_fee_rate))
    platform_fee = total_value * _dec(platform_fee_rate)
    net_settlement = gross_settlement

    return {
        "status": "ok",
        "currency": currency,
        "quantity": float(quantity),
        "unit_price": _money(unit_price),
        "total_value": _money(total_value),
        "platform_fee_rate": float(_dec(platform_fee_rate)),
        "platform_fee": _money(platform_fee),
        "gross_settlement": _money(total_value),
        "net_settlement": _money(net_settlement),
        "escrow_percentage": _money(escrow_pct * 100),
        "escrow_amount": _money(escrow_amount),
        "supply_band": supply_band,
    }


def deal_readiness_check(
    credentials_exchanged: bool = False,
    certificate_present: bool = False,
    warehouse_confirmed: bool = False,
    courier_assigned: bool = False,
) -> dict:
    """Run the pre-close readiness checklist for a deal."""
    checks = [
        {"label": "Credentials exchanged (buyer/seller)", "met": credentials_exchanged},
        {"label": "Quality certificate attached to the lot", "met": certificate_present},
        {"label": "Warehouse booking confirmed", "met": warehouse_confirmed},
        {"label": "Courier job assigned", "met": courier_assigned},
    ]
    met_count = sum(1 for c in checks if c["met"])
    ready = met_count == len(checks)
    return {
        "status": "ok",
        "ready": ready,
        "met_count": met_count,
        "total_checks": len(checks),
        "checks": checks,
        "summary": "Deal is ready to close." if ready else f"{met_count}/{len(checks)} readiness checks met.",
        "next_actions": [c["label"] for c in checks if not c["met"]],
    }


class DealFacilitatorTool(BaseTool):
    name = "deal_facilitator"
    description = (
        "Facilitate closing a bulking deal: compute the financial split "
        "(total value, escrow, fees, net payout) and run the pre-close readiness checklist."
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["split", "readiness"],
                "description": "split computes the deal financials; readiness runs the close checklist",
            },
            "quantity": {"type": "number", "description": "Deal quantity"},
            "unit_price": {"type": "number", "description": "Deal unit price"},
            "platform_fee_rate": {"type": "number", "description": "Platform fee rate (default 0.025)"},
            "escrow_pct": {"type": "number", "description": "Escrow percentage override (optional)"},
            "supply_band": {"type": "string", "enum": ["abundant", "rare"], "description": "Item supply band"},
            "currency": {"type": "string", "description": "Currency code (default USD)"},
            "credentials_exchanged": {"type": "boolean", "description": "Credentials exchanged flag"},
            "certificate_present": {"type": "boolean", "description": "Quality certificate present"},
            "warehouse_confirmed": {"type": "boolean", "description": "Warehouse booking confirmed"},
            "courier_assigned": {"type": "boolean", "description": "Courier job assigned"},
        },
        "required": ["action"],
    }

    @classmethod
    def check_available(cls) -> bool:
        return True

    def execute(self, **kwargs: Any) -> str:
        action = kwargs.get("action", "")
        if action == "split":
            result = compute_deal_split(
                kwargs.get("quantity", 0),
                kwargs.get("unit_price", 0),
                kwargs.get("platform_fee_rate", 0.025),
                kwargs.get("escrow_pct"),
                kwargs.get("supply_band", "abundant"),
                kwargs.get("currency", "USD"),
            )
        elif action == "readiness":
            result = deal_readiness_check(
                kwargs.get("credentials_exchanged", False),
                kwargs.get("certificate_present", False),
                kwargs.get("warehouse_confirmed", False),
                kwargs.get("courier_assigned", False),
            )
        else:
            result = {"status": "error", "message": f"Unknown action: {action}"}
        return json.dumps(result, ensure_ascii=False)
