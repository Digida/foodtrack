"""Earning & opportunity service (public browse).

Exposes pipeline-generated earning opportunities to unauthenticated users so
they can discover work — member jobs (clerks, verifiers, packers, certifiers,
couriers), courier/bulking deliver jobs and open supply aggregation campaigns.

Everything here is intentionally READ-ONLY and public. Participation requires
authentication, which is enforced at the action endpoints (existing commerce
routes require auth). No schema changes are introduced — we reuse the existing
bulking pipeline tables.
"""
from datetime import datetime, timezone
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.commerce import (
    BulkingRegister, RegisterStatus,
    CourierJob, CourierJobStatus,
    BulkingJobAssignment, BulkingJobStatus,
)
from app.models.taxonomy import TaxonomyItem

PAGE_SIZE = 20


def _enum_value(value):
    return value.value if hasattr(value, "value") else str(value)


def _item_summary(item: TaxonomyItem | None) -> dict:
    if item is None:
        return {}
    band = item.supply_band
    if hasattr(band, "value"):
        band = band.value
    return {
        "item_id": item.id,
        "item_code": item.code,
        "item_name": item.common_name,
        "supply_band": band,
    }


def _register_light(r: BulkingRegister, item: TaxonomyItem | None = None) -> dict:
    return {
        "id": r.id,
        "register_number": r.register_number,
        "title": r.title,
        **(_item_summary(item) if item is not None else {}),
        "target_quantity": r.target_quantity,
        "unit": r.unit,
        "target_price": r.target_price,
        "currency": r.currency,
        "region": r.region,
        "status": _enum_value(r.status),
        "created_at": str(r.created_at) if r.created_at else None,
    }


def _job_out(j: BulkingJobAssignment, register: BulkingRegister | None = None,
             item: TaxonomyItem | None = None) -> dict:
    return {
        "id": j.id,
        "type": "pipeline_job",
        "role": _enum_value(j.role),
        "assignee_name": j.assignee_name,
        "assignee_id": j.assignee_id,
        "assignee_location": j.assignee_location,
        "status": _enum_value(j.status),
        "notes": j.notes,
        "assigned_at": str(j.assigned_at) if j.assigned_at else None,
        "register": _register_light(register, item) if register is not None else None,
        "item": _item_summary(item) if item is not None else None,
    }


def _courier_out(j: CourierJob, register: BulkingRegister | None = None,
                 item: TaxonomyItem | None = None) -> dict:
    return {
        "id": j.id,
        "type": "courier_job",
        "pickup_location": j.pickup_location,
        "dropoff_warehouse_id": j.dropoff_warehouse_id,
        "deliver_to_buyer": bool(j.deliver_to_buyer),
        "quantity": j.quantity,
        "unit": j.unit,
        "weight_kg": j.weight_kg,
        "budget": j.budget,
        "currency": j.currency,
        "courier_name": j.courier_name,
        "tracking_code": j.tracking_code,
        "status": _enum_value(j.status),
        "posted_at": str(j.posted_at) if j.posted_at else None,
        "register": _register_light(register, item) if register is not None else None,
        "item": _item_summary(item) if item is not None else None,
    }


def _supply_out(r: BulkingRegister, item: TaxonomyItem | None = None) -> dict:
    return {
        "id": r.id,
        "type": "supply_opportunity",
        "register_number": r.register_number,
        "title": r.title,
        "region": r.region,
        "sourcing_mode": _enum_value(r.sourcing_mode) if hasattr(r, "sourcing_mode") else None,
        "sourcing_entity_name": r.sourcing_entity_name,
        "target_quantity": r.target_quantity,
        "unit": r.unit,
        "target_price": r.target_price,
        "currency": r.currency,
        "status": _enum_value(r.status),
        "created_at": str(r.created_at) if r.created_at else None,
        "item": _item_summary(item) if item is not None else None,
    }


async def list_earning_opportunities(
    db: AsyncSession,
    page: int = 1,
    kind: str | None = None,
) -> dict:
    """Public read-only list of earning opportunities from the pipelines.

    `kind` may be one of: `pipeline_job`, `courier_job`, `supply`.
    Only OPEN opportunities are exposed (active jobs, posted/assigned courier
    jobs, and non-closed registers).
    """
    page = max(1, page)
    opportunities: list[dict] = []

    if kind in (None, "pipeline_job"):
        jobs = (await db.execute(
            select(BulkingJobAssignment)
            .where(BulkingJobAssignment.status.in_([
                BulkingJobStatus.ASSIGNED, BulkingJobStatus.IN_PROGRESS,
            ]))
            .order_by(BulkingJobAssignment.created_at.desc())
            .limit(200)
        )).scalars().all()
        # Light-weight: batch fetch registers+items per job to avoid N+1
        reg_ids = {j.register_id for j in jobs}
        regs = {}
        if reg_ids:
            rows = (await db.execute(
                select(BulkingRegister).where(BulkingRegister.id.in_(reg_ids))
            )).scalars().all()
            regs = {r.id: r for r in rows}
        item_ids = {r.item_id for r in regs.values()}
        items = {}
        if item_ids:
            irows = (await db.execute(
                select(TaxonomyItem).where(TaxonomyItem.id.in_(item_ids))
            )).scalars().all()
            items = {i.id: i for i in irows}
        for j in jobs:
            reg = regs.get(j.register_id)
            item = items.get(reg.item_id) if reg else None
            opportunities.append(_job_out(j, reg, item))

    if kind in (None, "courier_job"):
        couriers = (await db.execute(
            select(CourierJob)
            .where(CourierJob.status.in_([
                CourierJobStatus.POSTED, CourierJobStatus.ASSIGNED,
                CourierJobStatus.IN_TRANSIT,
            ]))
            .order_by(CourierJob.created_at.desc())
            .limit(200)
        )).scalars().all()
        reg_ids = {c.register_id for c in couriers}
        regs = {}
        if reg_ids:
            rows = (await db.execute(
                select(BulkingRegister).where(BulkingRegister.id.in_(reg_ids))
            )).scalars().all()
            regs = {r.id: r for r in rows}
        item_ids = {r.item_id for r in regs.values()}
        items = {}
        if item_ids:
            irows = (await db.execute(
                select(TaxonomyItem).where(TaxonomyItem.id.in_(item_ids))
            )).scalars().all()
            items = {i.id: i for i in irows}
        for c in couriers:
            reg = regs.get(c.register_id)
            item = items.get(reg.item_id) if reg else None
            opportunities.append(_courier_out(c, reg, item))

    if kind in (None, "supply"):
        regs = (await db.execute(
            select(BulkingRegister)
            .where(BulkingRegister.status.in_([
                RegisterStatus.SOURCING, RegisterStatus.AGGREGATED,
            ]))
            .order_by(BulkingRegister.created_at.desc())
            .limit(200)
        )).scalars().all()
        item_ids = {r.item_id for r in regs}
        items = {}
        if item_ids:
            irows = (await db.execute(
                select(TaxonomyItem).where(TaxonomyItem.id.in_(item_ids))
            )).scalars().all()
            items = {i.id: i for i in irows}
        for r in regs:
            opportunities.append(_supply_out(r, items.get(r.item_id)))

    # Sort newest first, stable
    opportunities.sort(
        key=lambda o: o.get("created_at") or o.get("assigned_at") or o.get("posted_at") or "",
        reverse=True,
    )
    total = len(opportunities)
    start = (page - 1) * PAGE_SIZE
    rows = opportunities[start:start + PAGE_SIZE]

    return {
        "opportunities": rows,
        "total": total,
        "page": page,
        "total_pages": max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE),
    }