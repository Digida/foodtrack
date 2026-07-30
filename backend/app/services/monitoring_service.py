import time
from collections import deque
from datetime import datetime, timezone
from typing import TypedDict

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select, func

from app.models.certificate import Certificate
from app.models.telemetry import TelemetryAlert
from app.models.recall import Recall


class _RequestEntry(TypedDict):
    time: float
    duration_ms: int
    status_code: int


# In-memory request tracking for SLA calculation.
# NOTE: This is process-local and resets on restart/redeploy.
# For persistent SLA metrics, persist entries to a database table instead.
_request_timestamps: deque[_RequestEntry] = deque(maxlen=10000)
_total_requests: int = 0


def record_request(duration_ms: int, status_code: int) -> None:
    """Called by the logging middleware for every request."""
    global _total_requests
    _request_timestamps.append({
        "time": time.time(),
        "duration_ms": duration_ms,
        "status_code": status_code,
    })
    _total_requests += 1


async def get_health(db: AsyncSession) -> dict:
    db_ok = False
    try:
        await db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        pass

    return {
        "status": "ok" if db_ok else "degraded",
        "database": "connected" if db_ok else "disconnected",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


async def get_sla(db: AsyncSession) -> dict:
    """SLA dashboard: uptime, p95 latency, error rate, error budget."""
    now = datetime.now(timezone.utc)
    db_ok = False
    try:
        await db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        pass

    cutoff = time.time() - 3600
    recent = [r for r in _request_timestamps if r["time"] >= cutoff]
    total_recent = len(recent)

    # Count only 5xx responses as errors
    errors_recent = sum(1 for r in recent if r["status_code"] >= 500)

    sla_uptime = 100.0 if db_ok else 0.0

    p95_latency = 0.0
    if recent:
        durations = sorted(r["duration_ms"] for r in recent)
        idx = min(int(len(durations) * 0.95), len(durations) - 1)
        p95_latency = durations[idx]

    error_rate = 0.0
    if total_recent > 0:
        error_rate = round((errors_recent / total_recent) * 100, 2)

    return {
        "timestamp": now.isoformat(),
        "uptime_pct": round(sla_uptime, 3),
        "database_connected": db_ok,
        "total_requests_1h": total_recent,
        "error_count_1h": errors_recent,
        "error_rate_pct_1h": error_rate,
        "p95_latency_ms_1h": round(p95_latency, 1),
        "error_budget_remaining_pct": round(max(0, 100.0 - error_rate), 2),
        "sla_target": "99.9% uptime, <1% error rate, p95 < 500ms",
    }


# Known application tables — avoids using synchronous SQLAlchemy inspector
# on an async engine (which raises MissingGreenlet).
_KNOWN_TABLES = [
    "users", "tenants", "products", "taxonomy_items", "taxonomy_nodes",
    "taxonomies", "batches", "shipments", "shipment_tracking_events",
    "certificates", "certificate_requests", "cargo_registrations",
    "warehouses", "warehouse_items", "inventory_movements", "item_inventories",
    "collections", "collection_items", "tracking_events",
    "recalls", "recall_events", "suppliers", "supplier_scorecards",
    "cargo_policies", "insurance_claims", "telemetry_readings", "telemetry_alerts",
    "webhook_subscriptions", "event_logs", "api_keys", "search_logs",
    "enrichment_logs", "enrichment_suggestions", "item_carbon_footprints",
    "archive_policies", "item_rates", "item_identifier_logs",
]


async def get_metrics(db: AsyncSession) -> dict:
    """Return row counts for known tables plus key operational metrics."""
    now = datetime.now(timezone.utc)
    table_counts: dict[str, int] = {}

    for table_name in _KNOWN_TABLES:
        try:
            result = await db.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
            table_counts[table_name] = result.scalar() or 0
        except Exception:
            # Table may not exist in all migration states — skip gracefully
            pass

    expiring_certs = await db.execute(
        select(func.count(Certificate.id)).where(Certificate.expiry_date < now)
    )
    unacked_alerts = await db.execute(
        select(func.count(TelemetryAlert.id)).where(TelemetryAlert.acknowledged == False)
    )
    active_recalls = await db.execute(
        select(func.count(Recall.id)).where(Recall.status != "completed")
    )

    return {
        "timestamp": now.isoformat(),
        "tables": table_counts,
        "expiring_certificates": expiring_certs.scalar() or 0,
        "unacknowledged_alerts": unacked_alerts.scalar() or 0,
        "active_recalls": active_recalls.scalar() or 0,
    }
