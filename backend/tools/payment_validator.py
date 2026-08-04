"""Payment Validator Tool — validates payment references and provider formats.

The pipeline supports Stripe, MPesa, Airtel Money, MTN MoMo, Visa, Mastercard,
bank transfer and cash. This tool validates a provider reference format and
returns a simulated provider status so the AI can confirm a payment before the
service layer's confirm_payment flips it to SUCCEEDED.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any

from agent.base_tool import BaseTool

logger = logging.getLogger(__name__)

# Reference format rules per provider.
PROVIDER_PATTERNS: dict[str, dict] = {
    "stripe": {"regex": r"^(pi|ch|py)_[A-Za-z0-9]{16,}$", "label": "PaymentIntent / Charge / Payment ID"},
    "mpesa": {"regex": r"^(STK|PGW|UAG|SAF|TXC)[A-Z0-9]{6,}$", "label": "M-Pesa transaction reference"},
    "airtel_money": {"regex": r"^[A-Z0-9]{8,20}$", "label": "Airtel Money transaction ID"},
    "mtn_momo": {"regex": r"^(MM|MTN)[A-Z0-9]{6,}$", "label": "MTN MoMo transaction ID"},
    "visa": {"regex": r"^[A-Z0-9]{6,}$", "label": "Visa auth/transaction code"},
    "mastercard": {"regex": r"^[A-Z0-9]{6,}$", "label": "Mastercard auth/transaction code"},
    "bank_transfer": {"regex": r"^[A-Za-z0-9-]{6,}$", "label": "Bank transfer reference"},
    "cash": {"regex": r".+", "label": "Cash receipt reference"},
}


def validate_payment_reference(method: str, reference: str, amount: float = 0.0, currency: str = "USD") -> dict:
    """Validate a provider reference format and report a simulated status."""
    method = (method or "").lower().replace(" ", "_")
    reference = (reference or "").strip()

    if method not in PROVIDER_PATTERNS:
        return {"status": "error", "message": f"Unsupported payment method '{method}'"}

    pattern = PROVIDER_PATTERNS[method]
    matches = bool(re.match(pattern["regex"], reference))

    # Simulated provider status: format-valid references are "confirmed"; we do
    # not hit live provider APIs from the AI layer.
    if matches:
        provider_status = "confirmed"
        verdict = "ok"
    else:
        provider_status = "invalid_format"
        verdict = "invalid"

    return {
        "status": verdict,
        "method": method,
        "reference": reference,
        "reference_format": pattern["label"],
        "provider_status": provider_status,
        "amount": round(float(amount or 0), 2),
        "currency": currency or "USD",
        "message": (
            "Reference format accepted; awaiting service-layer confirmation."
            if matches else "Reference does not match the expected provider format."
        ),
    }


class PaymentValidatorTool(BaseTool):
    name = "payment_validator"
    description = (
        "Validate payment references for supported providers (Stripe, MPesa, "
        "Airtel Money, MTN MoMo, cards, bank, cash) and report provider status."
    )
    parameters = {
        "type": "object",
        "properties": {
            "method": {
                "type": "string",
                "enum": list(PROVIDER_PATTERNS.keys()),
                "description": "Payment method",
            },
            "reference": {"type": "string", "description": "Provider transaction reference"},
            "amount": {"type": "number", "description": "Payment amount"},
            "currency": {"type": "string", "description": "Currency code (default USD)"},
        },
        "required": ["method", "reference"],
    }

    @classmethod
    def check_available(cls) -> bool:
        return True

    def execute(self, **kwargs: Any) -> str:
        result = validate_payment_reference(
            kwargs.get("method", ""),
            kwargs.get("reference", ""),
            kwargs.get("amount", 0),
            kwargs.get("currency", "USD"),
        )
        return json.dumps(result, ensure_ascii=False)
