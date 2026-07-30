from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.cargo import CargoRegistration, CargoStatus
from app.models.taxonomy import TaxonomyItem
from app.models.tracking import Shipment, ShipmentBatch
from app.models.certificate import Certificate, CertificateStatus
from app.models.user import User, UserRole


PAGE_SIZE = 20


async def register_cargo(
    db: AsyncSession, user: User, item_id: int, quantity: int,
    origin_location: str | None = None, destination_location: str | None = None,
    mode: str | None = None, unit: str | None = None,
    carrier_name: str | None = None, carrier_ref: str | None = None,
    tracking_number: str | None = None,
    estimated_departure: datetime | None = None,
    estimated_arrival: datetime | None = None,
    weight_kg: float | None = None, volume_m3: float | None = None,
    notes: str | None = None,
):
    if user.role not in (UserRole.ADMIN, UserRole.ENTERPRISE):
        raise PermissionError("Only ADMIN and ENTERPRISE users can register cargo")

    item = await db.get(TaxonomyItem, item_id)
    if not item:
        raise ValueError(f"TaxonomyItem {item_id} not found")

    cargo = CargoRegistration(
        item_id=item_id, quantity=quantity, unit=unit or "units",
        origin_location=origin_location, destination_location=destination_location,
        mode=mode, status=CargoStatus.DRAFT,
        carrier_name=carrier_name, carrier_ref=carrier_ref,
        tracking_number=tracking_number,
        estimated_departure=estimated_departure,
        estimated_arrival=estimated_arrival,
        weight_kg=weight_kg, volume_m3=volume_m3,
        notes=notes, created_by=user.id,
    )
    db.add(cargo)
    await db.commit()
    await db.refresh(cargo)
    return cargo


async def get_cargo_detail(db: AsyncSession, cargo_id: int):
    cargo = await db.get(CargoRegistration, cargo_id)
    if not cargo:
        return None

    item = await db.get(TaxonomyItem, cargo.item_id)
    creator = await db.get(User, cargo.created_by)

    shipments = await db.execute(
        select(Shipment, ShipmentBatch)
        .join(ShipmentBatch, Shipment.id == ShipmentBatch.shipment_id)
        .where(ShipmentBatch.item_id == cargo.item_id)
        .order_by(Shipment.created_at.desc())
        .limit(10)
    )
    shipment_list = []
    for s, sb in shipments.all():
        shipment_list.append({
            "shipment_id": s.id,
            "shipment_number": s.shipment_number,
            "status": s.status.value if hasattr(s.status, 'value') else str(s.status),
            "carrier_name": s.carrier_name,
            "estimated_arrival": str(s.estimated_arrival) if s.estimated_arrival else None,
        })

    return {
        "id": cargo.id,
        "item_id": cargo.item_id,
        "item_name": item.common_name if item else None,
        "item_code": item.code if item else None,
        "quantity": cargo.quantity,
        "unit": cargo.unit,
        "origin_location": cargo.origin_location,
        "destination_location": cargo.destination_location,
        "mode": cargo.mode,
        "status": cargo.status.value if hasattr(cargo.status, 'value') else str(cargo.status),
        "carrier_name": cargo.carrier_name,
        "carrier_ref": cargo.carrier_ref,
        "tracking_number": cargo.tracking_number,
        "estimated_departure": str(cargo.estimated_departure) if cargo.estimated_departure else None,
        "estimated_arrival": str(cargo.estimated_arrival) if cargo.estimated_arrival else None,
        "weight_kg": cargo.weight_kg,
        "volume_m3": cargo.volume_m3,
        "notes": cargo.notes,
        "created_by": creator.email if creator else None,
        "created_at": str(cargo.created_at) if cargo.created_at else None,
        "updated_at": str(cargo.updated_at) if cargo.updated_at else None,
        "linked_shipments": shipment_list,
    }


