"""Tests for shipping_service and batch_service."""
from app.models.product import Product
from app.models.tracking import (
    Batch,
    BatchStatus,
    Shipment,
    ShipmentBatch,
    ShipmentMode,
    ShipmentStatus,
    Warehouse,
)
from app.services import batch_service, shipping_service


async def _warehouse(db, code="WH-O", name="Origin WH"):
    w = Warehouse(code=code, name=name)
    db.add(w)
    await db.commit()
    await db.refresh(w)
    return w


async def _product(db, sku="P-SHIP-1", name="Shipping Product"):
    p = Product(sku=sku, name=name, producer_id=1)
    db.add(p)
    await db.commit()
    await db.refresh(p)
    return p


async def _batch(db, num="B-SHIP-1", product_id=None):
    b = Batch(batch_number=num, product_id=product_id, quantity=100,
              status=BatchStatus.ACTIVE, created_by=1)
    db.add(b)
    await db.commit()
    await db.refresh(b)
    return b


async def _shipment(db, admin_user, num="SHP-1", origin=None, dest=None):
    return await shipping_service.create_shipment(
        db, admin_user, num, ShipmentMode.COURIER, origin_id=origin.id if origin else None,
        destination_id=dest.id if dest else None, carrier_name="DHL",
        courier_tracking_code="TRK-1", estimated_departure="2024-06-01T10:00:00Z",
        estimated_arrival="2024-06-05T10:00:00Z", total_weight_kg=100.5,
        total_volume_m3=2.0, notes="Test shipment")


async def test_create_and_list_shipments(db, admin_user):
    w = await _warehouse(db)
    s = await _shipment(db, admin_user, origin=w, dest=w)
    assert s.status == ShipmentStatus.CREATED
    assert s.carrier_name == "DHL"
    listed = await shipping_service.list_shipments(db)
    assert listed["total"] == 1
    assert listed["shipments"][0]["carrier_name"] == "DHL"
    assert listed["shipments"][0]["origin_name"] == "Origin WH"
    assert listed["shipments"][0]["tracking_count"] == 0
    try:
        await shipping_service.create_shipment(db, admin_user, "SHP-1", ShipmentMode.COURIER)
        assert False
    except ValueError:
        pass


async def test_list_shipments_filters(db, admin_user):
    w = await _warehouse(db)
    await _shipment(db, admin_user, "SHP-F1", origin=w)
    await _shipment(db, admin_user, "SHP-F2", origin=w)
    listed = await shipping_service.list_shipments(db, status="created", mode="courier")
    assert listed["total"] == 2
    listed2 = await shipping_service.list_shipments(db, status="delivered")
    assert listed2["total"] == 0


async def test_get_shipment_full(db, admin_user):
    w = await _warehouse(db)
    s = await _shipment(db, admin_user, origin=w, dest=w)
    p = await _product(db)
    b = await _batch(db, "B-FULL", p.id)
    await shipping_service.add_batch_to_shipment(db, admin_user, s.id, b.id, 60)
    await shipping_service.add_shipment_tracking_event(
        db, admin_user, s.id, "in_transit", location_name="Jebel Ali",
        message="Departed", carrier_status="departed", event_timestamp="2024-06-02T08:00:00Z")
    detail = await shipping_service.get_shipment(db, s.id)
    assert len(detail["batches"]) == 1
    assert detail["batches"][0]["quantity"] == 60
    assert len(detail["tracking_events"]) == 1
    assert detail["tracking_events"][0]["status"] == "in_transit"
    assert detail["origin"]["name"] == "Origin WH"
    assert detail["status"] == "in_transit"
    assert await shipping_service.get_shipment(db, 99999) is None


async def test_update_shipment(db, admin_user):
    w = await _warehouse(db)
    s = await _shipment(db, admin_user, origin=w)
    up = await shipping_service.update_shipment(db, admin_user, s.id, {
        "carrier_name": "FedEx", "actual_departure": "2024-06-01T11:00:00Z"})
    assert up.carrier_name == "FedEx"
    assert up.actual_departure is not None


async def test_shipment_errors(db, admin_user, viewer_user):
    w = await _warehouse(db)
    s = await _shipment(db, admin_user, origin=w)
    p = await _product(db)
    b = await _batch(db, "B-ERR", p.id)
    try:
        await shipping_service.add_batch_to_shipment(db, admin_user, 99999, b.id, 1)
        assert False
    except ValueError:
        pass
    try:
        await shipping_service.add_batch_to_shipment(db, admin_user, s.id, 99999, 1)
        assert False
    except ValueError:
        pass
    try:
        await shipping_service.add_shipment_tracking_event(db, admin_user, 99999, "x")
        assert False
    except ValueError:
        pass
    try:
        await shipping_service.add_shipment_tracking_event(db, viewer_user, s.id, "x")
        assert False
    except PermissionError:
        pass
    try:
        await shipping_service.update_shipment(db, admin_user, 99999, {})
        assert False
    except ValueError:
        pass


