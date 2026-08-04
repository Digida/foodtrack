"""Tests for the 20 new commerce tools (bulking, jobs, escrow, settlements)."""


from tools.bulking_planner import plan_register, BulkingPlannerTool
from tools.bid_evaluator import rank_bids
from tools.warehouse_optimizer import recommend_warehouse
from tools.courier_budgeter import estimate_courier_budget
from tools.deal_facilitator import deal_readiness_check
from tools.job_assigner import assign_jobs
from tools.workflow_engine import validate_transition, pipeline_stage
from tools.task_prioritizer import prioritize_tasks
from tools.quality_inspector import verify_quality_grade
from tools.job_availability import check_availability
from tools.escrow_calculator import escrow_percentage, escrow_amount
from tools.escrow_release_checker import check_release
from tools.escrow_dispute_resolver import resolve_dispute
from tools.escrow_reporter import escrow_report
from tools.settlement_calculator import calculate_settlement, calculate_settlement_batch
from tools.settlement_aggregator import aggregate_settlements
from tools.payment_validator import validate_payment_reference
from tools.settlement_reporter import settlement_report
from tools.settlement_notifier import settlement_event_notification


class TestBulkingPlanner:
    def test_plan_register_ok(self):
        plan = plan_register("maize", 5000, target_price=0.35, supply_band="abundant")
        assert plan["status"] == "ok"
        assert plan["feasible"] is True
        assert plan["escrow_percentage"] == 0.30
        assert plan["escrow_basis"] == 1750.0

    def test_plan_register_zero_quantity(self):
        plan = plan_register("maize", 0)
        assert plan["status"] == "error"

    def test_plan_register_rare_band(self):
        plan = plan_register("saffron", 10, target_price=40.0, supply_band="rare")
        assert plan["escrow_percentage"] == 0.65

    def test_tool_executes(self):
        raw = BulkingPlannerTool().execute(item_name="beans", target_quantity=2000, target_price=1.0)
        assert '"status": "ok"' in raw


class TestBidEvaluator:
    def test_rank_bids(self):
        result = rank_bids(
            [{"id": 1, "unit_price": 0.30, "quantity": 1000},
             {"id": 2, "unit_price": 0.50, "quantity": 1000}],
            target_price=0.35,
        )
        assert result["status"] == "ok"
        assert result["ranked_bids"][0]["id"] == 1

    def test_rank_bids_bad_target(self):
        assert rank_bids([], target_price=0)["status"] == "error"


class TestWarehouseOptimizer:
    def test_recommend_warehouse(self):
        warehouses = [
            {"id": 1, "name": "WH A", "capacity": 8000, "storage_cost": 6, "cold_chain": True},
            {"id": 2, "name": "WH B", "capacity": 20000, "storage_cost": 8, "cold_chain": False},
        ]
        result = recommend_warehouse(5000, warehouses=warehouses, cold_chain_required=True)
        assert result["status"] == "ok"
        assert result["best"]["id"] == 1

    def test_requires_warehouses(self):
        assert recommend_warehouse(5000)["status"] == "error"


class TestCourierBudgeter:
    def test_estimate_budget(self):
        result = estimate_courier_budget(120, weight_kg=5000)
        assert result["status"] == "ok"
        assert result["estimated_budget"] > 0


class TestDealFacilitator:
    def test_readiness_check(self):
        result = deal_readiness_check(
            credentials_exchanged=True,
            certificate_present=True,
            warehouse_confirmed=True,
            courier_assigned=True,
        )
        assert result["status"] == "ok"
        assert result["ready"] is True

    def test_readiness_incomplete(self):
        result = deal_readiness_check(credentials_exchanged=True)
        assert result["ready"] is False
        assert result["met_count"] == 1


class TestJobAssigner:
    def test_assign_jobs(self):
        result = assign_jobs(
            [{"role": "packer", "count": 1}],
            [{"id": 1, "name": "Grace", "roles": ["packer"]}],
        )
        assert result["status"] == "ok"
        assert result["assigned"][0]["assignee_id"] == 1
        assert result["assigned"][0]["role"] == "packer"


class TestWorkflowEngine:
    def test_valid_transition(self):
        result = validate_transition("register", "draft", "sourcing")
        assert result["status"] == "ok"
        assert result["allowed"] is True

    def test_illegal_transition(self):
        result = validate_transition("register", "draft", "closed")
        assert result["allowed"] is False

    def test_pipeline_stage(self):
        result = pipeline_stage("register", "sourcing")
        assert result["status"] == "ok"


class TestTaskPrioritizer:
    def test_prioritize(self):
        tasks = [
            {"id": "A", "severity": "high", "due_at": "2026-08-01T00:00:00Z"},
            {"id": "B", "severity": "low", "due_at": "2026-12-01T00:00:00Z"},
        ]
        result = prioritize_tasks(tasks)
        assert result["status"] == "ok"
        assert result["task_count"] == 2
        assert result["work_order"][0]["id"] == "A"

    def test_prioritize_empty(self):
        result = prioritize_tasks([])
        assert result["task_count"] == 0


