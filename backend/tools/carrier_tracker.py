from __future__ import annotations

import json
import logging
import re
from typing import Any

import httpx

from agent.base_tool import BaseTool

logger = logging.getLogger(__name__)

CARRIER_PATTERNS: dict[str, dict] = {
    "dhl": {"regex": r"\b\d{10}\b", "url": "https://www.dhl.com/shipmentTracking"},
    "fedex": {"regex": r"\b\d{12,15}\b", "url": "https://www.fedex.com/fedextrack"},
    "ups": {"regex": r"\b1Z[a-zA-Z0-9]{16}\b", "url": "https://www.ups.com/track"},
    "aramex": {"regex": r"\b\d{10,12}\b", "url": "https://www.aramex.com/track"},
    "maersk": {"regex": r"\b\d{10}\b", "url": "https://www.maersk.com/tracking"},
    "cma_cgm": {"regex": r"\b[A-Z]{4}\d{7}\b", "url": "https://www.cma-cgm.com/tracking"},
    "msc": {"regex": r"\b[A-Z]{3}\d{7,9}\b", "url": "https://www.msc.com/track"},
}


def detect_carrier(tracking_number: str) -> list[str]:
    detected = []
    for carrier, config in CARRIER_PATTERNS.items():
        if re.match(config["regex"], tracking_number.strip()):
            detected.append(carrier)
    return detected


async def track_shipment(tracking_number: str, carrier: str | None = None) -> dict:
    if carrier and carrier not in CARRIER_PATTERNS:
        return {"status": "error", "tracking_number": tracking_number, "message": f"Unknown carrier: {carrier}"}

    if not carrier:
        detected = detect_carrier(tracking_number)
        if not detected:
            return {"status": "error", "tracking_number": tracking_number, "message": "Could not detect carrier from tracking number"}
        carrier = detected[0]

    info = CARRIER_PATTERNS[carrier]
    return {
        "status": "ok",
        "tracking_number": tracking_number,
        "carrier": carrier,
        "tracking_url": f"{info['url']}?id={tracking_number}",
        "message": f"Tracking number format matches {carrier}. Use the tracking URL for live status.",
        "carrier_detected": detect_carrier(tracking_number),
    }


async def track_batch(tracking_numbers: list[str]) -> dict:
    results = []
    for tn in tracking_numbers:
        result = await track_shipment(tn)
        results.append(result)
    return {"status": "ok", "count": len(results), "results": results}


class CarrierTrackerTool(BaseTool):
    name = "carrier_tracker"
    description = "Detect carrier from tracking numbers and generate tracking URLs"
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["detect", "track", "track_batch"],
                "description": "Action to perform",
            },
            "tracking_number": {"type": "string", "description": "Single tracking number"},
            "tracking_numbers": {"type": "array", "items": {"type": "string"}, "description": "Multiple tracking numbers"},
            "carrier": {"type": "string", "description": "Carrier name (optional, auto-detected if omitted)"},
        },
        "required": ["action"],
    }

    @classmethod
    def check_available(cls) -> bool:
        return True

    def execute(self, **kwargs: Any) -> str:
        import asyncio

        action = kwargs.get("action", "")
        if action == "detect":
            tn = kwargs.get("tracking_number", "")
            result = {"tracking_number": tn, "detected_carriers": detect_carrier(tn)}
        elif action == "track":
            result = asyncio.run(track_shipment(
                kwargs.get("tracking_number", ""),
                kwargs.get("carrier"),
            ))
        elif action == "track_batch":
            result = asyncio.run(track_batch(kwargs.get("tracking_numbers", [])))
        else:
            result = {"status": "error", "message": f"Unknown action: {action}"}
        return json.dumps(result, ensure_ascii=False)
