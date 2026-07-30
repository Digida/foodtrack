from __future__ import annotations

import json
import logging
import re
from typing import Any

from agent.base_tool import BaseTool

logger = logging.getLogger(__name__)


EAN13_WEIGHTS = [1, 3, 1, 3, 1, 3, 1, 3, 1, 3, 1, 3]
UPC_PREFIXES = {"0", "1", "2", "3", "4", "5", "6", "7", "8", "9"}


def validate_ean13(barcode: str) -> dict:
    barcode = barcode.strip()
    if not re.match(r"^\d{13}$", barcode):
        return {
            "status": "invalid", "format": "ean13",
            "barcode": barcode,
            "message": "EAN-13 must be exactly 13 digits",
        }

    checksum = sum(int(barcode[i]) * EAN13_WEIGHTS[i] for i in range(12))
    expected_check = (10 - (checksum % 10)) % 10
    actual_check = int(barcode[12])
    valid = expected_check == actual_check

    country_prefix = int(barcode[:3])
    gs1_prefixes = {
        "0": "US/CA", "1": "US/CA", "2": "US/CA", "30": "FR",
        "31": "FR", "32": "FR", "33": "FR", "34": "FR", "35": "FR",
        "36": "FR", "37": "FR", "40": "DE", "41": "DE", "42": "DE",
        "43": "DE", "44": "DE", "45": "DE", "46": "DE", "47": "DE",
        "48": "DE", "49": "DE", "50": "UK", "51": "UK", "52": "UK",
        "53": "UK", "54": "UK", "55": "UK", "56": "UK", "57": "UK",
        "58": "UK", "59": "UK", "60": "UK", "61": "UK", "62": "UK",
        "63": "UK", "64": "UK", "65": "UK", "66": "UK", "67": "UK",
        "68": "UK", "69": "UK", "70": "NO", "73": "SE", "74": "SE",
        "75": "SE", "76": "SE", "77": "SE", "78": "SE", "79": "SE",
        "80": "IT", "81": "IT", "82": "IT", "83": "IT", "84": "IT",
        "85": "IT", "86": "IT", "87": "IT", "88": "IT", "89": "IT",
        "90": "AT", "91": "AT", "93": "AU", "94": "NZ", "955": "MY",
        "958": "HK", "978": "BOOK", "979": "BOOK", "977": "ISSN",
    }

    origin = "Unknown"
    for prefix, country in sorted(gs1_prefixes.items(), key=lambda x: -len(x[0])):
        if barcode.startswith(prefix):
            origin = country
            break

    return {
        "status": "valid" if valid else "invalid",
        "format": "ean13",
        "barcode": barcode,
        "valid_checksum": valid,
        "gs1_prefix": origin,
        "country_prefix": country_prefix,
    }


def generate_ean13(base: str = "") -> dict:
    if not base:
        import random
        base = f"{random.randint(100, 999)}" + "".join(str(random.randint(0, 9)) for _ in range(9))
    base = re.sub(r"\D", "", base)[:12].ljust(12, "0")

    checksum = sum(int(base[i]) * EAN13_WEIGHTS[i] for i in range(12))
    check_digit = (10 - (checksum % 10)) % 10
    barcode = f"{base}{check_digit}"

    return {
        "status": "ok",
        "format": "ean13",
        "barcode": barcode,
    }


class BarcodeTool(BaseTool):
    name = "barcode_tool"
    description = "Generate and validate EAN-13 barcodes for items"
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["validate", "generate"],
                "description": "Action to perform",
            },
            "barcode": {"type": "string", "description": "Barcode string (for validate)"},
            "base": {"type": "string", "description": "First 12 digits for generation (optional, random if omitted)"},
        },
        "required": ["action"],
    }

    @classmethod
    def check_available(cls) -> bool:
        return True

    def execute(self, **kwargs: Any) -> str:
        action = kwargs.get("action", "")
        if action == "validate":
            result = validate_ean13(kwargs.get("barcode", ""))
        elif action == "generate":
            result = generate_ean13(kwargs.get("base", ""))
        else:
            result = {"status": "error", "message": f"Unknown action: {action}"}
        return json.dumps(result, ensure_ascii=False)
