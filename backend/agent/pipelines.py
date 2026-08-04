"""DAG — Directed Acyclic Graph pipelines for composite tasks.

A pipeline decomposes a high-level intent into an ordered graph of tool calls.
Each node runs once all of its dependencies have produced output, and node
arguments may reference earlier outputs (``{node_id.field}``). The orchestrator
regresses into a pipeline when no memory recipe matches the task — the second
step of the ``MAG -> DAG -> RAG -> fallback`` regression.
"""
from __future__ import annotations

import re
from typing import Any

from agent.tool_registry import registry

_PIPELINE_SPECS: list[dict] = [
    {
        "id": "bulking_sourcing",
        "summary": "Plan a bulking register, evaluate bids, recommend warehouse and estimate courier budget.",
        "intents": [
            "plan bulking register",
            "bulk sourcing plan",
            "aggregate supply",
            "sourcing campaign plan",
            "start a bulking campaign",
            "plan a register",
        ],
        "nodes": [
            {
                "id": "planner",
                "tool": "bulking_planner",
                "inject": ["item_name", "target_quantity", "target_price", "unit", "currency", "region", "sourcing_mode", "supply_band"],
            },
            {
                "id": "evaluator",
                "tool": "bid_evaluator",
                "args": {"action": "rank", "target_price": "{planner.target_price}"},
                "inject": ["bids"],
                "depends": ["planner"],
            },
            {
                "id": "warehouse",
                "tool": "warehouse_optimizer",
                "args": {"capacity_required": "{planner.target_quantity}"},
                "inject": ["warehouses", "cold_chain_required", "region"],
                "depends": ["planner"],
            },
            {"id": "courier", "tool": "courier_budgeter", "args": {"distance_km": 0}, "inject": ["weight_kg", "mode", "region", "currency"], "depends": ["planner"]},
        ],
    },
    {
        "id": "deal_escrow",
        "summary": "Compute escrow for a deal, check deal readiness and release conditions.",
        "intents": [
            "escrow for a deal",
            "escrow amount",
            "check escrow release",
            "deal readiness",
            "release escrow",
            "escrow requirement",
        ],
        "nodes": [
            {
                "id": "calculator",
                "tool": "escrow_calculator",
                "args": {"action": "amount"},
                "inject": ["supply_band", "deal_value", "accepted_bid_value", "target_price", "target_quantity", "currency"],
            },
            {"id": "readiness", "tool": "deal_facilitator", "args": {"action": "readiness"}, "inject": ["deal"], "depends": ["calculator"]},
            {"id": "release", "tool": "escrow_release_checker", "inject": ["register_id", "supply_band", "amount", "currency"], "depends": ["calculator"]},
        ],
    },
    {
        "id": "job_operations",
        "summary": "Check job availability, assign jobs, prioritize tasks and verify quality.",
        "intents": [
            "assign jobs",
            "shift planning",
            "prioritize tasks",
            "worker availability",
            "quality check",
            "schedule workers",
            "job operations",
        ],
        "nodes": [
            {"id": "availability", "tool": "job_availability", "inject": ["assignee_id", "job_slots", "requested_start", "requested_end"]},
            {"id": "assigner", "tool": "job_assigner", "args": {"action": "assign"}, "inject": ["workers", "jobs", "shift"], "depends": ["availability"]},
            {"id": "prioritizer", "tool": "task_prioritizer", "inject": ["tasks"], "depends": ["assigner"]},
            {"id": "inspector", "tool": "quality_inspector", "inject": ["item_name", "grade", "certifications", "lab_results"], "depends": ["assigner"]},
        ],
    },
    {
        "id": "settlement_run",
        "summary": "Calculate seller settlements, aggregate by payee, validate payment and report.",
        "intents": [
            "calculate settlement",
            "settle sellers",
            "settlement run",
            "pay out sellers",
            "aggregate settlements",
            "seller payout",
        ],
        "nodes": [
            {
                "id": "calculator",
                "tool": "settlement_calculator",
                "args": {"action": "batch"},
                "inject": ["settlements", "platform_fee_rate", "currency"],
            },
            {
                "id": "aggregator",
                "tool": "settlement_aggregator",
                "args": {"settlements": "{calculator.settlements}"},
                "depends": ["calculator"],
            },
            {"id": "validator", "tool": "payment_validator", "inject": ["method", "reference", "amount", "currency"], "depends": ["calculator"]},
            {
                "id": "reporter",
                "tool": "settlement_reporter",
                "args": {"settlements": "{calculator.settlements}"},
                "depends": ["aggregator"],
            },
        ],
    },
    {
        "id": "compliance_trace",
        "summary": "Parse a document, check compliance for a market and audit the findings.",
        "intents": [
            "compliance check",
            "export compliance",
            "regulatory check",
            "document audit",
            "market compliance",
        ],
        "nodes": [
            {"id": "parser", "tool": "document_parser", "inject": ["text", "content"]},
            {"id": "compliance", "tool": "compliance_checker", "inject": ["item_category", "target_market", "current_certs", "current_labelling"], "depends": ["parser"]},
            {"id": "audit", "tool": "report_audit", "args": {"action": "data_quality"}, "inject": ["data"], "depends": ["compliance"]},
        ],
    },
]


