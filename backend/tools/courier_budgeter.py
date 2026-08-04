"""Courier Budgeter Tool — estimates the cost of a courier job.

Estimates the budget for moving aggregated stock from a pickup point to a
warehouse (or directly to the investing buyer). Uses distance, weight and mode
baselines, with regional rate adjustments. Purely deterministic so the buyer
can post a realistic budget before the courier job exists.
"""
from __future__ import annotations

import json
import logging
from typing import Any

from agent.base_tool import BaseTool

logger = logging.getLogger(__name__)

MODE_BASELINES = {
    "pickup_truck": {"base": 25.0, "per_km": 1.20, "per_kg": 0.02},
    "van": {"base": 20.0, "per_km": 0.90, "per_kg": 0.015},
    "motorbike": {"base": 8.0, "per_km": 0.45, "per_kg": 0.05},
    "reefer": {"base": 45.0, "per_km": 1.80, "per_kg": 0.03},
    "air": {"base": 120.0, "per_km": 0.60, "per_kg": 0.80},
    "ocean": {"base": 80.0, "per_km": 0.05, "per_kg": 0.06},
}

REGION_MULTIPLIERS = {
    "east_africa": 1.0,
    "dubai": 1.6,
    "gcc": 1.5,
    "eu": 2.2,
    "global": 1.4,
}


def _num(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def estimate_courier_budget(
    distance_km: float,
    weight_kg: float = 0.0,
    mode: str = "pickup_truck",
    region: str = "east_africa",
    currency: str = "USD",
) -> dict:
    """Estimate a courier job budget from distance, weight and mode baselines."""
    distance_km = _num(distance_km)
    weight_kg = _num(weight_kg)
    mode = (mode or "pickup_truck").lower()

    if mode not in MODE_BASELINES:
        return {
            "status": "error",
            "message": f"Unknown mode '{mode}'. Use {sorted(MODE_BASELINES)}",
        }

    base = MODE_BASELINES[mode]
    multiplier = REGION_MULTIPLIERS.get((region or "").lower(), REGION_MULTIPLIERS["global"])

    distance_cost = base["per_km"] * distance_km
    weight_cost = base["per_kg"] * max(0.0, weight_kg)
    budget = round((base["base"] + distance_cost + weight_cost) * multiplier, 2)
    lower = round(budget * 0.85, 2)
    upper = round(budget * 1.15, 2)

    breakdown = {
        "base": round(base["base"], 2),
        "distance": round(distance_cost, 2),
        "weight": round(weight_cost, 2),
        "region_multiplier": multiplier,
    }

    return {
        "status": "ok",
        "distance_km": distance_km,
        "weight_kg": weight_kg,
        "mode": mode,
        "region": region,
        "currency": currency,
        "estimated_budget": budget,
        "budget_range": {"low": lower, "high": upper, "currency": currency},
        "breakdown": breakdown,
        "note": "Budget is an estimate. Post a courier job and negotiate against the tracking quote.",
    }


class CourierBudgeterTool(BaseTool):
    name = "courier_budgeter"
    description = "Estimate a courier job budget from distance, weight and transport mode."
    parameters = {
        "type": "object",
        "properties": {
            "distance_km": {"type": "number", "description": "Distance from pickup to drop-off in km"},
            "weight_kg": {"type": "number", "description": "Weight of the load in kg"},
            "mode": {
                "type": "string",
                "enum": ["pickup_truck", "van", "motorbike", "reefer", "air", "ocean"],
                "description": "Transport mode",
            },
            "region": {"type": "string", "description": "Region for rate adjustment (east_africa/dubai/gcc/eu)"},
            "currency": {"type": "string", "description": "Currency code (default USD)"},
        },
        "required": ["distance_km"],
    }

    @classmethod
    def check_available(cls) -> bool:
        return True

    def execute(self, **kwargs: Any) -> str:
        result = estimate_courier_budget(
            kwargs.get("distance_km", 0),
            kwargs.get("weight_kg", 0),
            kwargs.get("mode", "pickup_truck"),
            kwargs.get("region", "east_africa"),
            kwargs.get("currency", "USD"),
        )
        return json.dumps(result, ensure_ascii=False)
