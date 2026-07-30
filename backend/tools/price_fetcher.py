from __future__ import annotations

import json
import logging
import re
from typing import Any

import httpx

from agent.base_tool import BaseTool

logger = logging.getLogger(__name__)

PRICE_SOURCES = [
    {"name": "tridge", "url": "https://www.tridge.com/intelligence", "category": "commodity"},
    {"name": "selina_wamucii", "url": "https://www.selinawamucii.com", "category": "produce"},
    {"name": "indexmundi", "url": "https://www.indexmundi.com/commodities", "category": "commodity"},
]


async def fetch_market_price(item_name: str, market: str = "global", currency: str = "USD") -> dict:
    query = f"{item_name} market price {market} {currency}"
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                "https://html.duckduckgo.com/html/",
                params={"q": query},
                headers={"User-Agent": "FoodTrack/1.0"},
            )
            resp.raise_for_status()
            snippets = re.findall(r'class="result__snippet"[^>]*>(.*?)</a>', resp.text, re.DOTALL)
            top_snippets = [s.strip() for s in snippets[:5]] if snippets else []

            return {
                "status": "ok",
                "item": item_name,
                "market": market,
                "currency": currency,
                "query": query,
                "sources": PRICE_SOURCES,
                "snippets": top_snippets,
                "note": "Review snippets for price estimates; use ReportAudit.extract_figures() to parse values",
            }
    except Exception as e:
        return {"status": "error", "item": item_name, "market": market, "message": str(e)}


class PriceFetcherTool(BaseTool):
    name = "price_fetcher"
    description = "Fetch market prices for food items from web sources"
    parameters = {
        "type": "object",
        "properties": {
            "item_name": {"type": "string", "description": "Item name (e.g., 'Organic Avocados')"},
            "market": {"type": "string", "description": "Target market (e.g., 'Dubai', 'global')"},
            "currency": {"type": "string", "description": "Currency code (default USD)"},
        },
        "required": ["item_name"],
    }

    @classmethod
    def check_available(cls) -> bool:
        return True

    def execute(self, **kwargs: Any) -> str:
        import asyncio
        result = asyncio.run(fetch_market_price(
            kwargs.get("item_name", ""),
            kwargs.get("market", "global"),
            kwargs.get("currency", "USD"),
        ))
        return json.dumps(result, ensure_ascii=False)
