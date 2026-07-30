from tools.web_search import web_search
from tools.web_reader import read_url
from tools.regulation_fetcher import fetch_regulations


async def check_dubai_trade_requirements(cargo_details: dict) -> dict:
    hs_code = cargo_details.get("hs_code", "")
    results = web_search(f"Dubai Trade portal customs clearance requirements {hs_code} food", max_results=5)
    return {
        "portal": "Dubai Trade",
        "hs_code": hs_code,
        "requirements_found": results.get("result_count", 0) if isinstance(results, dict) else 0,
        "note": "Dubai Trade integration requires API key registration. Contact Dubai Trade for portal access.",
    }


async def check_moccae_requirements(item_name: str) -> dict:
    results = web_search(f"MOCCAE UAE food import permit {item_name} pre-clearance", max_results=5)
    regs = await fetch_regulations(country="AE", sector="food")
    return {
        "agency": "MOCCAE",
        "item": item_name,
        "regulations_found": regs if isinstance(regs, dict) else {"raw": str(regs)},
        "note": "MOCCAE food import permit can be filed via the UAE Single Window portal.",
    }


async def check_dubai_municipality_requirements(item_name: str) -> dict:
    results = web_search(f"Dubai Municipality food safety product registration {item_name}", max_results=5)
    return {
        "agency": "Dubai Municipality Food Safety",
        "item": item_name,
        "requirements": results.get("results", []) if isinstance(results, dict) else [],
        "note": "Product registration with Dubai Municipality is required for food imports. Inspection booking available through the Food Watch portal.",
    }


async def check_esma_standards(item_name: str) -> dict:
    results = web_search(f"ESMA UAE conformity assessment {item_name} food standards", max_results=5)
    return {
        "agency": "ESMA",
        "item": item_name,
        "standards": results.get("results", []) if isinstance(results, dict) else [],
        "note": "ESMA conformity assessment may be required for specific food categories. Check UAE Standardization framework.",
    }


async def get_comprehensive_compliance(item_name: str, hs_code: str | None = None) -> dict:
    return {
        "item": item_name,
        "checks": {
            "dubai_trade": await check_dubai_trade_requirements({"hs_code": hs_code or "", "item": item_name}),
            "moccae": await check_moccae_requirements(item_name),
            "dubai_municipality": await check_dubai_municipality_requirements(item_name),
            "esma": await check_esma_standards(item_name),
        },
        "disclaimer": "This is an informational lookup. Always verify requirements directly with the relevant government agency.",
    }
