"""Orchestrator — the regression engine: MAG -> DAG -> RAG -> fallback.

The orchestrator resolves a natural-language task by trying, in order:

1. **MAG** — memory-augmented generation: recall a past episode whose recipe
   matches the task and replay it (continuity across sessions).
2. **DAG** — if no memory matches, decompose the task into a known pipeline of
   tool calls and execute it in dependency order.
3. **RAG** — if no pipeline applies, retrieve grounding knowledge snippets and
   synthesise an answer from them.
4. **Fallback** — direct single-tool dispatch by intent keyword; if that fails,
   return a structured "no route" response listing the available tools.

Every successful resolution is written back to memory so the next identical or
similar task resolves at the fastest (MAG) tier.
"""
from __future__ import annotations

import json
import re
from typing import Any

from agent.memory import MemoryStore, memory_store
from agent.pipelines import find_pipeline, run_pipeline
from agent.retrieval import KnowledgeBase, knowledge_base
from agent.tool_registry import ToolRegistry, registry as registry_mod

# Keyword intent map used by the fallback single-tool dispatcher.
FALLBACK_INTENTS: list[tuple[str, str]] = [
    (r"(track (shipment|package)|shipping status|carrier|delivery status)", "carrier_tracker"),
    (r"(market price|price of|price for|commodity price|price check)", "price_fetcher"),
    (r"(weather|forecast|temperature)", "weather_fetcher"),
    (r"(nutrition|calorie|nutrient|food label)", "nutrition_fetcher"),
    (r"(translate|translation|in french|in spanish|in arabic|in swahili)", "translator"),
    (r"(geocode|geo code|coordinates|location of|distance between)", "geocoder"),
    (r"(qr code|qr)", "qr_code_tool"),
    (r"(barcode|ean[- ]?13|validate ean)", "barcode_tool"),
    (r"(certificate|cert validation|ssl|tls|validat.*cert)", "certificate_validator"),
    (r"(compliance|export compliance|regulatory)", "compliance_checker"),
    (r"(audit|report audit|verify claim|trend analysis)", "report_audit"),
    (r"(regulations|regulation fetch|market rules)", "regulation_fetcher"),
    (r"(search the web|web search|find online|look up)", "web_search"),
    (r"(read (a |the |this )?(url|page|website)|fetch url|read url)", "web_reader"),
    (r"(parse document|extract from document|document parser|parse this)", "document_parser"),
    (r"(export (data|report)|download data)", "data_exporter"),
    (r"(import (data|file)|load data|ingest)", "data_importer"),
    (r"(notify|notification|send (email|alert|message))", "notification_dispatcher"),
    (r"(eta|estimated arrival|arrival time)", "eta_predictor"),
    (r"(analyze image|image analysis|picture)", "image_analyzer"),
]

RAG_SCORE_THRESHOLD = 0.35


