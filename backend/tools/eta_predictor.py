from __future__ import annotations

import json
import logging
import statistics
from datetime import datetime, timedelta, timezone
from typing import Any

from agent.base_tool import BaseTool

logger = logging.getLogger(__name__)


def predict_eta(
    origin: str,
    destination: str,
    mode: str = "ocean",
    historical_transit_days: list[float] | None = None,
    distance_km: float | None = None,
) -> dict:
    mode_speeds = {
        "ocean": {"km_per_day": 800, "base_days": 3},
        "air": {"km_per_day": 8000, "base_days": 1},
        "truck": {"km_per_day": 600, "base_days": 1},
        "rail": {"km_per_day": 500, "base_days": 2},
        "courier": {"km_per_day": 2000, "base_days": 0.5},
        "multimodal": {"km_per_day": 400, "base_days": 5},
    }

    mode_info = mode_speeds.get(mode, mode_speeds["ocean"])
    predictions: dict[str, Any] = {
        "origin": origin,
        "destination": destination,
        "mode": mode,
        "distance_km": distance_km,
    }

    if historical_transit_days and len(historical_transit_days) >= 1:
        n = len(historical_transit_days)
        mean_days = statistics.mean(historical_transit_days)
        median_days = statistics.median(historical_transit_days) if n >= 3 else mean_days
        std_dev = statistics.stdev(historical_transit_days) if n >= 2 else 0
        min_days = min(historical_transit_days)
        max_days = max(historical_transit_days)

        reliability = max(0, min(1, 1.0 - (std_dev / max(mean_days, 0.1))))
        predictions.update({
            "method": "historical",
            "sample_size": n,
            "mean_days": round(mean_days, 2),
            "median_days": round(median_days, 2),
            "std_dev_days": round(std_dev, 2),
            "min_days": min_days,
            "max_days": max_days,
            "predicted_days": round(mean_days, 2),
            "pessimistic_days": round(mean_days + 2 * std_dev, 2),
            "optimistic_days": round(max(mean_days - std_dev, min_days), 2),
            "reliability": round(reliability, 4),
        })
    elif distance_km:
        estimated_days = (distance_km / mode_info["km_per_day"]) + mode_info["base_days"]
        predictions.update({
            "method": "distance_based",
            "predicted_days": round(estimated_days, 2),
            "reliability": 0.5,
            "note": "Based on distance and mode averages; no historical data",
        })
    else:
        base = mode_info["base_days"]
        predictions.update({
            "method": "mode_based",
            "predicted_days": base,
            "reliability": 0.3,
            "note": "Based on mode baseline only; provide distance or historical data for better accuracy",
        })

    now = datetime.now(timezone.utc)
    est_days = predictions.get("predicted_days", 0)
    predictions["estimated_arrival"] = (now + timedelta(days=est_days)).isoformat()
    predictions["estimated_departure"] = now.isoformat()

    return predictions


class EtaPredictorTool(BaseTool):
    name = "eta_predictor"
    description = "Predict estimated time of arrival using historical data, distance, or mode baselines"
    parameters = {
        "type": "object",
        "properties": {
            "origin": {"type": "string", "description": "Origin location"},
            "destination": {"type": "string", "description": "Destination location"},
            "mode": {
                "type": "string",
                "enum": ["ocean", "air", "truck", "rail", "courier", "multimodal"],
                "description": "Transport mode",
            },
            "historical_transit_days": {
                "type": "array", "items": {"type": "number"},
                "description": "List of historical transit times in days",
            },
            "distance_km": {"type": "number", "description": "Distance in kilometers"},
        },
        "required": ["origin", "destination"],
    }

    @classmethod
    def check_available(cls) -> bool:
        return True

    def execute(self, **kwargs: Any) -> str:
        result = predict_eta(
            kwargs.get("origin", ""),
            kwargs.get("destination", ""),
            kwargs.get("mode", "ocean"),
            kwargs.get("historical_transit_days"),
            kwargs.get("distance_km"),
        )
        return json.dumps(result, ensure_ascii=False)
