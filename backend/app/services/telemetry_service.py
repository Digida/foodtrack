import json
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.telemetry import TelemetryReading, TelemetryAlert
from app.models.user import User, UserRole
from tools.notification_dispatcher import send_notification

PAGE_SIZE = 20

TEMP_ALERT_THRESHOLD_C = 30
TEMP_FROZEN_THRESHOLD_C = -15
HUMIDITY_HIGH_THRESHOLD = 85
SHOCK_THRESHOLD_G = 5.0


async def ingest_telemetry(
    db: AsyncSession,
    device_id: str,
    telemetry_type: str,
    value: float | str,
    unit: str | None = None,
    item_id: int | None = None,
    batch_id: int | None = None,
    location_lat: float | None = None,
    location_lng: float | None = None,
    metadata: dict | None = None,
    recorded_at: datetime | None = None,
) -> TelemetryReading:
    reading = TelemetryReading(
        device_id=device_id,
        telemetry_type=telemetry_type,
        value_float=value if isinstance(value, (int, float)) else None,
        value_str=str(value) if not isinstance(value, (int, float)) else None,
        unit=unit,
        item_id=item_id,
        batch_id=batch_id,
        location_lat=location_lat,
        location_lng=location_lng,
        metadata_json=json.dumps(metadata) if metadata else None,
        recorded_at=recorded_at or datetime.now(timezone.utc),
    )
    db.add(reading)
    await db.commit()
    await db.refresh(reading)

    alerts = []
    if telemetry_type == "temperature":
        val = value if isinstance(value, (int, float)) else None
        if val is not None:
            if val > TEMP_ALERT_THRESHOLD_C:
                alert = TelemetryAlert(device_id=device_id, telemetry_type=telemetry_type, rule_name="high_temp", threshold=TEMP_ALERT_THRESHOLD_C, actual_value=val, message=f"Temperature {val}{unit or '°C'} exceeds {TEMP_ALERT_THRESHOLD_C}°C", severity="warning")
                db.add(alert)
                alerts.append(alert)
            elif val < TEMP_FROZEN_THRESHOLD_C:
                alert = TelemetryAlert(device_id=device_id, telemetry_type=telemetry_type, rule_name="freeze_temp", threshold=TEMP_FROZEN_THRESHOLD_C, actual_value=val, message=f"Temperature {val}{unit or '°C'} below freezing {TEMP_FROZEN_THRESHOLD_C}°C", severity="warning")
                db.add(alert)
                alerts.append(alert)

    elif telemetry_type == "humidity":
        val = value if isinstance(value, (int, float)) else None
        if val is not None and val > HUMIDITY_HIGH_THRESHOLD:
            alert = TelemetryAlert(device_id=device_id, telemetry_type=telemetry_type, rule_name="high_humidity", threshold=HUMIDITY_HIGH_THRESHOLD, actual_value=val, message=f"Humidity {val}{unit or '%'} exceeds {HUMIDITY_HIGH_THRESHOLD}%", severity="warning")
            db.add(alert)
            alerts.append(alert)

    elif telemetry_type == "shock":
        val = value if isinstance(value, (int, float)) else None
        if val is not None and val > SHOCK_THRESHOLD_G:
            alert = TelemetryAlert(device_id=device_id, telemetry_type=telemetry_type, rule_name="high_shock", threshold=SHOCK_THRESHOLD_G, actual_value=val, message=f"Shock {val}{unit or 'G'} exceeds {SHOCK_THRESHOLD_G}G", severity="critical")
            db.add(alert)
            alerts.append(alert)

    if alerts:
        await db.commit()
        for alert in alerts:
            try:
                await send_notification(recipient="admin@foodtrack.local", subject=f"Telemetry Alert: {alert.rule_name}", message=alert.message, channel="email")
            except Exception:
                pass

    return reading


async def list_telemetry(
    db: AsyncSession,
    device_id: str | None = None,
    telemetry_type: str | None = None,
    item_id: int | None = None,
    page: int = 1,
):
    q = select(TelemetryReading)
    if device_id:
        q = q.where(TelemetryReading.device_id == device_id)
    if telemetry_type:
        q = q.where(TelemetryReading.telemetry_type == telemetry_type)
    if item_id:
        q = q.where(TelemetryReading.item_id == item_id)
    q = q.order_by(TelemetryReading.recorded_at.desc())

    count_q = select(func.count()).select_from(q.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    rows = (await db.execute(q.offset((page - 1) * PAGE_SIZE).limit(PAGE_SIZE))).scalars().all()
    results = []
    for r in rows:
        results.append({
            "id": r.id,
            "device_id": r.device_id,
            "telemetry_type": r.telemetry_type,
            "value": r.value_float or r.value_str,
            "unit": r.unit,
            "item_id": r.item_id,
            "batch_id": r.batch_id,
            "location": {"lat": r.location_lat, "lng": r.location_lng} if r.location_lat else None,
            "recorded_at": str(r.recorded_at) if r.recorded_at else None,
        })

    return {"readings": results, "total": total, "page": page, "total_pages": max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)}


async def list_alerts(db: AsyncSession, acknowledged: bool | None = None, page: int = 1):
    q = select(TelemetryAlert).order_by(TelemetryAlert.created_at.desc())
    if acknowledged is not None:
        q = q.where(TelemetryAlert.acknowledged == acknowledged)

    count_q = select(func.count()).select_from(q.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    rows = (await db.execute(q.offset((page - 1) * PAGE_SIZE).limit(PAGE_SIZE))).scalars().all()
    results = []
    for r in rows:
        results.append({
            "id": r.id,
            "device_id": r.device_id,
            "telemetry_type": r.telemetry_type,
            "rule_name": r.rule_name,
            "threshold": r.threshold,
            "actual_value": r.actual_value,
            "message": r.message,
            "severity": r.severity,
            "acknowledged": r.acknowledged,
            "created_at": str(r.created_at) if r.created_at else None,
        })

    return {"alerts": results, "total": total, "page": page, "total_pages": max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)}


async def acknowledge_alert(db: AsyncSession, user: User, alert_id: int) -> TelemetryAlert:
    if user.role not in (UserRole.SUPERUSER, UserRole.ADMIN, UserRole.ENTERPRISE):
        raise PermissionError("Insufficient permissions")

    alert = await db.get(TelemetryAlert, alert_id)
    if not alert:
        raise ValueError(f"Alert {alert_id} not found")

    alert.acknowledged = True
    alert.acknowledged_by = user.id
    await db.commit()
    await db.refresh(alert)
    return alert