class TestQualityInspector:
    def test_pass(self):
        result = verify_quality_grade(
            "A",
            certificates=[{"status": "issued"}],
            telemetry=[{"type": "temperature", "value_float": 4.0}],
        )
        assert result["status"] in ("ok", "pass")
        assert result["verdict"] != "fail"

    def test_warn_on_flags(self):
        result = verify_quality_grade(
            "A",
            certificates=[{"status": "issued"}],
            flags=["possible moisture damage"],
        )
        assert result["verdict"] == "warn"


class TestJobAvailability:
    def test_no_conflict(self):
        result = check_availability(
            assignee_id=1,
            job_slots=[{"id": "S1", "start": "2026-08-04T08:00:00", "end": "2026-08-04T10:00:00"}],
            requested_start="2026-08-04T11:00:00",
            requested_end="2026-08-04T12:00:00",
        )
        assert result["status"] == "ok"
        assert result["available"] is True


class TestEscrowCalculator:
    def test_percentage_abundant(self):
        assert escrow_percentage("abundant")["escrow_rate"] == 0.30

    def test_percentage_rare(self):
        assert escrow_percentage("rare")["escrow_rate"] == 0.65

    def test_amount_from_deal(self):
        result = escrow_amount("rare", deal_value=10000)
        assert result["required_amount"] == 6500.0
        assert result["basis_source"] == "deal_value"

    def test_amount_from_target(self):
        result = escrow_amount("abundant", target_price=2.0, target_quantity=500)
        assert result["required_amount"] == 300.0


class TestEscrowReleaseChecker:
    def test_release_when_satisfied(self):
        result = check_release(
            "held",
            buyer_delivery_confirmed=True,
            goods_received_confirmed=True,
            documents_verified=True,
        )
        assert result["status"] == "ok"
        assert result["recommendation"] == "release_now"

    def test_hold_when_missing(self):
        result = check_release("held")
        assert result["recommendation"] == "hold"


class TestEscrowDisputeResolver:
    def test_resolve_dispute(self):
        result = resolve_dispute("buyer", "buyer claims goods damaged")
        assert result["status"] == "ok"


class TestEscrowReporter:
    def test_report(self):
        result = escrow_report(
            [{"amount": 300, "currency": "USD", "status": "held"},
             {"amount": 650, "currency": "USD", "status": "released"}]
        )
        assert result["status"] == "ok"
        assert result["escrow_count"] == 2


class TestSettlementCalculator:
    def test_single(self):
        result = calculate_settlement(100, 2.0)
        assert result["status"] == "ok"
        assert result["gross_amount"] == 200.0
        assert result["platform_fee"] == 5.0
        assert result["net_amount"] == 195.0

    def test_single_invalid(self):
        assert calculate_settlement(0, 2.0)["status"] == "error"

    def test_batch(self):
        result = calculate_settlement_batch([
            {"id": 1, "quantity": 100, "unit_price": 2.0},
            {"id": 2, "quantity": 50, "unit_price": 4.0},
        ])
        assert result["settlement_count"] == 2
        assert result["totals"]["net"] == 390.0


class TestSettlementAggregator:
    def test_aggregate(self):
        result = aggregate_settlements([
            {"payee_id": 1, "payee_name": "Farmer A", "gross_amount": 200, "net_amount": 195},
            {"payee_id": 1, "payee_name": "Farmer A", "gross_amount": 100, "net_amount": 97.5},
            {"payee_id": 2, "payee_name": "Coop B", "gross_amount": 400, "net_amount": 390},
        ])
        assert result["status"] == "ok"
        assert result["payee_count"] == 2
        by_id = {p["payee_id"]: p for p in result["payees"]}
        assert by_id[1]["net_amount"] == 292.5

    def test_aggregate_empty(self):
        assert aggregate_settlements(None)["payee_count"] == 0


class TestPaymentValidator:
    def test_mpesa_valid(self):
        result = validate_payment_reference("mpesa", "STK123456789")
        assert result["status"] == "ok"
        assert result["provider_status"] == "confirmed"

    def test_stripe_invalid(self):
        result = validate_payment_reference("stripe", "not-a-ref")
        assert result["status"] == "invalid"

    def test_unsupported_method(self):
        assert validate_payment_reference("bitcoin", "x")["status"] == "error"


class TestSettlementReporter:
    def test_report(self):
        result = settlement_report([
            {"net_amount": 195, "currency": "USD", "status": "paid"},
            {"net_amount": 97.5, "currency": "USD", "status": "pending"},
        ])
        assert result["status"] == "ok"
        assert result["settlement_count"] == 2


class TestSettlementNotifier:
    def test_paid_message(self):
        result = settlement_event_notification("paid", settlement_number="STL-1", payee_name="Farmer A", amount=195)
        assert result["status"] == "ok"
        assert "STL-1" in result["message"]

    def test_unknown_event(self):
        assert settlement_event_notification("bogus")["status"] == "error"
