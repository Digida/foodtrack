"""Escrow Reporter Tool — builds an escrow status/audit report.

Aggregates escrow records into a summary: totals held, deposited, released and
refunded, per-status counts and a serialisable audit trail for the pipeline
trace.
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


def escrow_report(escrows: list[dict] | None = None) -> dict:
    """Aggregate escrow records into a status report.

    Each escrow dict: {register_id, supply_band, percentage, amount, currency,
    status, deposited_at, released_at}.
    """
    escrows = escrows or []
    totals = {
        "required": 0.0,
        "deposited": 0.0,
        "held": 0.0,
        "released": 0.0,
        "refunded": 0.0,
    }
    by_status: dict[str, int] = {}
    by_currency: dict[str, float] = {}

    for e in escrows:
        status = (e.get("status") or "required").lower()
        amount = _money(e.get("amount"))
        currency = e.get("currency") or "USD"
        totals[status] = totals.get(status, 0.0) + amount
        by_status[status] = by_status.get(status, 0) + 1
        by_currency[currency] = by_currency.get(currency, 0.0) + amount

    return {
        "status": "ok",
        "escrow_count": len(escrows),
        "totals": totals,
        "by_status": by_status,
        "by_currency": by_currency,
        "summary": (
            f"{len(escrows)} escrow record(s); {_money(totals['released'])} released, "
            f"{_money(totals['held'])} currently held."
        ),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


class EscrowReporterTool(BaseTool):
    name = "escrow_reporter"
    description = "Aggregate escrow records into a status and audit summary report."
    parameters = {
        "type": "object",
        "properties": {
            "escrows": {
                "type": "array",
                "items": {"type": "object"},
                "description": "Escrow records: [{amount, currency, status, ...}]",
            }
        },
        "required": [],
    }

    @classmethod
    def check_available(cls) -> bool:
        return True

    def execute(self, **kwargs: Any) -> str:
        result = escrow_report(kwargs.get("escrows"))
        return json.dumps(result, ensure_ascii=False)