async def test_delete_shipment_admin_only(db, admin_user, enterprise_user):
    w = await _warehouse(db)
    s = await _shipment(db, admin_user, origin=w)
    await shipping_service.delete_shipment(db, admin_user, s.id)
    assert await db.get(Shipment, s.id) is None
    s2 = await _shipment(db, admin_user, "SHP-DEL", origin=w)
    try:
        await shipping_service.delete_shipment(db, enterprise_user, s2.id)
        assert False
    except PermissionError:
        pass
    try:
        await shipping_service.delete_shipment(db, admin_user, 99999)
        assert False
    except ValueError:
        pass


async def test_batch_crud(db, admin_user, enterprise_user):
    p = await _product(db)
    b = await batch_service.create_batch(db, admin_user, "B-CRUD", p.id, quantity=200,
                                         serial_number="SN-1", manufacturer_part_number="MPN-1",
                                         production_date="2024-01-15", expiry_date="2025-01-15",
                                         notes="Batch notes")
    assert b.batch_number == "B-CRUD"
    assert b.status == BatchStatus.ACTIVE
    detail = await batch_service.get_batch(db, b.id)
    assert detail["product_name"] == "Shipping Product"
    assert detail["serial_number"] == "SN-1"
    assert detail["production_date"].startswith("2024")
    listed = await batch_service.list_batches(db)
    assert listed["total"] == 1
    listed2 = await batch_service.list_batches(db, status="active", product_id=p.id)
    assert listed2["total"] == 1
    up = await batch_service.update_batch(db, admin_user, b.id, {"quantity": 300, "expiry_date": "2026-01-01"})
    assert up.quantity == 300
    assert await batch_service.get_batch(db, 99999) is None


async def test_batch_locations(db, admin_user):
    p = await _product(db)
    b = await batch_service.create_batch(db, admin_user, "B-LOC", p.id, quantity=50)
    w = Warehouse(code="WH-LOC", name="Location WH")
    db.add(w)
    await db.commit()
    await db.refresh(w)
    from app.models.tracking import WarehouseItem
    db.add(WarehouseItem(warehouse_id=w.id, batch_id=b.id, item_id=None, quantity=10,
                         location_zone="Z1", location_rack="R2", location_bin="B3"))
    await db.commit()
    detail = await batch_service.get_batch(db, b.id)
    assert detail["locations"][0]["warehouse_name"] == "Location WH"
    assert detail["locations"][0]["zone"] == "Z1"
    listed = await batch_service.list_batches(db)
    assert listed["batches"][0]["locations"][0]["rack"] == "R2"


async def test_batch_errors(db, admin_user):
    try:
        await batch_service.create_batch(db, admin_user, "B-X", 99999)
        assert False
    except ValueError:
        pass
    p = await _product(db, "P-ERR")
    await batch_service.create_batch(db, admin_user, "B-ERR", p.id)
    try:
        await batch_service.create_batch(db, admin_user, "B-ERR", p.id)
        assert False
    except ValueError:
        pass
    try:
        await batch_service.update_batch(db, admin_user, 99999, {})
        assert False
    except ValueError:
        pass
    try:
        await batch_service.delete_batch(db, admin_user, 99999)
        assert False
    except ValueError:
        pass


async def test_batch_permissions(db, viewer_user, admin_user):
    p = await _product(db, "P-PERM")
    try:
        await batch_service.create_batch(db, viewer_user, "B-PERM", p.id)
        assert False
    except PermissionError:
        pass
    b = await batch_service.create_batch(db, admin_user, "B-PERM2", p.id)
    await batch_service.delete_batch(db, admin_user, b.id)
    b2 = await db.get(Batch, b.id)
    assert b2.status == BatchStatus.RECALLED


async def test_shipment_batch_status_default(db, admin_user):
    w = await _warehouse(db)
    s = await _shipment(db, admin_user, origin=w)
    p = await _product(db, "P-DEF")
    b = await _batch(db, "B-DEF", p.id)
    sb = ShipmentBatch(shipment_id=s.id, batch_id=b.id, quantity=5)
    db.add(sb)
    await db.commit()
    assert sb.item_shipment_status.value == "pending"
