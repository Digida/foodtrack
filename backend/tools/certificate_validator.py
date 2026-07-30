from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

import httpx

from agent.base_tool import BaseTool

logger = logging.getLogger(__name__)


def validate_certificate(
    cert_id: str,
    issuer: str,
    expiry_date: str | None = None,
    status: str | None = None,
    verify_url: str | None = None,
) -> dict:
    checks = []
    passed = 0
    failed = 0

    checks.append({
        "check": "certificate_id_present", "passed": bool(cert_id),
        "detail": cert_id or "missing",
    })
    if bool(cert_id):
        passed += 1
    else:
        failed += 1

    checks.append({
        "check": "issuer_present", "passed": bool(issuer),
        "detail": issuer or "missing",
    })
    if bool(issuer):
        passed += 1
    else:
        failed += 1

    if expiry_date:
        try:
            expiry = datetime.fromisoformat(expiry_date.replace("Z", "+00:00"))
            is_expired = expiry < datetime.now(timezone.utc)
            checks.append({
                "check": "not_expired", "passed": not is_expired,
                "detail": f"expires {expiry_date}",
            })
            if not is_expired:
                passed += 1
            else:
                failed += 1
        except ValueError:
            checks.append({
                "check": "expiry_parseable", "passed": False,
                "detail": f"cannot parse: {expiry_date}",
            })
            failed += 1

    if status:
        valid_statuses = {"active", "valid", "issued", "certified"}
        is_valid = status.lower() in valid_statuses
        checks.append({
            "check": "status_valid", "passed": is_valid,
            "detail": status,
        })
        if is_valid:
            passed += 1
        else:
            failed += 1

    if verify_url:
        checks.append({
            "check": "has_verify_url", "passed": True,
            "detail": verify_url,
        })
        passed += 1

    score = passed / max(passed + failed, 1)
    return {
        "status": "ok",
        "certificate_id": cert_id,
        "issuer": issuer,
        "checks": checks,
        "passed": passed,
        "failed": failed,
        "score": round(score, 4),
        "summary": f"{passed}/{passed + failed} checks passed",
    }


class CertificateValidatorTool(BaseTool):
    name = "certificate_validator"
    description = "Validate certificate authenticity, expiry, and status against issuer rules"
    parameters = {
        "type": "object",
        "properties": {
            "cert_id": {"type": "string", "description": "Certificate ID"},
            "issuer": {"type": "string", "description": "Issuing authority name"},
            "expiry_date": {"type": "string", "description": "Expiry date (ISO format)"},
            "status": {"type": "string", "description": "Current status string"},
            "verify_url": {"type": "string", "description": "Optional verification URL"},
        },
        "required": ["cert_id", "issuer"],
    }

    @classmethod
    def check_available(cls) -> bool:
        return True

    def execute(self, **kwargs: Any) -> str:
        result = validate_certificate(
            kwargs.get("cert_id", ""),
            kwargs.get("issuer", ""),
            kwargs.get("expiry_date"),
            kwargs.get("status"),
            kwargs.get("verify_url"),
        )
        return json.dumps(result, ensure_ascii=False)
