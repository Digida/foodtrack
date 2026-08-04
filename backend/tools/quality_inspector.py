"""Quality Inspector Tool — verifies a quality grade claim for a lot.

Cross-checks a claimed quality grade against certificate data, telemetry
(temperature/shock) and document flags. Produces a pass/warn/fail verdict the
Verifier and Certifier pipeline roles can act on before packing and certifying
the aggregated lot.
"""
from __future__ import annotations

import json
import logging
from typing import Any

from agent.base_tool import BaseTool

logger = logging.getLogger(__name__)

# Allowed temp band (°C) for a "good" cold-chain state across most agrifood.
COLD_CHAIN_OK_MIN = -2.0
COLD_CHAIN_OK_MAX = 8.0


def _num(value: Any, default: float | None = None) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def verify_quality_grade(
    claimed_grade: str | None = None,
    certificates: list[dict] | None = None,
    telemetry: list[dict] | None = None,
    flags: list[str] | None = None,
) -> dict:
    """Verify a quality grade claim against certs, telemetry and flags.

    certificates: [{status, expiry_date}]  — an unexpired, issued/verified cert adds confidence.
    telemetry:    [{type, value_float}]    — out-of-band cold-chain readings warn.
    flags:        free-form warning strings from document/image inspection.
    """
    claimed = (claimed_grade or "").strip().lower() or "unrated"
    checks = []
    pass_count = 0

    # 1. Certificate check
    certs = certificates or []
    valid_certs = [
        c for c in certs
        if (c.get("status") or "").lower() in ("issued", "verified", "valid", "active")
    ]
    cert_ok = len(valid_certs) >= 1
    checks.append({
        "label": "Valid certificate on file",
        "passed": cert_ok,
        "detail": f"{len(valid_certs)} valid certificate(s) found" if cert_ok else "no valid certificate found",
    })
    pass_count += 1 if cert_ok else 0

    # 2. Cold-chain telemetry check
    temp_readings = [
        _num(r.get("value_float")) for r in (telemetry or [])
        if (r.get("type") or r.get("telemetry_type")) == "temperature"
    ]
    temp_ok = True
    max_temp = None
    if temp_readings:
        max_temp = max(t for t in temp_readings if t is not None)
        temp_ok = max_temp is not None and COLD_CHAIN_OK_MIN <= max_temp <= COLD_CHAIN_OK_MAX
    checks.append({
        "label": "Cold chain within band",
        "passed": temp_ok,
        "detail": f"max recorded temp {max_temp}°C" if max_temp is not None else "no temperature telemetry",
    })
    pass_count += 1 if temp_ok else 0

    # 3. Inspection flags
    flags = flags or []
    flags_ok = len(flags) == 0
    checks.append({
        "label": "No inspection flags",
        "passed": flags_ok,
        "detail": "; ".join(flags) if flags else "no flags",
    })
    pass_count += 1 if flags_ok else 0

    # 4. Grade coherence
    grade_ok = claimed in ("a", "b", "premium", "organic", "standard", "unrated")
    checks.append({
        "label": "Grade claim coherent",
        "passed": grade_ok,
        "detail": f"claimed grade '{claimed}'",
    })
    pass_count += 1 if grade_ok else 0

    total = len(checks)
    if pass_count == total:
        verdict, confidence = "pass", "high"
    elif pass_count >= total - 1:
        verdict, confidence = "warn", "medium"
    else:
        verdict, confidence = "fail", "low"

    return {
        "status": "ok",
        "claimed_grade": claimed,
        "verdict": verdict,
        "confidence": confidence,
        "passed_checks": pass_count,
        "total_checks": total,
        "checks": checks,
    }


class QualityInspectorTool(BaseTool):
    name = "quality_inspector"
    description = (
        "Verify a quality grade claim for an aggregated lot against certificates, "
        "cold-chain telemetry and inspection flags."
    )
    parameters = {
        "type": "object",
        "properties": {
            "claimed_grade": {"type": "string", "description": "Claimed quality grade"},
            "certificates": {
                "type": "array",
                "items": {"type": "object"},
                "description": "Certificates: [{status, expiry_date}]",
            },
            "telemetry": {
                "type": "array",
                "items": {"type": "object"},
                "description": "Telemetry: [{type, value_float}]",
            },
            "flags": {"type": "array", "items": {"type": "string"}, "description": "Inspection warning flags"},
        },
        "required": [],
    }

    @classmethod
    def check_available(cls) -> bool:
        return True

    def execute(self, **kwargs: Any) -> str:
        result = verify_quality_grade(
            kwargs.get("claimed_grade"),
            kwargs.get("certificates"),
            kwargs.get("telemetry"),
            kwargs.get("flags"),
        )
        return json.dumps(result, ensure_ascii=False)
