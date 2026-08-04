"""Settlement Aggregator Tool — groups settlements by payee.

Aggregates settlement records by payee (farmer/cooperative/aggregator) so the
AI can report "what each seller is owed". Deduplicates payee rows that reference
the same payee identifier and guards against same-name collapse by preferring
the explicit payee_id when present.
"""
from __future__ import annotations

import json
import logging
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from agent.base_tool import BaseTool

logger = logging.getLogger(__name__)

HUNDREDTH = Decimal("0.01")


def _dec(value: Any) -> Decimal:
    if value is None:
        return Decimal("0")
    try:
        return Decimal(str(value))
    except (TypeError, ValueError):
        return Decimal("0")


def _money(value: Decimal) -> float:
    try:
        value = Decimal(str(value))
    except (TypeError, ValueError):
        return 0.0
    return float(value.quantize(HUNDREDTH, rounding=ROUND_HALF_UP))


def aggregate_settlements(settlements: list[dict] | None = None) -> dict:
    """Aggregate settlements by payee.

    Each settlement dict: {payee_id, payee_name, gross_amount, platform_fee,
    net_amount, currency, status}. Grouping key prefers payee_id; falls back to
    payee_name.
    """
    settlements = settlements or []
    groups: dict[str, dict] = {}

    for s in settlements:
        payee_id = s.get("payee_id")
        payee_name = s.get("payee_name") or (f"payee-{payee_id}" if payee_id else "Aggregated seller")
        key = f"id:{payee_id}" if payee_id is not None else f"name:{payee_name}"

        group = groups.setdefault(key, {
            "payee_id": payee_id,
            "payee_name": payee_name,
            "settlement_count": 0,
            "gross_amount": Decimal("0"),
            "platform_fee": Decimal("0"),
            "net_amount": Decimal("0"),
            "currency": s.get("currency") or "USD",
            "statuses": {},
        })
        group["settlement_count"] += 1
        group["gross_amount"] += _dec(s.get("gross_amount"))
        group["platform_fee"] += _dec(s.get("platform_fee"))
        group["net_amount"] += _dec(s.get("net_amount"))
        status = (s.get("status") or "pending").lower()
        group["statuses"][status] = group["statuses"].get(status, 0) + 1

    output = []
    for group in groups.values():
        output.append({
            "payee_id": group["payee_id"],
            "payee_name": group["payee_name"],
            "settlement_count": group["settlement_count"],
            "gross_amount": _money(group["gross_amount"]),
            "platform_fee": _money(group["platform_fee"]),
            "net_amount": _money(group["net_amount"]),
            "currency": group["currency"],
            "statuses": group["statuses"],
        })

    output.sort(key=lambda g: g["net_amount"], reverse=True)
    total_net = sum(_dec(g["net_amount"]) for g in output)

    return {
        "status": "ok",
        "payee_count": len(output),
        "total_net_owed": _money(total_net),
        "payees": output,
    }


class SettlementAggregatorTool(BaseTool):
    name = "settlement_aggregator"
    description = (
        "Aggregate settlement records by payee to report what each seller is owed "
        "(gross, platform fee, net)."
    )
    parameters = {
        "type": "object",
        "properties": {
            "settlements": {
                "type": "array",
                "items": {"type": "object"},
                "description": "Settlements: [{payee_id, payee_name, gross_amount, platform_fee, net_amount, currency, status}]",
            }
        },
        "required": ["settlements"],
    }

    @classmethod
    def check_available(cls) -> bool:
        return True

    def execute(self, **kwargs: Any) -> str:
        result = aggregate_settlements(kwargs.get("settlements"))
        return json.dumps(result, ensure_ascii=False)