async def list_cargo_for_item(db: AsyncSession, item_id: int, page: int = 1):
    q = select(CargoRegistration).where(CargoRegistration.item_id == item_id)
    count_q = select(func.count()).select_from(q.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    items = (await db.execute(
        q.order_by(CargoRegistration.created_at.desc())
        .offset((page - 1) * PAGE_SIZE).limit(PAGE_SIZE)
    )).scalars().all()

    results = []
    for c in items:
        results.append({
            "id": c.id,
            "quantity": c.quantity,
            "unit": c.unit,
            "origin_location": c.origin_location,
            "destination_location": c.destination_location,
            "mode": c.mode,
            "status": c.status.value if hasattr(c.status, 'value') else str(c.status),
            "carrier_name": c.carrier_name,
            "tracking_number": c.tracking_number,
            "estimated_arrival": str(c.estimated_arrival) if c.estimated_arrival else None,
            "created_at": str(c.created_at) if c.created_at else None,
        })

    return {"cargo": results, "total": total, "page": page, "total_pages": max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)}


async def update_cargo_status(db: AsyncSession, user: User, cargo_id: int, new_status: CargoStatus):
    if user.role not in (UserRole.ADMIN, UserRole.ENTERPRISE):
        raise PermissionError("Only ADMIN and ENTERPRISE users can update cargo status")

    cargo = await db.get(CargoRegistration, cargo_id)
    if not cargo:
        raise ValueError(f"Cargo {cargo_id} not found")

    valid_transitions = {
        CargoStatus.DRAFT: [CargoStatus.REGISTERED, CargoStatus.CANCELLED],
        CargoStatus.REGISTERED: [CargoStatus.CERTIFIED, CargoStatus.IN_TRANSIT, CargoStatus.CANCELLED],
        CargoStatus.CERTIFIED: [CargoStatus.IN_TRANSIT, CargoStatus.CANCELLED],
        CargoStatus.IN_TRANSIT: [CargoStatus.DELIVERED, CargoStatus.CANCELLED],
        CargoStatus.DELIVERED: [],
        CargoStatus.CANCELLED: [],
    }

    allowed = valid_transitions.get(cargo.status, [])
    if new_status not in allowed:
        raise ValueError(f"Cannot transition from {cargo.status.value} to {new_status.value}")

    cargo.status = new_status
    await db.commit()
    await db.refresh(cargo)
    return cargo


async def get_cargo_certification_status(db: AsyncSession, cargo_id: int):
    cargo = await db.get(CargoRegistration, cargo_id)
    if not cargo:
        return None

    item = await db.get(TaxonomyItem, cargo.item_id)

    certs = await db.execute(
        select(Certificate).where(
            Certificate.item_id == cargo.item_id,
            Certificate.status.in_([CertificateStatus.ISSUED, CertificateStatus.VERIFIED]),
        ).order_by(Certificate.expiry_date.desc())
    )
    certs = certs.scalars().all()

    valid_certs = []
    expired_certs = []
    now = datetime.now(timezone.utc)
    for c in certs:
        entry = {
            "id": c.id,
            "certificate_id": c.certificate_id,
            "certificate_type": c.type.value if hasattr(c.type, 'value') else str(c.type),
            "issuer_name": c.issuer_name,
            "issue_date": str(c.issued_date) if c.issued_date else None,
            "expiry_date": str(c.expiry_date) if c.expiry_date else None,
            "status": c.status.value if hasattr(c.status, 'value') else str(c.status),
        }
        if c.expiry_date and c.expiry_date < now:
            expired_certs.append(entry)
        else:
            valid_certs.append(entry)

    return {
        "cargo_id": cargo_id,
        "item_id": cargo.item_id,
        "item_name": item.common_name if item else None,
        "cargo_status": cargo.status.value if hasattr(cargo.status, 'value') else str(cargo.status),
        "certification_health": "healthy" if valid_certs and not expired_certs else "partial" if valid_certs else "missing",
        "valid_certificates": valid_certs,
        "expired_or_inactive_certificates": expired_certs,
        "total_certificates": len(certs),
        "valid_count": len(valid_certs),
    }
