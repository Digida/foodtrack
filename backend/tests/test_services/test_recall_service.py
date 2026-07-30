"""Unit tests for recall_service: initiate, detail, status update, trace, list."""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserRole
from app.models.recall import RecallSeverity, RecallStatus
from app.services.auth_service import register_user
from app.services.recall_service import (
    initiate_recall,
    get_recall_detail,
    update_recall_status,
    list_recalls,
)


async def _setup(db: AsyncSession):
    user, _ = await register_user(db, "recall_admin@test.com", "password123", "Recall Admin")
    user.role = UserRole.ADMIN
    await db.commit()

    # Create a minimal batch so the FK exists
    from app.models.product import Product
    from app.models.taxonomy import TaxonomyItem, TaxonomyNode, Taxonomy
    from app.models.traceability import Batch

    taxonomy = Taxonomy(name="Test Tax")
    db.add(taxonomy)
    await db.commit()
    node = TaxonomyNode(taxonomy_id=taxonomy.id, code="N1", name="Node")
    db.add(node)
    await db.commit()
    item = TaxonomyItem(node_id=node.id, code="ITEM1", common_name="Apple")
    db.add(item)
    product = Product(sku="SKU-001", name="Apple Product", item_id=item.id)
    db.add(product)
    await db.commit()
    batch = Batch(product_id=product.id, batch_code="BATCH-001", quantity=100, unit="kg", created_by=user.id)
    db.add(batch)
    await db.commit()
    await db.refresh(batch)
    return user, batch


async def test_initiate_recall(db: AsyncSession):
    user, batch = await _setup(db)
    recall = await initiate_recall(db, user, batch.id, "Pesticide found", RecallSeverity.HIGH)
    assert recall.id is not None
    assert recall.status == RecallStatus.INITIATED
    assert recall.severity == RecallSeverity.HIGH


async def test_initiate_recall_viewer_denied(db: AsyncSession):
    _, batch = await _setup(db)
    viewer, _ = await register_user(db, "viewer_recall@test.com", "password123", "Viewer")
    viewer.role = UserRole.VIEWER
    await db.commit()
    with pytest.raises(PermissionError):
        await initiate_recall(db, viewer, batch.id, "Reason", RecallSeverity.MEDIUM)


async def test_get_recall_detail(db: AsyncSession):
    user, batch = await _setup(db)
    recall = await initiate_recall(db, user, batch.id, "E. coli", RecallSeverity.CRITICAL)
    detail = await get_recall_detail(db, recall.id)
    assert detail is not None
    assert detail["id"] == recall.id
    assert "events" in detail


async def test_get_recall_detail_not_found(db: AsyncSession):
    result = await get_recall_detail(db, 99999)
    assert result is None


async def test_update_recall_status(db: AsyncSession):
    user, batch = await _setup(db)
    recall = await initiate_recall(db, user, batch.id, "Mold", RecallSeverity.LOW)
    updated = await update_recall_status(db, user, recall.id, RecallStatus.IN_PROGRESS)
    assert updated.status == RecallStatus.IN_PROGRESS


async def test_list_recalls_pagination(db: AsyncSession):
    user, batch = await _setup(db)
    for _ in range(3):
        await initiate_recall(db, user, batch.id, "Test reason", RecallSeverity.MEDIUM)
    result = await list_recalls(db, page=1)
    assert "recalls" in result
    assert result["total"] >= 3


async def test_list_recalls_filter_by_status(db: AsyncSession):
    user, batch = await _setup(db)
    r = await initiate_recall(db, user, batch.id, "Filter test", RecallSeverity.MEDIUM)
    await update_recall_status(db, user, r.id, RecallStatus.COMPLETED)
    result = await list_recalls(db, page=1, status="completed")
    statuses = [rec["status"] for rec in result["recalls"]]
    assert all(s == "completed" for s in statuses)
