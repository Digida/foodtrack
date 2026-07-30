import time
from collections import deque
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select, func

from app.models.certificate import Certificate
from app.models.telemetry import TelemetryAlert
from app.models.recall import Recall

# In-memory request tracking for SLA calculation
_request_timestamps: deque = deque(maxlen=10000)
_error_count: int = 0
_total_requests: int = 0


def record_request(duration_ms: int, status_code: int):
    global _error_count, _total_requests
    _request_timestamps.append({"time": time.time(), "duration_ms": duration_ms})
    _total_requests += 1
    if status_code >= 500:
        _error_count += 1


async def get_health(db: AsyncSession) -> dict:
    db_ok = False
    try:
        await db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        pass

    now = datetime.now(timezone.utc)
    return {
        "status": "ok" if db_ok else "degraded",
        "database": "connected" if db_ok else "disconnected",
        "timestamp": str(now),
    }


async def get_sla(db: AsyncSession) -> dict:
    """SLA dashboard: uptime, p95 latency, error budget."""
    now = datetime.now(timezone.utc)
    db_ok = False
    try:
        await db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        pass

    # Calculate from in-memory request log (last 1 hour)
    cutoff = time.time() - 3600
    recent = [r for r in _request_timestamps if r["time"] >= cutoff]
    total_recent = len(recent)
    errors_recent = sum(1 for r in _request_timestamps if r["time"] >= cutoff)

    sla_uptime = 100.0 if db_ok else 0.0

    p95_latency = 0.0
    if recent:
        durations = sorted(r["duration_ms"] for r in recent)
        idx = int(len(durations) * 0.95)
        p95_latency = durations[min(idx, len(durations) - 1)]

    error_rate = 0.0
    if total_recent > 0:
        error_rate = round((errors_recent / max(total_recent, 1)) * 100, 2)

    return {
        "timestamp": str(now),
        "uptime_pct": round(sla_uptime, 3),
        "database_connected": db_ok,
        "total_requests_1h": total_recent,
        "error_rate_pct_1h": error_rate,
        "p95_latency_ms_1h": round(p95_latency, 1),
        "error_budget_remaining_pct": round(max(0, 100.0 - error_rate), 2),
        "sla_target": "99.9% uptime, <1% error rate, p95 < 500ms",
    }


async def get_metrics(db: AsyncSession) -> dict:
    from sqlalchemy import inspect as sa_inspect

    table_counts = {}
    inspector = sa_inspect(db.bind)
    for table_name in inspector.get_table_names():
        try:
            result = await db.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
            count = result.scalar() or 0
            table_counts[table_name] = count
        except Exception:
            pass

    now = datetime.now(timezone.utc)

    pending_certs = await db.execute(select(func.count()).where(Certificate.expiry_date < now))
    unacknowledged_alerts = await db.execute(select(func.count()).where(TelemetryAlert.acknowledged == False))
    active_recalls = await db.execute(select(func.count()).where(Recall.status != "completed"))

    return {
        "timestamp": str(now),
        "tables": table_counts,
        "pending_certificates": pending_certs.scalar() or 0,
        "unacknowledged_alerts": unacknowledged_alerts.scalar() or 0,
        "active_recalls": active_recalls.scalar() or 0,
    }
