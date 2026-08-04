"""Tests for inventory_service and warehouse_service."""
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select

from app.models.inventory import (
    InventoryMovement,
    ItemInventory,
    MovementReference,
    MovementType,
)
from app.models.taxonomy import TaxonomyItem
from app.models.tracking import Batch, BatchStatus, Warehouse, WarehouseItem
from app.services import inventory_service, warehouse_service


async def _item(db, code="INV-1", common_name="Coconut"):
    from app.models.taxonomy import Taxonomy, TaxonomyNode
    t = Taxonomy(name="Inventory Taxonomy", description="t")
    db.add(t)
    await db.commit()
    await db.refresh(t)
    node = TaxonomyNode(taxonomy_id=t.id, code="N-" + code, name="Node")
    db.add(node)
    await db.commit()
    await db.refresh(node)
    item = TaxonomyItem(node_id=node.id, code=code, common_name=common_name)
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


async def _warehouse(db, code="WH-1", name="Warehouse One"):
    w = Warehouse(code=code, name=name)
    db.add(w)
    await db.commit()
    await db.refresh(w)
    return w


async def _batch(db, num, product_id):
    b = Batch(batch_number=num, product_id=product_id, quantity=10,
              status=BatchStatus.ACTIVE, created_by=1)
    db.add(b)
    await db.commit()
    await db.refresh(b)
    return b


async def _product(db, sku="P-1", name="Coconut Product"):
    from app.models.product import Product
    p = Product(sku=sku, name=name, producer_id=1)
    db.add(p)
    await db.commit()
    await db.refresh(p)
    return p


async def test_get_item_inventory(db):
    item = await _item(db)
    wh = await _warehouse(db)
    db.add(ItemInventory(item_id=item.id, warehouse_id=wh.id, total_quantity=100,
                         available_quantity=80, reserved_quantity=20))
    await db.commit()
    out = await inventory_service.get_item_inventory(db, item.id)
    assert out["total_quantity"] == 100
    assert out["total_available"] == 80
    assert out["total_reserved"] == 20
    assert out["warehouse_count"] == 1
    assert out["warehouses"][0]["warehouse_name"] == "Warehouse One"
    assert await inventory_service.get_item_inventory(db, 99999) is None


async def test_get_item_warehouse_detail(db):
    item = await _item(db)
    wh = await _warehouse(db)
    p = await _product(db)
    b = await _batch(db, "B-INV-1", p.id)
    db.add(ItemInventory(item_id=item.id, warehouse_id=wh.id, total_quantity=50,
                         available_quantity=50, reserved_quantity=0))
    db.add(WarehouseItem(warehouse_id=wh.id, batch_id=b.id, item_id=item.id, quantity=25,
                         location_zone="Z-A", location_rack="R1", location_bin="B1"))
    await db.commit()
    out = await inventory_service.get_item_warehouse_detail(db, item.id, wh.id)
    assert out["warehouse_name"] == "Warehouse One"
    assert out["batches"][0]["batch_number"] == "B-INV-1"
    assert out["batches"][0]["zone"] == "Z-A"
    assert await inventory_service.get_item_warehouse_detail(db, item.id, 99999) is None


async def test_get_movement_history(db):
    item = await _item(db)
    wh = await _warehouse(db)
    db.add(InventoryMovement(item_id=item.id, warehouse_id=wh.id,
                             movement_type=MovementType.INBOUND, quantity=10, notes="first"))
    db.add(InventoryMovement(item_id=item.id, warehouse_id=wh.id,
                             movement_type=MovementType.OUTBOUND, quantity=3, notes="second",
                             moved_at=datetime.now(timezone.utc) + timedelta(days=2)))
    await db.commit()
    out = await inventory_service.get_movement_history(db, item.id)
    assert out["total"] == 2
    assert out["total_pages"] == 1
    types = {m["movement_type"] for m in out["movements"]}
    assert types == {"inbound", "outbound"}
    assert out["movements"][0]["warehouse_name"] == "Warehouse One"
    out_days = await inventory_service.get_movement_history(db, item.id, days=1)
    assert out_days["total"] == 1


async def test_record_movement_inbound_creates_inventory(db, admin_user):
    item = await _item(db)
    wh = await _warehouse(db)
    mv = await inventory_service.record_movement(
        db, admin_user, item.id, MovementType.INBOUND, 30, warehouse_id=wh.id, notes="stock")
    assert mv.movement_type == MovementType.INBOUND
    inv = (await db.execute(select(ItemInventory).where(ItemInventory.item_id == item.id))).scalar_one()
    assert inv.total_quantity == 30
    assert inv.available_quantity == 30


async def test_record_movement_outbound_and_floor(db, admin_user):
    item = await _item(db)
    wh = await _warehouse(db)
    await inventory_service.record_movement(db, admin_user, item.id, MovementType.INBOUND, 10, warehouse_id=wh.id)
    await inventory_service.record_movement(db, admin_user, item.id, MovementType.OUTBOUND, 25, warehouse_id=wh.id)
    inv = (await db.execute(select(ItemInventory).where(ItemInventory.item_id == item.id))).scalar_one()
    assert inv.total_quantity == 0