def get_pipelines() -> list[dict]:
    return [
        {
            "id": p["id"],
            "summary": p["summary"],
            "intents": list(p["intents"]),
            "node_count": len(p["nodes"]),
            "tools": [n["tool"] for n in p["nodes"]],
        }
        for p in _PIPELINE_SPECS
    ]


def _norm_words(text: str) -> set[str]:
    """Tokenize and lightly de-pluralize (settlements -> settlement)."""
    words = set()
    for token in re.findall(r"[a-z0-9_]{2,}", (text or "").lower()):
        if token.endswith("ies") and len(token) > 4:
            words.add(token[:-3] + "y")
        elif token.endswith("es") and len(token) > 3:
            words.add(token[:-2])
        elif token.endswith("s") and len(token) > 3:
            words.add(token[:-1])
        words.add(token)
    return words


def find_pipeline(text: str) -> dict | None:
    """Pick the pipeline whose intent phrase best matches the task text."""
    words = _norm_words(text)
    best, best_score = None, 0.0
    for spec in _PIPELINE_SPECS:
        spec_best = 0.0
        for phrase in spec["intents"]:
            phrase_words = _norm_words(phrase)
            hits = len(words & phrase_words)
            if hits:
                spec_best = max(spec_best, hits / max(len(phrase_words), 1))
        if spec_best > best_score:
            best, best_score = spec, spec_best
    if best is not None and best_score >= 0.6:
        return best
    return None


def _resolve_refs(value: Any, outputs: dict, errors: list) -> Any:
    """Resolve ``{node_id.field}`` references inside args."""
    if isinstance(value, str):
        match = re.fullmatch(r"\{(?P<node>[A-Za-z0-9_]+)\.(?P<field>[A-Za-z0-9_]+)\}", value)
        if match:
            out = outputs.get(match.group("node"), {}).get("result", {})
            if isinstance(out, dict):
                return out.get(match.group("field"))
            return None
        return value
    if isinstance(value, dict):
        return {k: _resolve_refs(v, outputs, errors) for k, v in value.items()}
    if isinstance(value, list):
        return [_resolve_refs(v, outputs, errors) for v in value]
    return value


def _topo_order(nodes: list[dict]) -> list[dict]:
    """Kahn's algorithm with cycle detection."""
    ids = {n["id"] for n in nodes}
    for n in nodes:
        for dep in n.get("depends", []):
            if dep not in ids:
                raise ValueError(f"Pipeline node {n['id']} depends on unknown node {dep!r}")

    remaining = list(nodes)
    order: list[dict] = []
    while remaining:
        ready = [
            n for n in remaining
            if all(dep in {x["id"] for x in order} for dep in n.get("depends", []))
        ]
        if not ready:
            raise ValueError("Pipeline contains a dependency cycle")
        picked = ready[0]
        remaining.remove(picked)
        order.append(picked)
    return order


def run_pipeline(spec: dict, inputs: dict) -> dict:
    """Execute a pipeline spec, returning per-node outputs and errors."""
    try:
        order = _topo_order(spec["nodes"])
    except ValueError as exc:
        return {"status": "error", "message": str(exc), "outputs": {}, "errors": []}

    outputs: dict[str, dict] = {}
    errors: list[dict] = []

    for node in order:
        args = dict(node.get("args", {}))
        for key in node.get("inject", []):
            if key in inputs and inputs[key] is not None:
                args[key] = inputs[key]
        try:
            resolved = _resolve_refs(args, outputs, errors)
        except Exception as exc:  # defensive: never break the DAG on ref errors
            errors.append({"node": node["id"], "tool": node["tool"], "error": str(exc)})
            continue
        try:
            result = registry.execute(node["tool"], **resolved)
        except Exception as exc:
            errors.append({"node": node["id"], "tool": node["tool"], "error": str(exc)})
            continue
        outputs[node["id"]] = {"tool": node["tool"], "args": resolved, "result": result}

    ok_nodes = [o for o in outputs.values() if isinstance(o.get("result"), dict) and o["result"].get("status") == "ok"]
    return {
        "status": "ok" if ok_nodes else "degraded",
        "pipeline": spec["id"],
        "outputs": outputs,
        "errors": errors,
        "ok_node_count": len(ok_nodes),
        "total_node_count": len(spec["nodes"]),
    }
