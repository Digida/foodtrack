import json
from datetime import datetime, timezone
from typing import Any

from fastapi import WebSocket
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.events import EventLog, WebhookSubscription, WebhookEvent
from app.models.user import User, UserRole
from app.tools.notification_dispatcher import send_notification

_ws_connections: dict[str, list[WebSocket]] = {}


async def publish_event(
    db: AsyncSession,
    user: User,
    event_type: str,
    channel: str,
    payload: dict[str, Any],
) -> dict:
    if user.role not in (UserRole.ADMIN, UserRole.ENTERPRISE):
        raise PermissionError("Only ADMIN and ENTERPRISE can publish events")

    event_log = EventLog(
        event_type=event_type,
        channel=channel,
        payload_json=json.dumps(payload, default=str),
        published_by=user.id,
    )
    db.add(event_log)
    await db.commit()

    msg = json.dumps({"type": event_type, "channel": channel, "payload": payload, "timestamp": str(datetime.now(timezone.utc))}, default=str)

    if channel in _ws_connections:
        stale = []
        for ws in _ws_connections[channel]:
            try:
                await ws.send_text(msg)
            except Exception:
                stale.append(ws)
        for ws in stale:
            _ws_connections[channel].remove(ws)

    await _deliver_webhooks(db, event_type, payload)

    return {"id": event_log.id, "event_type": event_type, "channel": channel, "delivered": True}


async def subscribe_ws(channel: str, websocket: WebSocket):
    if channel not in _ws_connections:
        _ws_connections[channel] = []
    _ws_connections[channel].append(websocket)


async def unsubscribe_ws(channel: str, websocket: WebSocket):
    if channel in _ws_connections:
        try:
            _ws_connections[channel].remove(websocket)
        except ValueError:
            pass


async def _deliver_webhooks(db: AsyncSession, event_type: str, payload: dict):
    subs = await db.execute(
        select(WebhookSubscription).where(
            WebhookSubscription.is_active == True,
        )
    )
    for sub in subs.scalars().all():
        if sub.events:
            subscribed_events = [e.strip() for e in sub.events.split(",")]
            if event_type not in subscribed_events:
                continue
        try:
            await send_notification(
                recipient=sub.url,
                subject=f"FoodTrack Event: {event_type}",
                message=json.dumps(payload, default=str),
                channel="webhook",
            )
        except Exception:
            pass


async def register_webhook(
    db: AsyncSession,
    user: User,
    url: str,
    events: list[str] | None = None,
    secret: str | None = None,
) -> WebhookSubscription:
    if user.role not in (UserRole.ADMIN, UserRole.ENTERPRISE):
        raise PermissionError("Only ADMIN and ENTERPRISE can register webhooks")

    sub = WebhookSubscription(
        url=url,
        secret=secret,
        events=",".join(events) if events else None,
        is_active=True,
        created_by=user.id,
    )
    db.add(sub)
    await db.commit()
    await db.refresh(sub)
    return sub


async def list_webhooks(db: AsyncSession, user: User) -> list[dict]:
    if user.role not in (UserRole.ADMIN, UserRole.ENTERPRISE):
        raise PermissionError("Insufficient permissions")

    subs = await db.execute(
        select(WebhookSubscription).order_by(WebhookSubscription.created_at.desc())
    )
    results = []
    for s in subs.scalars().all():
        results.append({
            "id": s.id,
            "url": s.url,
            "events": s.events.split(",") if s.events else [],
            "is_active": s.is_active,
            "created_at": str(s.created_at) if s.created_at else None,
        })
    return results


async def delete_webhook(db: AsyncSession, user: User, webhook_id: int):
    if user.role != UserRole.ADMIN:
        raise PermissionError("Admin access required")

    sub = await db.get(WebhookSubscription, webhook_id)
    if not sub:
        raise ValueError(f"Webhook {webhook_id} not found")

    await db.delete(sub)
    await db.commit()


async def list_event_logs(db: AsyncSession, page: int = 1, event_type: str | None = None):
    q = select(EventLog)
    if event_type:
        q = q.where(EventLog.event_type == event_type)
    q = q.order_by(EventLog.created_at.desc())

    from sqlalchemy import func
    count_q = select(func.count()).select_from(q.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    rows = (await db.execute(q.offset((page - 1) * 20).limit(20))).scalars().all()
    results = []
    for r in rows:
        results.append({
            "id": r.id,
            "event_type": r.event_type,
            "channel": r.channel,
            "payload": json.loads(r.payload_json) if r.payload_json else None,
            "published_by": r.published_by,
            "created_at": str(r.created_at) if r.created_at else None,
        })

    return {"events": results, "total": total, "page": page, "total_pages": max(1, (total + 20 - 1) // 20)}