async def test_record_movement_adjustment_and_writeoff(db, admin_user):
    item = await _item(db)
    wh = await _warehouse(db)
    await inventory_service.record_movement(db, admin_user, item.id, MovementType.ADJUSTMENT, 5, warehouse_id=wh.id)
    inv = (await db.execute(select(ItemInventory).where(ItemInventory.item_id == item.id))).scalar_one()
    assert inv.total_quantity == 5
    await inventory_service.record_movement(db, admin_user, item.id, MovementType.WRITE_OFF, 2, warehouse_id=wh.id)
    await db.refresh(inv)
    assert inv.total_quantity == 3


async def test_record_movement_transfer_no_change(db, admin_user):
    item = await _item(db)
    wh = await _warehouse(db)
    await inventory_service.record_movement(db, admin_user, item.id, MovementType.TRANSFER, 9, warehouse_id=wh.id)
    inv = (await db.execute(select(ItemInventory).where(ItemInventory.item_id == item.id))).scalar_one()
    assert inv.total_quantity == 0


async def test_record_movement_denied_for_viewer(db, viewer_user):
    await inventory_service.record_movement(db, None, 1, MovementType.INBOUND, 1)
    try:
        await inventory_service.record_movement(db, viewer_user, 1, MovementType.INBOUND, 1)
        assert False
    except PermissionError:
        pass


async def test_record_movement_reference_and_user(db, admin_user):
    item = await _item(db)
    wh = await _warehouse(db)
    mv = await inventory_service.record_movement(
        db, admin_user, item.id, MovementType.INBOUND, 7, warehouse_id=wh.id,
        batch_id=1, reference_type=MovementReference.SHIPMENT, reference_id=42)
    assert mv.reference_id == 42
    assert mv.reference_type == MovementReference.SHIPMENT
    assert mv.moved_by == admin_user.id


async def test_reconcile_from_warehouse_items_existing(db):
    item = await _item(db)
    wh = await _warehouse(db)
    p = await _product(db)
    b = await _batch(db, "B-REC", p.id)
    db.add(WarehouseItem(warehouse_id=wh.id, batch_id=b.id, item_id=item.id, quantity=60))
    db.add(ItemInventory(item_id=item.id, warehouse_id=wh.id, total_quantity=10,
                         available_quantity=10, reserved_quantity=0))
    await db.commit()
    inv = await inventory_service.reconcile_from_warehouse_items(db, item.id, wh.id)
    assert inv.total_quantity == 60
    mv = (await db.execute(select(InventoryMovement).where(InventoryMovement.item_id == item.id))).scalar_one()
    assert mv.movement_type == MovementType.ADJUSTMENT
    assert mv.quantity == 50


async def test_reconcile_from_warehouse_items_new(db):
    item = await _item(db)
    wh = await _warehouse(db)
    p = await _product(db)
    b = await _batch(db, "B-REC2", p.id)
    db.add(WarehouseItem(warehouse_id=wh.id, batch_id=b.id, item_id=item.id, quantity=15))
    await db.commit()
    inv = await inventory_service.reconcile_from_warehouse_items(db, item.id, wh.id)
    assert inv.total_quantity == 15


async def test_transfer_between_warehouses(db, admin_user):
    item = await _item(db)
    wh_a = await _warehouse(db, "WH-A")
    wh_b = await _warehouse(db, "WH-B")
    db.add(ItemInventory(item_id=item.id, warehouse_id=wh_a.id, total_quantity=100,
                         available_quantity=100, reserved_quantity=0))
    await db.commit()
    res = await inventory_service.transfer_between_warehouses(db, admin_user, item.id, wh_a.id, wh_b.id, 40)
    assert res["quantity"] == 40
    inv_a = (await db.execute(select(ItemInventory).where(
        ItemInventory.item_id == item.id, ItemInventory.warehouse_id == wh_a.id))).scalar_one()
    inv_b = (await db.execute(select(ItemInventory).where(
        ItemInventory.item_id == item.id, ItemInventory.warehouse_id == wh_b.id))).scalar_one()
    assert inv_a.total_quantity == 60
    assert inv_b.total_quantity == 40
    mv_count = (await db.execute(select(func.count()).select_from(InventoryMovement))).scalar()
    assert mv_count == 2


async def test_transfer_between_warehouses_insufficient(db, admin_user):
    item = await _item(db)
    wh_a = await _warehouse(db, "WH-A2")
    wh_b = await _warehouse(db, "WH-B2")
    db.add(ItemInventory(item_id=item.id, warehouse_id=wh_a.id, total_quantity=5,
                         available_quantity=5, reserved_quantity=0))
    await db.commit()
    try:
        await inventory_service.transfer_between_warehouses(db, admin_user, item.id, wh_a.id, wh_b.id, 50)
        assert False
    except ValueError:
        pass