class Orchestrator:
    """Resolves tasks through the MAG -> DAG -> RAG -> fallback regression."""

    def __init__(
        self,
        registry: ToolRegistry | None = None,
        memory: MemoryStore | None = None,
        kb: KnowledgeBase | None = None,
    ) -> None:
        self.registry = registry if registry is not None else registry_mod
        self.memory = memory if memory is not None else memory_store
        self.kb = kb if kb is not None else knowledge_base

    # -- strategy selection -------------------------------------------------
    def resolve_strategy(self, task: str) -> str:
        """Which regression tier will serve this task (used by tests/UI)."""
        if self.memory.best_memory(task) is not None:
            return "mag"
        if find_pipeline(task) is not None:
            return "dag"
        hits = self.kb.retrieve(task, limit=1)
        if hits and hits[0]["score"] >= RAG_SCORE_THRESHOLD:
            return "rag"
        return "fallback"

    # -- tier implementations ----------------------------------------------
    def _tier_mag(self, task: str, context: dict) -> dict:
        best = self.memory.best_memory(task)
        if best is None:
            return {"matched": False}
        record = best["record"]
        steps: list[dict] = []
        last: Any = None
        for step in record.get("recipe", []):
            args = dict(step.get("args", {}))
            for key, value in context.items():
                if key in args or value is not None:
                    args.setdefault(key, value)
            try:
                last = self.registry.execute(step["tool"], **args)
            except Exception as exc:  # defensive: a stale recipe must not crash
                return {"matched": False, "error": str(exc)}
            steps.append({"tool": step["tool"], "args": args, "result": last})
        return {"matched": True, "score": best["score"], "steps": steps, "last": last}

    def _tier_dag(self, task: str, context: dict) -> dict:
        spec = find_pipeline(task)
        if spec is None:
            return {"matched": False}
        result = run_pipeline(spec, context)
        if result["status"] == "error" or result["ok_node_count"] == 0:
            return {"matched": False, "pipeline": spec["id"], "result": result}
        return {"matched": True, "pipeline": spec["id"], "result": result}

    def _tier_rag(self, task: str, context: dict) -> dict:
        hits = self.kb.retrieve(task, limit=3)
        if not hits or hits[0]["score"] < RAG_SCORE_THRESHOLD:
            return {"matched": False}
        snippets = [
            {
                "score": hit["score"],
                "id": hit["id"],
                "title": hit["title"],
                "excerpt": hit["text"][:220],
            }
            for hit in hits
        ]
        answer = (
            f"Based on the knowledge base, the relevant guidance is: {snippets[0]['title']} — "
            f"{snippets[0]['excerpt']}"
        )
        return {"matched": True, "answer": answer, "snippets": snippets}

    def _tier_fallback(self, task: str, context: dict) -> dict:
        lowered = (task or "").lower()
        matched_name: str | None = None
        for pattern, tool_name in FALLBACK_INTENTS:
            if re.search(pattern, lowered):
                matched_name = tool_name
                break
        if matched_name is None or not self.registry.available(matched_name):
            return {
                "matched": False,
                "tools": self.registry.tool_names(),
            }
        try:
            result = self.registry.execute(matched_name, **context)
        except Exception as exc:
            return {"matched": False, "error": str(exc), "tools": self.registry.tool_names()}
        return {"matched": True, "tool": matched_name, "result": result}

    # -- public API ---------------------------------------------------------
    def orchestrate(self, task: str, context: dict | None = None) -> dict:
        context = context or {}
        trace: list[dict] = []
        result: dict

        mem = self._tier_mag(task, context)
        trace.append({"strategy": "mag", "matched": bool(mem.get("matched"))})
        if mem.get("matched"):
            result = {
                "strategy": "mag",
                "task": task,
                "confidence": mem.get("score", 1.0),
                "answer": _answer_from_steps(mem.get("steps", [])),
                "steps": mem.get("steps", []),
            }
            self._remember(task, result, context)
            return result

        dag = self._tier_dag(task, context)
        trace.append({"strategy": "dag", "matched": bool(dag.get("matched"))})
        if dag.get("matched"):
            outputs = dag["result"].get("outputs", {})
            result = {
                "strategy": "dag",
                "task": task,
                "confidence": dag["result"]["ok_node_count"] / max(dag["result"]["total_node_count"], 1),
                "pipeline": dag["pipeline"],
                "answer": _answer_from_pipeline(dag["result"]),
                "outputs": outputs,
                "errors": dag["result"].get("errors", []),
            }
            self._remember(task, result, context)
            return result

        rag = self._tier_rag(task, context)
        trace.append({"strategy": "rag", "matched": bool(rag.get("matched"))})
        if rag.get("matched"):
            result = {
                "strategy": "rag",
                "task": task,
                "confidence": round(min(rag["snippets"][0]["score"], 1.0), 4),
                "answer": rag["answer"],
                "snippets": rag["snippets"],
            }
            return result

        fb = self._tier_fallback(task, context)
        trace.append({"strategy": "fallback", "matched": bool(fb.get("matched"))})
        if fb.get("matched"):
            result = {
                "strategy": "fallback",
                "task": task,
                "confidence": 0.7,
                "answer": _answer_from_fallback(fb["result"]),
                "tool": fb["tool"],
                "result": fb["result"],
            }
            self._remember(task, result, context)
            return result

        result = {
            "strategy": "fallback",
            "task": task,
            "confidence": 0.0,
            "answer": (
                "I could not map this task to a tool or pipeline. "
                "Available tools: " + ", ".join(fb.get("tools", [])[:10]) + "."
            ),
            "tools": fb.get("tools", []),
        }
        return result

    def _remember(self, task: str, result: dict, context: dict) -> None:
        recipe: list[dict] = []
        if result["strategy"] == "mag":
            recipe = [
                {"tool": s["tool"], "args": s.get("args", {})}
                for s in result.get("steps", [])
            ]
        elif result["strategy"] == "dag":
            recipe = [
                {"tool": out.get("tool"), "args": out.get("args", {})}
                for out in result.get("outputs", {}).values()
            ]
        elif result["strategy"] == "fallback":
            recipe = [{"tool": result.get("tool"), "args": context}]
        else:
            return
        tags = [result["strategy"]]
        if result["strategy"] == "dag":
            tags.append(result.get("pipeline", ""))
        if result["strategy"] == "fallback":
            tags.append(result.get("tool", ""))
        self.memory.remember(
            task=task,
            strategy=result["strategy"],
            recipe=[r for r in recipe if r.get("tool")],
            summary=result.get("answer", "")[:200],
            tags=[t for t in tags if t],
            context=context,
        )


def _answer_from_steps(steps: list[dict]) -> str:
    if not steps:
        return "Resolved from memory."
    last = steps[-1].get("result")
    return _summarise(last, "Resolved from memory.")


def _answer_from_pipeline(result: dict) -> str:
    ok = [
        out for out in result.get("outputs", {}).values()
        if isinstance(out.get("result"), dict) and out["result"].get("status") == "ok"
    ]
    if not ok:
        return "Pipeline completed with no successful step."
    last = ok[-1]
    return _summarise(last["result"], f"Pipeline '{result['pipeline']}' completed.")


def _answer_from_fallback(result: Any) -> str:
    return _summarise(result, "Tool executed.")


def _summarise(payload: Any, default: str) -> str:
    if isinstance(payload, dict):
        for key in ("summary", "message", "answer"):
            value = payload.get(key)
            if isinstance(value, str) and value:
                return value
        try:
            return json.dumps(payload, ensure_ascii=False)[:300]
        except (TypeError, ValueError):
            return str(payload)[:300]
    if payload is None:
        return default
    return str(payload)[:300]


orchestrator = Orchestrator()
