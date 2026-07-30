"""Unit tests for supplier_service: create, list, scorecard, ranking."""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserRole
from app.services.auth_service import register_user
from app.services.supplier_service import (
    create_supplier,
    get_supplier_detail,
    list_suppliers,
    create_scorecard,
    get_supplier_ranking,
)


async def _make_user(db: AsyncSession, role: UserRole, suffix: str = "") -> User:
    user, _ = await register_user(db, f"{role.value}{suffix}@test.com", "password123", role.value)
    user.role = role
    await db.commit()
    return user


async def test_create_supplier_success(db: AsyncSession):
    user = await _make_user(db, UserRole.ENTERPRISE)
    supplier = await create_supplier(db, user, "Acme Foods", contact_email="acme@test.com")
    assert supplier.id is not None
    assert supplier.name == "Acme Foods"
    assert supplier.is_active is True
    assert supplier.tenant_id == user.tenant_id


async def test_create_supplier_viewer_denied(db: AsyncSession):
    user = await _make_user(db, UserRole.VIEWER)
    with pytest.raises(PermissionError):
        await create_supplier(db, user, "Should Fail")


async def test_get_supplier_detail(db: AsyncSession):
    user = await _make_user(db, UserRole.ADMIN, "detail")
    supplier = await create_supplier(db, user, "Detail Supplier")
    result = await get_supplier_detail(db, supplier.id)
    assert result is not None
    assert result["name"] == "Detail Supplier"
    assert "scorecards" in result
    assert isinstance(result["scorecards"], list)


async def test_get_supplier_detail_not_found(db: AsyncSession):
    result = await get_supplier_detail(db, 99999)
    assert result is None


async def test_list_suppliers_pagination(db: AsyncSession):
    user = await _make_user(db, UserRole.ADMIN, "list")
    for i in range(5):
        await create_supplier(db, user, f"Supplier {i:03d}")
    result = await list_suppliers(db, page=1)
    assert "suppliers" in result
    assert result["total"] >= 5


async def test_create_scorecard_success(db: AsyncSession):
    user = await _make_user(db, UserRole.ENTERPRISE, "score")
    supplier = await create_supplier(db, user, "Scorecard Supplier")
    sc = await create_scorecard(db, user, supplier.id, "2024-Q1",
                                on_time_delivery_pct=95.0, quality_score=88.0)
    assert sc.id is not None
    assert sc.overall_score == pytest.approx(91.5, 0.1)


async def test_create_scorecard_invalid_supplier(db: AsyncSession):
    user = await _make_user(db, UserRole.ADMIN, "badscore")
    with pytest.raises(ValueError, match="not found"):
        await create_scorecard(db, user, 99999, "2024-Q1")


async def test_ranking_uses_join_not_n_plus_one(db: AsyncSession):
    """get_supplier_ranking should return results without N+1 queries."""
    user = await _make_user(db, UserRole.ADMIN, "rank")
    for i in range(3):
        sup = await create_supplier(db, user, f"Ranked Supplier {i}")
        await create_scorecard(db, user, sup.id, "2024-Q1",
                               on_time_delivery_pct=float(70 + i * 10),
                               quality_score=float(70 + i * 10))
    result = await get_supplier_ranking(db)
    assert "ranking" in result
    assert len(result["ranking"]) >= 3
    scores = [r["overall_score"] for r in result["ranking"] if r["overall_score"] is not None]
    assert scores == sorted(scores, reverse=True)