async def test_transfer_between_warehouses_denied(db, viewer_user):
    item = await _item(db)
    try:
        await inventory_service.transfer_between_warehouses(db, viewer_user, item.id, 1, 2, 1)
        assert False
    except PermissionError:
        pass


async def test_get_warehouse_items_and_summary(db):
    item = await _item(db)
    wh = await _warehouse(db)
    db.add(ItemInventory(item_id=item.id, warehouse_id=wh.id, total_quantity=25,
                         available_quantity=20, reserved_quantity=5))
    await db.commit()
    out = await inventory_service.get_warehouse_items(db, wh.id)
    assert out["total"] == 1
    assert out["items"][0]["item_name"] == "Coconut"
    summary = await inventory_service.get_inventory_summary(db)
    assert summary["total_items"] == 1
    assert summary["total_warehouses"] == 1
    assert summary["total_quantity"] == 25
    assert summary["total_available"] == 20


async def test_warehouse_crud(db, admin_user, viewer_user):
    w = await warehouse_service.create_warehouse(db, admin_user, "WH-CRUD", "Crud Warehouse",
                                                 city="Dubai", country="AE", capacity_items=1000,
                                                 temperature_celsius=4.0, humidity_percent=85.0)
    assert w.code == "WH-CRUD"
    listed = await warehouse_service.list_warehouses(db)
    assert listed["total"] == 1
    assert listed["warehouses"][0]["capacity_items"] == 1000
    detail = await warehouse_service.get_warehouse(db, w.id)
    assert detail["name"] == "Crud Warehouse"
    updated = await warehouse_service.update_warehouse(db, admin_user, w.id, {"name": "Renamed WH"})
    assert updated.name == "Renamed WH"
    try:
        await warehouse_service.create_warehouse(db, admin_user, "WH-CRUD", "dup")
        assert False
    except ValueError:
        pass


async def test_warehouse_permission_errors(db, viewer_user, admin_user):
    try:
        await warehouse_service.create_warehouse(db, viewer_user, "WH-X", "X")
        assert False
    except PermissionError:
        pass
    try:
        await warehouse_service.update_warehouse(db, viewer_user, 1, {})
        assert False
    except PermissionError:
        pass
    try:
        await warehouse_service.delete_warehouse(db, viewer_user, 1)
        assert False
    except PermissionError:
        pass
    try:
        await warehouse_service.delete_warehouse(db, admin_user, 99999)
        assert False
    except ValueError:
        pass
    try:
        await warehouse_service.update_warehouse(db, admin_user, 99999, {})
        assert False
    except ValueError:
        pass


async def test_warehouse_add_and_update_items(db, admin_user):
    w = await warehouse_service.create_warehouse(db, admin_user, "WH-IT", "Item WH")
    p = await _product(db, "P-WH")
    b = await _batch(db, "B-WHIT", p.id)
    wi = await warehouse_service.add_warehouse_item(db, admin_user, w.id, b.id, 10, zone="Z1", rack="R1")
    assert wi.quantity == 10
    wi2 = await warehouse_service.add_warehouse_item(db, admin_user, w.id, b.id, 5, zone="Z1", rack="R1")
    assert wi2.quantity == 15
    wi3 = await warehouse_service.add_warehouse_item(db, admin_user, w.id, b.id, 3, zone="Z2")
    assert wi3.quantity == 3
    up = await warehouse_service.update_warehouse_item(db, admin_user, wi3.id, {"quantity": 8, "location_bin": "B9"})
    assert up.quantity == 8
    detail = await warehouse_service.get_warehouse(db, w.id)
    assert len(detail["items"]) == 2


async def test_warehouse_add_item_errors(db, admin_user):
    w = await warehouse_service.create_warehouse(db, admin_user, "WH-ERR", "Err WH")
    try:
        await warehouse_service.add_warehouse_item(db, admin_user, w.id, 99999, 1)
        assert False
    except ValueError:
        pass
    try:
        await warehouse_service.add_warehouse_item(db, admin_user, 99999, 1, 1)
        assert False
    except ValueError:
        pass
    try:
        await warehouse_service.update_warehouse_item(db, admin_user, 99999, {})
        assert False
    except ValueError:
        pass


async def test_warehouse_delete_and_remove_items(db, admin_user):
    w = await warehouse_service.create_warehouse(db, admin_user, "WH-DEL", "Delete WH")
    p = await _product(db, "P-DEL")
    b = await _batch(db, "B-DEL", p.id)
    wi = await warehouse_service.add_warehouse_item(db, admin_user, w.id, b.id, 4)
    await warehouse_service.remove_warehouse_item(db, admin_user, wi.id)
    assert await db.get(WarehouseItem, wi.id) is None
    await warehouse_service.delete_warehouse(db, admin_user, w.id)
    w2 = await db.get(Warehouse, w.id)
    assert w2.is_active is False
    try:
        await warehouse_service.remove_warehouse_item(db, admin_user, 99999)
        assert False
    except ValueError:
        pass
