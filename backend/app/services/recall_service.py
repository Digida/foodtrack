from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.recall import Recall, RecallEvent, RecallSeverity, RecallStatus
from app.models.tracking import Batch, ShipmentBatch
from app.models.taxonomy import TaxonomyItem
from app.models.user import User, UserRole
from tools.notification_dispatcher import send_notification

PAGE_SIZE = 20


async def initiate_recall(
    db: AsyncSession,
    user: User,
    batch_id: int,
    reason: str,
    severity: RecallSeverity = RecallSeverity.MEDIUM,
    affected_region: str | None = None,
) -> Recall:
    if user.role not in (UserRole.SUPERUSER, UserRole.ADMIN, UserRole.ENTERPRISE):
        raise PermissionError("Only ADMIN and ENTERPRISE can initiate recalls")

    batch = await db.get(Batch, batch_id)
    if not batch:
        raise ValueError(f"Batch {batch_id} not found")

    recall = Recall(
        batch_id=batch_id,
        item_id=batch.item_id,
        reason=reason,
        severity=severity,
        status=RecallStatus.INITIATED,
        affected_region=affected_region,
        created_by=user.id,
    )
    db.add(recall)
    await db.commit()
    await db.refresh(recall)

    event = RecallEvent(recall_id=recall.id, action="initiated", description=f"Recall initiated by {user.email}: {reason}", performed_by=user.id)
    db.add(event)
    await db.commit()

    recipients = await db.execute(
        select(User).where(User.role.in_([UserRole.SUPERUSER, UserRole.ADMIN, UserRole.ENTERPRISE]))
    )
    for recipient in recipients.scalars().all():
        try:
            await send_notification(
                recipient=recipient.email,
                subject=f"Recall Alert: {severity.value} - Batch {batch_id}",
                message=f"Recall initiated: {reason}\nSeverity: {severity.value}\nRegion: {affected_region or 'Global'}",
                channel="email",
            )
        except Exception:
            pass

    return recall


async def get_recall_detail(db: AsyncSession, recall_id: int) -> dict | None:
    recall = await db.get(Recall, recall_id)
    if not recall:
        return None

    events = await db.execute(
        select(RecallEvent).where(RecallEvent.recall_id == recall_id).order_by(RecallEvent.created_at.asc())
    )

    batch = await db.get(Batch, recall.batch_id)
    item = await db.get(TaxonomyItem, recall.item_id) if recall.item_id else None

    return {
        "id": recall.id,
        "batch_id": recall.batch_id,
        "batch_number": batch.batch_number if batch else None,
        "item_id": recall.item_id,
        "item_name": item.common_name if item else None,
        "reason": recall.reason,
        "severity": recall.severity.value if hasattr(recall.severity, "value") else str(recall.severity),
        "status": recall.status.value if hasattr(recall.status, "value") else str(recall.status),
        "affected_region": recall.affected_region,
        "notified_at": str(recall.notified_at) if recall.notified_at else None,
        "completed_at": str(recall.completed_at) if recall.completed_at else None,
        "created_by": recall.created_by,
        "created_at": str(recall.created_at) if recall.created_at else None,
        "events": [{"id": e.id, "action": e.action, "description": e.description, "created_at": str(e.created_at)} for e in events.scalars().all()],
    }


async def update_recall_status(db: AsyncSession, user: User, recall_id: int, new_status: RecallStatus) -> Recall:
    if user.role not in (UserRole.SUPERUSER, UserRole.ADMIN):
        raise PermissionError("Admin access required to update recall status")

    recall = await db.get(Recall, recall_id)
    if not recall:
        raise ValueError(f"Recall {recall_id} not found")

    recall.status = new_status
    if new_status == RecallStatus.COMPLETED:
        recall.completed_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(recall)

    event = RecallEvent(recall_id=recall.id, action=f"status_{new_status.value}", description=f"Status changed to {new_status.value} by {user.email}", performed_by=user.id)
    db.add(event)
    await db.commit()

    return recall


async def trace_recall(db: AsyncSession, recall_id: int) -> dict | None:
    recall = await db.get(Recall, recall_id)
    if not recall:
        return None

    recipients = await db.execute(
        select(ShipmentBatch).where(ShipmentBatch.item_id == recall.item_id)
    )

    return {
        "recall_id": recall_id,
        "item_id": recall.item_id,
        "shipments_affected": [{"shipment_id": sb.shipment_id, "quantity": sb.quantity} for sb in recipients.scalars().all()],
    }


async def list_recalls(db: AsyncSession, page: int = 1, status: str | None = None):
    q = select(Recall).order_by(Recall.created_at.desc())
    if status:
        q = q.where(Recall.status == status)

    count_q = select(func.count()).select_from(q.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    rows = (await db.execute(q.offset((page - 1) * PAGE_SIZE).limit(PAGE_SIZE))).scalars().all()
    results = []
    for r in rows:
        results.append({
            "id": r.id,
            "batch_id": r.batch_id,
            "reason": r.reason[:100],
            "severity": r.severity.value if hasattr(r.severity, "value") else str(r.severity),
            "status": r.status.value if hasattr(r.status, "value") else str(r.status),
            "affected_region": r.affected_region,
            "created_at": str(r.created_at) if r.created_at else None,
        })

    return {"recalls": results, "total": total, "page": page, "total_pages": max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)}
