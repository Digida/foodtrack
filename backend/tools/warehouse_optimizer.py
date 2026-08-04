"""Warehouse Optimizer Tool — recommends a warehouse for aggregated stock.

Scores candidate warehouses by capacity fit, cold-chain capability, distance
from the sourcing region, active status and cost. Deterministic and explainable,
so the AI can justify its recommendation to the buyer.
"""
from __future__ import annotations

import json
import logging
from typing import Any

from agent.base_tool import BaseTool

logger = logging.getLogger(__name__)


def _num(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _distance_km(a: dict | None, b: dict | None) -> float:
    """Approximate haversine distance between two {lat, lng} dicts."""
    import math

    if not a or not b:
        return 0.0
    lat1, lng1 = _num(a.get("lat")), _num(a.get("lng"))
    lat2, lng2 = _num(b.get("lat")), _num(b.get("lng"))
    if not lat1 or not lng1 or not lat2 or not lng2:
        return 0.0
    r = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lng2 - lng1)
    a_ = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlmb / 2) ** 2
    return round(2 * r * math.asin(math.sqrt(a_)), 1)


def recommend_warehouse(
    capacity_required: float,
    unit: str = "kg",
    cold_chain_required: bool = False,
    warehouses: list[dict] | None = None,
    origin: dict | None = None,
    region: str | None = None,
    currency: str = "USD",
    limit: int = 3,
) -> dict:
    """Rank warehouses for an aggregated lot.

    Each warehouse dict may carry: id, name, location, lat, lng, capacity,
    capacity_unit, cold_chain, storage_cost, is_active. Scoring weights:
    40% capacity fit, 30% cold-chain match, 20% distance, 10% cost.
    """
    capacity_required = float(capacity_required or 0)
    if capacity_required <= 0:
        return {"status": "error", "message": "capacity_required must be greater than 0"}
    if not warehouses:
        return {"status": "error", "message": "no warehouses provided to evaluate"}

    scored = []
    for wh in warehouses:
        if not wh:
            continue
        is_active = wh.get("is_active", True)
        if isinstance(is_active, str):
            is_active = is_active.lower() in ("y", "yes", "true", "1")
        if not is_active:
            continue

        capacity = _num(wh.get("capacity"))
        cold_chain = bool(wh.get("cold_chain", False))

        capacity_score = min(1.0, capacity / capacity_required) if capacity else 0.5
        cold_score = 1.0 if cold_chain == cold_chain_required else 0.0
        distance = _distance_km(origin, {"lat": wh.get("lat"), "lng": wh.get("lng")})
        distance_score = max(0.0, 1.0 - distance / 1000.0) if distance else 0.5
        cost = _num(wh.get("storage_cost"))
        cost_score = max(0.0, 1.0 - cost / 10.0) if cost else 0.7

        overall = round(0.40 * capacity_score + 0.30 * cold_score + 0.20 * distance_score + 0.10 * cost_score, 3)

        scored.append({
            "id": wh.get("id"),
            "name": wh.get("name") or wh.get("location") or f"warehouse-{wh.get('id')}",
            "capacity_score": round(capacity_score, 3),
            "cold_chain_match": cold_score == 1.0,
            "distance_km": distance,
            "cost_score": round(cost_score, 3),
            "overall_score": overall,
            "storage_cost": cost,
            "currency": currency,
        })

    scored.sort(key=lambda w: w["overall_score"], reverse=True)
    for rank, wh in enumerate(scored, start=1):
        wh["rank"] = rank

    return {
        "status": "ok",
        "capacity_required": capacity_required,
        "unit": unit,
        "cold_chain_required": cold_chain_required,
        "region": region,
        "currency": currency,
        "recommendations": scored[: max(1, int(limit or 3))],
        "best": scored[0] if scored else None,
    }


class WarehouseOptimizerTool(BaseTool):
    name = "warehouse_optimizer"
    description = (
        "Recommend the best warehouse for aggregated stock by capacity fit, "
        "cold-chain match, distance and storage cost."
    )
    parameters = {
        "type": "object",
        "properties": {
            "capacity_required": {"type": "number", "description": "Volume of aggregated stock to store"},
            "unit": {"type": "string", "description": "Unit of measure (default kg)"},
            "cold_chain_required": {"type": "boolean", "description": "Whether refrigerated storage is required"},
            "warehouses": {
                "type": "array",
                "items": {"type": "object"},
                "description": "Candidate warehouses: [{id, name, lat, lng, capacity, cold_chain, storage_cost, is_active}]",
            },
            "origin": {"type": "object", "description": "Sourcing origin: {lat, lng}"},
            "region": {"type": "string", "description": "Sourcing region (optional)"},
            "currency": {"type": "string", "description": "Currency code (default USD)"},
            "limit": {"type": "integer", "description": "Number of recommendations to return"},
        },
        "required": ["capacity_required", "warehouses"],
    }

    @classmethod
    def check_available(cls) -> bool:
        return True

    def execute(self, **kwargs: Any) -> str:
        result = recommend_warehouse(
            kwargs.get("capacity_required", 0),
            kwargs.get("unit", "kg"),
            kwargs.get("cold_chain_required", False),
            kwargs.get("warehouses"),
            kwargs.get("origin"),
            kwargs.get("region"),
            kwargs.get("currency", "USD"),
            kwargs.get("limit", 3),
        )
        return json.dumps(result, ensure_ascii=False)
