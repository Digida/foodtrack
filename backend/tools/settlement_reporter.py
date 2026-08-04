"""Settlement Reporter Tool — builds a settlement status/audit report.

Aggregates settlement records into a summary: totals pending, paid and failed,
per-status counts and a serialisable audit trail for the pipeline trace.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from agent.base_tool import BaseTool

logger = logging.getLogger(__name__)


def _money(value: Any) -> float:
    try:
        return round(float(value), 2)
    except (TypeError, ValueError):
        return 0.0


def settlement_report(settlements: list[dict] | None = None) -> dict:
    """Aggregate settlement records into a status report.

    Each settlement dict: {settlement_number, payee_name, net_amount, currency,
    status, due_date, paid_at}.
    """
    settlements = settlements or []
    totals = {
        "pending": 0.0,
        "paid": 0.0,
        "failed": 0.0,
    }
    by_status: dict[str, int] = {}
    by_currency: dict[str, float] = {}
    due = [s for s in settlements if (s.get("status") or "").lower() in ("pending", "scheduled")]

    for s in settlements:
        status = (s.get("status") or "pending").lower()
        amount = _money(s.get("net_amount") or s.get("amount"))
        currency = s.get("currency") or "USD"
        totals[status] = totals.get(status, 0.0) + amount
        by_status[status] = by_status.get(status, 0) + 1
        by_currency[currency] = by_currency.get(currency, 0.0) + amount

    return {
        "status": "ok",
        "settlement_count": len(settlements),
        "totals": totals,
        "by_status": by_status,
        "by_currency": by_currency,
        "due_count": len(due),
        "due_amount": _money(sum(_money(s.get("net_amount") or s.get("amount")) for s in due)),
        "summary": (
            f"{len(settlements)} settlement(s); {_money(totals['paid'])} paid, "
            f"{_money(totals['pending'])} pending."
        ),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


class SettlementReporterTool(BaseTool):
    name = "settlement_reporter"
    description = "Aggregate settlement records into a status and audit summary report."
    parameters = {
        "type": "object",
        "properties": {
            "settlements": {
                "type": "array",
                "items": {"type": "object"},
                "description": "Settlement records: [{net_amount, currency, status, ...}]",
            }
        },
        "required": [],
    }

    @classmethod
    def check_available(cls) -> bool:
        return True

    def execute(self, **kwargs: Any) -> str:
        result = settlement_report(kwargs.get("settlements"))
        return json.dumps(result, ensure_ascii=False)
