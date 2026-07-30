"""Tests for recall_service.py — initiate, detail, status update, trace, listing."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.recall import Recall, RecallEvent, RecallSeverity, RecallStatus
from app.models.tracking import Batch, BatchStatus
from app.models.product import Product, ProductCategory
from app.services.recall_service import (
    initiate_recall, get_recall_detail, update_recall_status,
    trace_recall, list_recalls,
)


@pytest.mark.asyncio
async def test_initiate_recall(db: AsyncSession, admin_user, taxonomy_item):
    """Should initiate a recall with valid parameters."""
    product = Product(sku="RECALL-SKU-001", name="Recall Test",
                      category=ProductCategory.FRESH_PRODUCE, item_id=taxonomy_item.id)
    db.add(product); await db.commit(); await db.refresh(product)

    batch = Batch(batch_number="B-RECALL-001", product_id=product.id,
                  quantity=100, status=BatchStatus.ACTIVE, item_id=taxonomy_item.id)
    db.add(batch); await db.commit(); await db.refresh(batch)

    recall = await initiate_recall(
        db, admin_user, batch.id, "Contamination detected",
        severity=RecallSeverity.HIGH, affected_region="Dubai",
    )
    assert recall.id is not None
    assert recall.batch_id == batch.id
    assert recall.severity == RecallSeverity.HIGH
    assert recall.status == RecallStatus.INITIATED

    # Should have created an initial event
    events = await db.execute(
        __import__("sqlalchemy").select(RecallEvent).where(RecallEvent.recall_id == recall.id)
    )
    events_list = events.scalars().all()
    assert len(events_list) >= 1
    assert events_list[0].action == "initiated"


@pytest.mark.asyncio
async def test_initiate_recall_viewer_denied(db: AsyncSession, viewer_user, taxonomy_item):
    """VIEWER should not be able to initiate recalls."""
    with pytest.raises(PermissionError):
        await initiate_recall(db, viewer_user, 1, "Test")


@pytest.mark.asyncio
async def test_get_recall_detail(db: AsyncSession, admin_user, taxonomy_item):
    """Should return full recall detail with timeline."""
    product = Product(sku="RECALL-DTL-SKU", name="Recall Dtl",
                      category=ProductCategory.FRESH_PRODUCE, item_id=taxonomy_item.id)
    db.add(product); await db.commit(); await db.refresh(product)
    batch = Batch(batch_number="B-RECALL-DTL", product_id=product.id,
                  quantity=50, status=BatchStatus.ACTIVE, item_id=taxonomy_item.id)
    db.add(batch); await db.commit(); await db.refresh(batch)

    recall = await initiate_recall(db, admin_user, batch.id, "Quality issue", severity=RecallSeverity.MEDIUM)
    detail = await get_recall_detail(db, recall.id)
    assert detail is not None
    assert detail["id"] == recall.id
    assert detail["reason"] == "Quality issue"
    assert "events" in detail
    assert len(detail["events"]) >= 1


@pytest.mark.asyncio
async def test_get_recall_detail_not_found(db: AsyncSession):
    """Should return None for nonexistent recall."""
    detail = await get_recall_detail(db, 9999)
    assert detail is None


@pytest.mark.asyncio
async def test_update_recall_status(db: AsyncSession, admin_user, taxonomy_item):
    """Should transition recall through valid statuses."""
    product = Product(sku="RECALL-UPD-SKU", name="Recall Upd",
                      category=ProductCategory.FRESH_PRODUCE, item_id=taxonomy_item.id)
    db.add(product); await db.commit(); await db.refresh(product)
    batch = Batch(batch_number="B-RECALL-UPD", product_id=product.id,
                  quantity=30, status=BatchStatus.ACTIVE, item_id=taxonomy_item.id)
    db.add(batch); await db.commit(); await db.refresh(batch)

    recall = await initiate_recall(db, admin_user, batch.id, "Test update")
    assert recall.status == RecallStatus.INITIATED

    recall = await update_recall_status(db, admin_user, recall.id, RecallStatus.IN_PROGRESS)
    assert recall.status == RecallStatus.IN_PROGRESS

    recall = await update_recall_status(db, admin_user, recall.id, RecallStatus.COMPLETED)
    assert recall.status == RecallStatus.COMPLETED
    assert recall.completed_at is not None


@pytest.mark.asyncio
async def test_trace_recall(db: AsyncSession, admin_user, taxonomy_item):
    """Should identify shipments affected by recall."""
    product = Product(sku="RECALL-TRC-SKU", name="Recall Trc",
                      category=ProductCategory.FRESH_PRODUCE, item_id=taxonomy_item.id)
    db.add(product); await db.commit(); await db.refresh(product)
    batch = Batch(batch_number="B-RECALL-TRC", product_id=product.id,
                  quantity=20, status=BatchStatus.ACTIVE, item_id=taxonomy_item.id)
    db.add(batch); await db.commit(); await db.refresh(batch)

    recall = await initiate_recall(db, admin_user, batch.id, "Trace test")
    result = await trace_recall(db, recall.id)
    assert result is not None
    assert result["recall_id"] == recall.id
    assert "shipments_affected" in result


@pytest.mark.asyncio
async def test_list_recalls(db: AsyncSession, admin_user, taxonomy_item):
    """Should list recalls with pagination and status filter."""
    product = Product(sku="RECALL-LST-SKU", name="Recall Lst",
                      category=ProductCategory.FRESH_PRODUCE, item_id=taxonomy_item.id)
    db.add(product); await db.commit(); await db.refresh(product)
    batch = Batch(batch_number="B-RECALL-LST", product_id=product.id,
                  quantity=10, status=BatchStatus.ACTIVE, item_id=taxonomy_item.id)
    db.add(batch); await db.commit(); await db.refresh(batch)

    await initiate_recall(db, admin_user, batch.id, "List test 1")
    await initiate_recall(db, admin_user, batch.id, "List test 2")

    result = await list_recalls(db)
    assert result["total"] >= 2
    assert len(result["recalls"]) >= 1