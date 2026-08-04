"""Tests for the agent orchestrator regression: MAG -> DAG -> RAG -> fallback.

Each test uses a fresh MemoryStore/KnowledgeBase so no state leaks between
tests. Registry is the shared module singleton (read-only).
"""


from agent.memory import MemoryStore
from agent.orchestrator import Orchestrator
from agent.pipelines import find_pipeline, run_pipeline
from agent.retrieval import KnowledgeBase
from agent.tool_registry import registry


def _fresh_orchestrator() -> Orchestrator:
    return Orchestrator(registry=registry, memory=MemoryStore(), kb=KnowledgeBase())


class TestRegistry:
    def test_counts_forty_tools(self):
        assert registry.count() == 40

    def test_all_tools_available(self):
        for name in registry.tool_names():
            assert registry.available(name), f"{name} should be available"

    def test_catalog_has_schema(self):
        catalog = registry.list_tools()
        names = {t["name"] for t in catalog}
        for expected in ("bulking_planner", "escrow_calculator", "settlement_calculator", "workflow_engine"):
            assert expected in names
        for tool in catalog:
            assert tool["description"]
            assert tool["parameters"]


class TestRegressionOrder:
    def test_unknown_task_falls_back(self):
        orch = _fresh_orchestrator()
        result = orch.orchestrate("do something completely unknown xyzzy")
        assert result["strategy"] == "fallback"
        assert result["confidence"] == 0.0
        assert len(result["tools"]) == 40

    def test_bulking_task_uses_dag(self):
        orch = _fresh_orchestrator()
        result = orch.orchestrate("plan bulking register for maize")
        assert result["strategy"] == "dag"
        assert result["pipeline"] == "bulking_sourcing"
        assert result["confidence"] > 0

    def test_repeat_task_upgrades_to_mag(self):
        orch = _fresh_orchestrator()
        first = orch.orchestrate("plan bulking register for maize")
        assert first["strategy"] == "dag"
        second = orch.orchestrate("plan bulking register for maize")
        assert second["strategy"] == "mag"
        assert second["steps"]

    def test_policy_question_uses_rag(self):
        orch = _fresh_orchestrator()
        result = orch.orchestrate("what is the escrow policy")
        assert result["strategy"] == "rag"
        assert result["snippets"]

    def test_single_tool_intent_uses_fallback(self):
        orch = _fresh_orchestrator()
        result = orch.orchestrate("show me the weather in Nairobi")
        assert result["strategy"] == "fallback"
        assert result["tool"] == "weather_fetcher"

    def test_resolve_strategy_matches(self):
        orch = _fresh_orchestrator()
        assert orch.resolve_strategy("plan bulking register for maize") == "dag"
        assert orch.resolve_strategy("totally unknown xyzzy") == "fallback"

    def test_escrow_pipeline(self):
        orch = _fresh_orchestrator()
        result = orch.orchestrate(
            "escrow for a deal",
            {"supply_band": "rare", "deal_value": 25000},
        )
        assert result["strategy"] == "dag"
        calculator = result["outputs"]["calculator"]["result"]
        assert calculator["required_amount"] == 16250.0

    def test_settlement_pipeline(self):
        orch = _fresh_orchestrator()
        result = orch.orchestrate(
            "calculate settlements for farmers",
            {"settlements": [
                {"payee_id": 1, "payee_name": "Farmer A", "quantity": 1000, "unit_price": 0.4},
            ]},
        )
        assert result["strategy"] == "dag"
        assert result["outputs"]["aggregator"]["result"]["payee_count"] == 1


class TestPipelines:
    def test_cycle_detection(self):
        spec = {
            "id": "cycle",
            "intents": [],
            "nodes": [
                {"id": "a", "tool": "bulking_planner", "depends": ["b"]},
                {"id": "b", "tool": "bulking_planner", "depends": ["a"]},
            ],
        }
        result = run_pipeline(spec, {})
        assert result["status"] == "error"
        assert "cycle" in result["message"]

    def test_unknown_dependency(self):
        spec = {
            "id": "bad-dep",
            "intents": [],
            "nodes": [{"id": "a", "tool": "bulking_planner", "depends": ["ghost"]}],
        }
        assert run_pipeline(spec, {})["status"] == "error"

    def test_find_pipeline_plural(self):
        assert find_pipeline("calculate settlements for farmers")["id"] == "settlement_run"

    def test_find_pipeline_none(self):
        assert find_pipeline("totally unrelated gibberish") is None
