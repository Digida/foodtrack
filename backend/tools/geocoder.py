from __future__ import annotations

import json
import logging
import math
from typing import Any

import httpx

from agent.base_tool import BaseTool

logger = logging.getLogger(__name__)

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"


async def geocode(address: str) -> dict:
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                NOMINATIM_URL,
                params={"q": address, "format": "json", "limit": 1},
                headers={"User-Agent": "FoodTrack/1.0"},
            )
            resp.raise_for_status()
            data = resp.json()
            if data:
                return {
                    "status": "ok",
                    "address": address,
                    "lat": float(data[0]["lat"]),
                    "lng": float(data[0]["lon"]),
                    "display_name": data[0].get("display_name", ""),
                    "source": "nominatim",
                }
            return {"status": "error", "address": address, "message": "Address not found"}
    except Exception as e:
        return {"status": "error", "address": address, "message": str(e)}


def vincenty_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> dict:
    R = 6371000
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)

    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    meters = R * c

    return {
        "from": {"lat": lat1, "lng": lng1},
        "to": {"lat": lat2, "lng": lng2},
        "meters": round(meters, 2),
        "kilometers": round(meters / 1000, 2),
        "miles": round(meters / 1609.344, 2),
    }


class GeocoderTool(BaseTool):
    name = "geocoder"
    description = "Geocode addresses to lat/lng and calculate distances between coordinates"
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["geocode", "distance"],
                "description": "Action to perform",
            },
            "address": {"type": "string", "description": "Address to geocode"},
            "lat1": {"type": "number", "description": "Origin latitude (for distance)"},
            "lng1": {"type": "number", "description": "Origin longitude (for distance)"},
            "lat2": {"type": "number", "description": "Destination latitude (for distance)"},
            "lng2": {"type": "number", "description": "Destination longitude (for distance)"},
        },
        "required": ["action"],
    }

    @classmethod
    def check_available(cls) -> bool:
        return True

    def execute(self, **kwargs: Any) -> str:
        import asyncio

        action = kwargs.get("action", "")
        if action == "geocode":
            address = kwargs.get("address", "")
            if not address:
                return json.dumps({"status": "error", "message": "address required"})
            result = asyncio.run(geocode(address))
        elif action == "distance":
            result = vincenty_distance(
                kwargs.get("lat1", 0), kwargs.get("lng1", 0),
                kwargs.get("lat2", 0), kwargs.get("lng2", 0),
            )
        else:
            result = {"status": "error", "message": f"Unknown action: {action}"}
        return json.dumps(result, ensure_ascii=False)
