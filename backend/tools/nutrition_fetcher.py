from __future__ import annotations

import json
import logging
from typing import Any

import httpx

from agent.base_tool import BaseTool

logger = logging.getLogger(__name__)

USDA_API_URL = "https://api.nal.usda.gov/fdc/v1/foods/search"
OPENFOODFACTS_API = "https://world.openfoodfacts.org/api/v2"


async def fetch_nutrition(item_name: str, language: str = "en") -> dict:
    results = []

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{OPENFOODFACTS_API}/search",
                params={"search_terms": item_name, "page_size": 1, "lang": language},
                headers={"User-Agent": "FoodTrack/1.0"},
            )
            resp.raise_for_status()
            data = resp.json()
            products = data.get("products", [])
            if products:
                p = products[0]
                nutriments = p.get("nutriments", {})
                results.append({
                    "source": "openfoodfacts",
                    "product_name": p.get("product_name", ""),
                    "barcode": p.get("code", ""),
                    "nutrients": {
                        "energy_kcal": nutriments.get("energy-kcal_100g"),
                        "protein_g": nutriments.get("proteins_100g"),
                        "fat_g": nutriments.get("fat_100g"),
                        "carbohydrates_g": nutriments.get("carbohydrates_100g"),
                        "fiber_g": nutriments.get("fiber_100g"),
                        "sugars_g": nutriments.get("sugars_100g"),
                        "salt_g": nutriments.get("salt_100g"),
                        "saturated_fat_g": nutriments.get("saturated-fat_100g"),
                    },
                    "image_url": p.get("image_url"),
                    "categories": p.get("categories", ""),
                })
    except Exception as e:
        logger.warning(f"OpenFoodFacts lookup failed: {e}")

    if not results:
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(
                    USDA_API_URL,
                    params={"query": item_name, "pageSize": 1, "api_key": "DEMO_KEY"},
                )
                resp.raise_for_status()
                data = resp.json()
                foods = data.get("foods", [])
                if foods:
                    f = foods[0]
                    nutrients = {}
                    for nutrient in f.get("foodNutrients", []):
                        name = nutrient.get("nutrientName", "").lower().replace(" ", "_").replace(",", "")
                        val = nutrient.get("value")
                        unit = nutrient.get("unitName", "")
                        if val is not None:
                            nutrients[name] = {"value": val, "unit": unit}
                    results.append({
                        "source": "usda",
                        "food_name": f.get("description", ""),
                        "fdc_id": f.get("fdcId"),
                        "nutrients": nutrients,
                    })
        except Exception as e:
            logger.warning(f"USDA lookup failed: {e}")

    if not results:
        return {
            "status": "error",
            "item": item_name,
            "message": "No nutritional data found from available sources",
        }

    return {"status": "ok", "item": item_name, "language": language, "results": results}


class NutritionFetcherTool(BaseTool):
    name = "nutrition_fetcher"
    description = "Fetch nutritional data for food items from OpenFoodFacts and USDA databases"
    parameters = {
        "type": "object",
        "properties": {
            "item_name": {"type": "string", "description": "Food item name"},
            "language": {"type": "string", "description": "Language code (default en)"},
        },
        "required": ["item_name"],
    }

    @classmethod
    def check_available(cls) -> bool:
        return True

    def execute(self, **kwargs: Any) -> str:
        import asyncio
        result = asyncio.run(fetch_nutrition(
            kwargs.get("item_name", ""),
            kwargs.get("language", "en"),
        ))
        return json.dumps(result, ensure_ascii=False)
