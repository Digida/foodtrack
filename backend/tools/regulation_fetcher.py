from __future__ import annotations

import json
import logging
from typing import Any

import httpx

from agent.base_tool import BaseTool

logger = logging.getLogger(__name__)


async def fetch_regulations(country: str, sector: str = "food") -> dict:
    query = f"{country} {sector} import regulations requirements 2026"
    sources = []

    country_lower = country.lower()

    known_regs = {
        "uae": {
            "agencies": ["MOCCAE", "Dubai Municipality", "Emirates Authority for Standardization"],
            "key_requirements": ["Halal certification", "Arabic labelling", "Export health certificate", "Product registration"],
            "references": [
                "https://www.moccae.gov.ae/",
                "https://www.dm.gov.ae/",
                "https://www.esma.gov.ae/",
            ],
        },
        "dubai": {
            "agencies": ["Dubai Municipality - Food Safety Dept", "Dubai Customs", "Dubai Trade"],
            "key_requirements": ["Dubai Municipality registration", "Halal certification", "Arabic + English labelling", "Product listing in Food Import System"],
            "references": [
                "https://www.dm.gov.ae/food-safety/",
                "https://www.dubaicustoms.gov.ae/",
                "https://www.dubaitrade.ae/",
            ],
        },
        "saudi_arabia": {
            "agencies": ["SFDA", "Ministry of Environment, Water and Agriculture"],
            "key_requirements": ["SFDA registration", "Halal certification", "Arabic labelling", "SASO conformity"],
            "references": ["https://www.sfda.gov.sa/"],
        },
        "kenya": {
            "agencies": ["KEBS", "Dairy Board of Kenya", "HCD", "KEPHIS"],
            "key_requirements": ["Export health certificate", "Phytosanitary certificate", "KEBS standardization mark"],
            "references": ["https://www.kebs.org/", "https://www.kephis.org/"],
        },
        "uganda": {
            "agencies": ["UNBS", "MAAIF", "NARO"],
            "key_requirements": ["UNBS certification", "Phytosanitary certificate", "Export health certificate"],
            "references": ["https://www.unbs.go.ug/"],
        },
    }

    for key, info in known_regs.items():
        if key in country_lower:
            sources.append(info)

    if not sources:
        sources.append({
            "agencies": [f"{country.capitalize()} food safety authority"],
            "key_requirements": ["Export health certificate", "Product registration", "Labelling compliance"],
            "references": [],
        })

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                "https://html.duckduckgo.com/html/",
                params={"q": query},
                headers={"User-Agent": "FoodTrack/1.0"},
            )
            resp.raise_for_status()
            import re
            urls = re.findall(r'href="(https?://[^"]+)"', resp.text)[:5]
            if urls:
                sources[0]["references"].extend(urls)
    except Exception as e:
        logger.warning(f"Web search for regulations failed: {e}")

    return {
        "status": "ok",
        "country": country,
        "sector": sector,
        "query": query,
        "regulatory_bodies": sources[0].get("agencies", []) if sources else [],
        "key_requirements": sources[0].get("key_requirements", []) if sources else [],
        "references": sources[0].get("references", []) if sources else [],
        "disclaimer": "This is a summary. Always verify with official sources for current requirements.",
    }


class RegulationFetcherTool(BaseTool):
    name = "regulation_fetcher"
    description = "Fetch import regulations and compliance requirements for target markets"
    parameters = {
        "type": "object",
        "properties": {
            "country": {"type": "string", "description": "Target country or market (e.g., UAE, Dubai, Kenya)"},
            "sector": {"type": "string", "description": "Sector (default 'food')"},
        },
        "required": ["country"],
    }

    @classmethod
    def check_available(cls) -> bool:
        return True

    def execute(self, **kwargs: Any) -> str:
        import asyncio
        result = asyncio.run(fetch_regulations(
            kwargs.get("country", ""),
            kwargs.get("sector", "food"),
        ))
        return json.dumps(result, ensure_ascii=False)
