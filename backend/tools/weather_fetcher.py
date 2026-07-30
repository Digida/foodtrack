from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

import httpx

from agent.base_tool import BaseTool

logger = logging.getLogger(__name__)

OPENMETEO_URL = "https://api.open-meteo.com/v1/forecast"
HISTORICAL_URL = "https://archive-api.open-meteo.com/v1/archive"


async def fetch_weather(
    lat: float,
    lng: float,
    forecast_days: int = 7,
    past_days: int = 0,
    include_marine: bool = False,
) -> dict:
    params = {
        "latitude": lat,
        "longitude": lng,
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,wind_speed_10m_max,weather_code",
        "timezone": "auto",
        "forecast_days": max(1, min(forecast_days, 16)),
    }
    if past_days > 0:
        params["past_days"] = min(past_days, 92)
        url = HISTORICAL_URL
    else:
        url = OPENMETEO_URL

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

            daily = data.get("daily", {})
            days = []
            dates = daily.get("time", [])
            for i in range(len(dates)):
                days.append({
                    "date": dates[i],
                    "temp_max_c": daily.get("temperature_2m_max", [None])[i],
                    "temp_min_c": daily.get("temperature_2m_min", [None])[i],
                    "precipitation_mm": daily.get("precipitation_sum", [None])[i],
                    "wind_max_kmh": daily.get("wind_speed_10m_max", [None])[i],
                    "weather_code": daily.get("weather_code", [None])[i],
                })

            return {
                "status": "ok",
                "source": "open-meteo",
                "lat": lat,
                "lng": lng,
                "days": days,
                "day_count": len(days),
                "summary": {
                    "avg_temp_max": round(sum(d["temp_max_c"] for d in days if d["temp_max_c"] is not None) / max(len([d for d in days if d["temp_max_c"] is not None]), 1), 1),
                    "total_precipitation_mm": round(sum(d["precipitation_mm"] for d in days if d["precipitation_mm"] is not None), 1),
                },
            }
    except Exception as e:
        return {"status": "error", "lat": lat, "lng": lng, "message": str(e)}


class WeatherFetcherTool(BaseTool):
    name = "weather_fetcher"
    description = "Fetch weather forecasts and historical data for supply chain route planning"
    parameters = {
        "type": "object",
        "properties": {
            "lat": {"type": "number", "description": "Latitude"},
            "lng": {"type": "number", "description": "Longitude"},
            "forecast_days": {"type": "integer", "description": "Days to forecast (max 16)"},
            "past_days": {"type": "integer", "description": "Historical days to include (max 92)"},
        },
        "required": ["lat", "lng"],
    }

    @classmethod
    def check_available(cls) -> bool:
        return True

    def execute(self, **kwargs: Any) -> str:
        import asyncio
        result = asyncio.run(fetch_weather(
            kwargs.get("lat", 0),
            kwargs.get("lng", 0),
            kwargs.get("forecast_days", 7),
            kwargs.get("past_days", 0),
        ))
        return json.dumps(result, ensure_ascii=False)
