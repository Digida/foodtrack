"""Settlement Calculator Tool — computes gross/fee/net per seller.

Settlements are what a seller (farmer, cooperative, aggregator) is owed for
accepted bids / closed deals, net of the platform fee. This tool computes the
split for one settlement or a whole batch, mirroring the service-layer fee rule
(default 2.5% platform fee).
"""
from __future__ import annotations

import json
import logging
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from agent.base_tool import BaseTool

logger = logging.getLogger(__name__)

DEFAULT_PLATFORM_FEE_RATE = Decimal("0.025")
HUNDREDTH = Decimal("0.01")


def _dec(value: Any) -> Decimal:
    try:
        return Decimal(str(value))
    except (TypeError, ValueError):
        return Decimal("0")


def _money(value: Decimal) -> float:
    return float(value.quantize(HUNDREDTH, rounding=ROUND_HALF_UP))


def calculate_settlement(
    quantity: float,
    unit_price: float,
    platform_fee_rate: float = 0.025,
    currency: str = "USD",
) -> dict:
    """Compute a single settlement: gross = qty x price, net = gross - fee."""
    quantity = _dec(quantity)
    unit_price = _dec(unit_price)
    fee_rate = _dec(platform_fee_rate)

    if quantity <= 0 or unit_price < 0:
        return {"status": "error", "message": "quantity must be positive and unit_price non-negative"}

    gross = quantity * unit_price
    platform_fee = (gross * fee_rate).quantize(HUNDREDTH, rounding=ROUND_HALF_UP)
    net = (gross - platform_fee).quantize(HUNDREDTH, rounding=ROUND_HALF_UP)

    return {
        "status": "ok",
        "currency": currency,
        "quantity": float(quantity),
        "unit_price": _money(unit_price),
        "gross_amount": _money(gross),
        "platform_fee_rate": float(fee_rate),
        "platform_fee": _money(platform_fee),
        "net_amount": _money(net),
    }


def calculate_settlement_batch(
    settlements: list[dict],
    platform_fee_rate: float = 0.025,
    currency: str = "USD",
) -> dict:
    """Compute settlements for a batch of {quantity, unit_price, payee_name}."""
    results = []
    total_gross = Decimal("0")
    total_fee = Decimal("0")
    total_net = Decimal("0")

    for item in settlements:
        result = calculate_settlement(
            item.get("quantity", 0),
            item.get("unit_price", 0),
            platform_fee_rate,
            currency,
        )
        if result.get("status") == "ok":
            results.append({
                "id": item.get("id"),
                "payee_name": item.get("payee_name"),
                **result,
            })
            total_gross += _dec(result["gross_amount"])
            total_fee += _dec(result["platform_fee"])
            total_net += _dec(result["net_amount"])

    return {
        "status": "ok",
        "currency": currency,
        "settlement_count": len(results),
        "settlements": results,
        "totals": {
            "gross": _money(total_gross),
            "platform_fee": _money(total_fee),
            "net": _money(total_net),
        },
    }


class SettlementCalculatorTool(BaseTool):
    name = "settlement_calculator"
    description = (
        "Compute settlement amounts for sellers: gross = quantity x unit price, "
        "net = gross minus the platform fee (default 2.5%)."
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {"type": "string", "enum": ["single", "batch"], "description": "Action to perform"},
            "quantity": {"type": "number", "description": "Settled quantity"},
            "unit_price": {"type": "number", "description": "Unit price"},
            "platform_fee_rate": {"type": "number", "description": "Platform fee rate (default 0.025)"},
            "settlements": {
                "type": "array",
                "items": {"type": "object"},
                "description": "Batch: [{id, payee_name, quantity, unit_price}]",
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
        if action == "single":
            result = calculate_settlement(
                kwargs.get("quantity", 0),
                kwargs.get("unit_price", 0),
                kwargs.get("platform_fee_rate", 0.025),
                kwargs.get("currency", "USD"),
            )
        elif action == "batch":
            result = calculate_settlement_batch(
                kwargs.get("settlements", []),
                kwargs.get("platform_fee_rate", 0.025),
                kwargs.get("currency", "USD"),
            )
        else:
            result = {"status": "error", "message": f"Unknown action: {action}"}
        return json.dumps(result, ensure_ascii=False)
