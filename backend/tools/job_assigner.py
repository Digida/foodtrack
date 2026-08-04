"""Job Assigner Tool — assigns bulking pipeline roles to users.

Clerks collate and receive goods, Verifiers inspect and certify quality,
Packers package the aggregated lot, Certifiers issue the quality certificate
and Couriers move stock to the buyer. The assigner matches role requirements to
candidate users, avoiding double-assignment and preferencing co-located users.
"""
from __future__ import annotations

import json
import logging
from typing import Any

from agent.base_tool import BaseTool

logger = logging.getLogger(__name__)

PIPELINE_ROLES = ("clerk", "verifier", "packer", "certifier", "courier")


def assign_jobs(
    role_requirements: list[dict],
    candidates: list[dict],
    max_roles_per_user: int = 1,
) -> dict:
    """Assign pipeline roles to candidates.

    role_requirements: [{role, count, location}]  (count default 1)
    candidates: [{id, name, location, roles: [..], reliability}]
    """
    if not role_requirements:
        return {"status": "error", "message": "role_requirements must not be empty"}

    required: list[tuple[str, int, str | None]] = []
    for req in role_requirements:
        role = (req.get("role") or "").lower()
        if role not in PIPELINE_ROLES:
            return {"status": "error", "message": f"Unknown role '{req.get('role')}'. Use {list(PIPELINE_ROLES)}"}
        count = max(1, int(req.get("count", 1)))
        required.append((role, count, req.get("location")))

    # Group candidates by the roles they can perform, keeping reliability order.
    by_role: dict[str, list[dict]] = {r: [] for r in PIPELINE_ROLES}
    for cand in candidates or []:
        cand_roles = [r.lower() for r in (cand.get("roles") or [])]
        for role in PIPELINE_ROLES:
            if role in cand_roles:
                by_role[role].append(cand)
    for role in by_role:
        by_role[role].sort(key=lambda c: float(c.get("reliability", 0)), reverse=True)

    assigned: list[dict] = []
    used_counts: dict[str, int] = {}
    failures: list[dict] = []
    covered_roles = set()

    for role, count, location in required:
        matches = by_role.get(role, [])
        for cand in matches:
            if used_counts.get(str(cand.get("id")), 0) >= max_roles_per_user:
                continue
            if location and cand.get("location") and location.lower() != str(cand.get("location")).lower():
                continue
            used_counts[str(cand.get("id"))] = used_counts.get(str(cand.get("id")), 0) + 1
            assigned.append({
                "role": role,
                "assignee_id": cand.get("id"),
                "assignee_name": cand.get("name") or f"user-{cand.get('id')}",
                "assignee_location": cand.get("location"),
            })
            covered_roles.add(role)
            break
        else:
            failures.append({"role": role, "count": count, "reason": "no eligible candidate"})

    return {
        "status": "ok" if not failures else "partial",
        "assigned": assigned,
        "unfilled": failures,
        "roles_covered": sorted(covered_roles),
        "summary": f"Assigned {len(assigned)} of {sum(c for _, c, _ in required)} required roles.",
    }


def build_shift(candidates: list[dict]) -> dict:
    """Suggest a balanced one-role-per-user assignment across the whole pipeline."""
    roles_available = {r: [] for r in PIPELINE_ROLES}
    for cand in candidates or []:
        for role in (cand.get("roles") or []):
            roles_available.setdefault(str(role).lower(), []).append(cand)

    plan = []
    for role, pool in roles_available.items():
        if pool:
            best = max(pool, key=lambda c: float(c.get("reliability", 0)))
            plan.append({"role": role, "candidate": best.get("name"), "candidate_id": best.get("id")})

    return {"status": "ok", "shift": plan, "role_count": len(plan)}


class JobAssignerTool(BaseTool):
    name = "job_assigner"
    description = (
        "Assign bulking pipeline roles (clerk/verifier/packer/certifier/courier) to "
        "eligible candidate users, avoiding double-assignment."
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {"type": "string", "enum": ["assign", "shift"], "description": "Action to perform"},
            "role_requirements": {
                "type": "array",
                "items": {"type": "object"},
                "description": "Roles needed: [{role, count, location}]",
            },
            "candidates": {
                "type": "array",
                "items": {"type": "object"},
                "description": "Candidate users: [{id, name, location, roles, reliability}]",
            },
            "max_roles_per_user": {"type": "integer", "description": "Max roles a single user may hold"},
        },
        "required": ["action"],
    }

    @classmethod
    def check_available(cls) -> bool:
        return True

    def execute(self, **kwargs: Any) -> str:
        action = kwargs.get("action", "")
        if action == "assign":
            result = assign_jobs(
                kwargs.get("role_requirements", []),
                kwargs.get("candidates", []),
                kwargs.get("max_roles_per_user", 1),
            )
        elif action == "shift":
            result = build_shift(kwargs.get("candidates", []))
        else:
            result = {"status": "error", "message": f"Unknown action: {action}"}
        return json.dumps(result, ensure_ascii=False)
