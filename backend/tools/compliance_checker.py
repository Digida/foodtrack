from __future__ import annotations

import json
import logging
from typing import Any

from agent.base_tool import BaseTool

logger = logging.getLogger(__name__)

DUBAI_REQUIREMENTS = {
    "food": {
        "required_certs": ["dubai_municipality", "halal", "export_health"],
        "labelling": ["arabic_english", "nutrition_facts", "origin_country", "expiry_date", "ingredients"],
        "restrictions": ["pork_derivatives", "non_halal_gelatin", "alcohol_additives"],
    },
    "beverage": {
        "required_certs": ["dubai_municipality", "export_health"],
        "labelling": ["arabic_english", "nutrition_facts", "origin_country", "expiry_date", "ingredients"],
        "restrictions": ["alcohol_over_0.5%"],
    },
    "seafood": {
        "required_certs": ["dubai_municipality", "export_health", "fishing_license", "heavy_metals_test"],
        "labelling": ["arabic_english", "origin_country", "species_name", "catch_date", "expiry_date"],
        "restrictions": ["endangered_species", "below_minimum_size"],
    },
    "meat": {
        "required_certs": ["dubai_municipality", "halal", "veterinary_health", "export_health", "slaughterhouse_approval"],
        "labelling": ["arabic_english", "origin_country", "species", "slaughter_date", "expiry_date"],
        "restrictions": ["non_halal", "pork", "improper_stunning"],
    },
    "produce": {
        "required_certs": ["dubai_municipality", "phytosanitary", "pesticide_residue_test"],
        "labelling": ["arabic_english", "origin_country", "variety", "net_weight"],
        "restrictions": ["banned_pesticides", "gm_varieties"],
    },
    "dairy": {
        "required_certs": ["dubai_municipality", "export_health", "halal", "laboratory_test"],
        "labelling": ["arabic_english", "nutrition_facts", "origin_country", "expiry_date", "storage_temp"],
        "restrictions": ["raw_unpasteurized", "non_halal_rennet"],
    },
}


def check_compliance(
    item_category: str,
    target_market: str,
    current_certs: list[str] | None = None,
    current_labelling: list[str] | None = None,
) -> dict:
    market = target_market.lower()
    category = item_category.lower()

    if market != "dubai" and market != "uae":
        return {
            "status": "ok",
            "market": target_market,
            "message": f"No specific compliance rules for {target_market}",
            "compliant": True,
        }

    rules = DUBAI_REQUIREMENTS.get(category)
    if not rules:
        return {
            "status": "warn",
            "market": target_market,
            "category": item_category,
            "message": f"No compliance rules defined for category '{item_category}'",
            "compliant": False,
        }

    current_certs = current_certs or []
    current_labelling = current_labelling or []

    missing_certs = [c for c in rules["required_certs"] if c not in current_certs]
    missing_labelling = [l for l in rules["labelling"] if l not in current_labelling]
    has_restrictions = any(r in rules.get("restrictions", []) for r in current_certs)

    total_checks = len(rules["required_certs"]) + len(rules["labelling"])
    passed = (len(rules["required_certs"]) - len(missing_certs)) + (len(rules["labelling"]) - len(missing_labelling))
    compliant = len(missing_certs) == 0 and len(missing_labelling) == 0

    return {
        "status": "ok" if compliant else "fail",
        "market": target_market,
        "category": item_category,
        "compliant": compliant,
        "missing_certifications": missing_certs,
        "missing_labelling": missing_labelling,
        "restriction_flags": rules.get("restrictions", []),
        "has_restriction_concerns": has_restrictions,
        "score": round(passed / max(total_checks, 1), 4),
        "summary": (
            f"{'Compliant' if compliant else 'Non-compliant'} for {target_market}: "
            f"{len(missing_certs)} missing certs, {len(missing_labelling)} missing labelling items"
        ),
    }


class ComplianceCheckerTool(BaseTool):
    name = "compliance_checker"
    description = "Check item compliance against Dubai/UAE market regulations"
    parameters = {
        "type": "object",
        "properties": {
            "item_category": {"type": "string", "description": "Item category (food, beverage, seafood, meat, produce, dairy)"},
            "target_market": {"type": "string", "description": "Target market (e.g., Dubai, UAE)"},
            "current_certs": {"type": "array", "items": {"type": "string"}, "description": "List of current certificate types"},
            "current_labelling": {"type": "array", "items": {"type": "string"}, "description": "List of current labelling features"},
        },
        "required": ["item_category", "target_market"],
    }

    @classmethod
    def check_available(cls) -> bool:
        return True

    def execute(self, **kwargs: Any) -> str:
        result = check_compliance(
            kwargs.get("item_category", ""),
            kwargs.get("target_market", ""),
            kwargs.get("current_certs"),
            kwargs.get("current_labelling"),
        )
        return json.dumps(result, ensure_ascii=False)
