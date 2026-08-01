"""Tests for cargo_service.py — registration, detail, listing, status transitions, certification status."""

import pytest
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cargo import CargoRegistration, CargoStatus
from app.models.certificate import Certificate, CertificateStatus, CertificateType
from app.services.cargo_service import (
    register_cargo, get_cargo_detail, list_cargo_for_item,
    update_cargo_status, get_cargo_certification_status,
)
from app.models.product import Product, ProductCategory


@pytest.mark.asyncio
async def test_register_cargo(db: AsyncSession, admin_user, taxonomy_item):
    """Should register cargo with valid parameters."""
    cargo = await register_cargo(
        db, admin_user, taxonomy_item.id, quantity=500, unit="kg",
        origin_location="Mombasa", destination_location="Dubai",
        mode="sea_freight", carrier_name="Maersk",
    )
    assert cargo.id is not None
    assert cargo.item_id == taxonomy_item.id
    assert cargo.quantity == 500
    assert cargo.status == CargoStatus.DRAFT


@pytest.mark.asyncio
async def test_register_cargo_viewer_denied(db: AsyncSession, viewer_user, taxonomy_item):
    """VIEWER should not be able to register cargo."""
    with pytest.raises(PermissionError):
        await register_cargo(db, viewer_user, taxonomy_item.id, quantity=10)


@pytest.mark.asyncio
async def test_get_cargo_detail(db: AsyncSession, admin_user, taxonomy_item):
    """Should return full cargo detail with linked shipments."""
    cargo = await register_cargo(db, admin_user, taxonomy_item.id, quantity=100)
    detail = await get_cargo_detail(db, cargo.id)
    assert detail is not None
    assert detail["id"] == cargo.id
    assert detail["item_name"] == taxonomy_item.common_name
    assert "linked_shipments" in detail


@pytest.mark.asyncio
async def test_get_cargo_detail_not_found(db: AsyncSession):
    """Should return None for nonexistent cargo."""
    detail = await get_cargo_detail(db, 9999)
    assert detail is None


@pytest.mark.asyncio
async def test_list_cargo_for_item(db: AsyncSession, admin_user, taxonomy_item):
    """Should list all cargo registrations for an item."""
    await register_cargo(db, admin_user, taxonomy_item.id, quantity=10)
    await register_cargo(db, admin_user, taxonomy_item.id, quantity=20)

    result = await list_cargo_for_item(db, taxonomy_item.id)
    assert result["total"] >= 2
    assert len(result["cargo"]) >= 1


@pytest.mark.asyncio
async def test_update_cargo_status_valid_transition(db: AsyncSession, admin_user, taxonomy_item):
    """Should transition through valid statuses."""
    cargo = await register_cargo(db, admin_user, taxonomy_item.id, quantity=50)
    assert cargo.status == CargoStatus.DRAFT

    # DRAFT -> REGISTERED
    cargo = await update_cargo_status(db, admin_user, cargo.id, CargoStatus.REGISTERED)
    assert cargo.status == CargoStatus.REGISTERED

    # REGISTERED -> CERTIFIED
    cargo = await update_cargo_status(db, admin_user, cargo.id, CargoStatus.CERTIFIED)
    assert cargo.status == CargoStatus.CERTIFIED

    # CERTIFIED -> IN_TRANSIT
    cargo = await update_cargo_status(db, admin_user, cargo.id, CargoStatus.IN_TRANSIT)
    assert cargo.status == CargoStatus.IN_TRANSIT

    # IN_TRANSIT -> DELIVERED
    cargo = await update_cargo_status(db, admin_user, cargo.id, CargoStatus.DELIVERED)
    assert cargo.status == CargoStatus.DELIVERED


@pytest.mark.asyncio
async def test_update_cargo_status_invalid_transition(db: AsyncSession, admin_user, taxonomy_item):
    """Should raise on invalid transitions (e.g., DRAFT -> DELIVERED)."""
    cargo = await register_cargo(db, admin_user, taxonomy_item.id, quantity=30)
    with pytest.raises(ValueError, match="Cannot transition"):
        await update_cargo_status(db, admin_user, cargo.id, CargoStatus.DELIVERED)


@pytest.mark.asyncio
async def test_get_cargo_certification_status(db: AsyncSession, admin_user, taxonomy_item):
    """Should return certification health for cargo's item."""
    cargo = await register_cargo(db, admin_user, taxonomy_item.id, quantity=100)
    await update_cargo_status(db, admin_user, cargo.id, CargoStatus.REGISTERED)

    # Create a valid certificate for the item
    product = Product(sku="TEST-CARGO-SKU", name="Cargo Test Product",
                      category=ProductCategory.FRESH_PRODUCE, item_id=taxonomy_item.id,
                      producer_id=admin_user.id)
    db.add(product); await db.commit(); await db.refresh(product)

    cert = Certificate(
        certificate_id="FT-CARGO-TEST-001", product_id=product.id,
        item_id=taxonomy_item.id, type=CertificateType.HALAL,
        status=CertificateStatus.ISSUED, issuer_id=admin_user.id,
        issuer_name=admin_user.full_name,
    )
    db.add(cert); await db.commit()

    result = await get_cargo_certification_status(db, cargo.id)
    assert result is not None
    assert result["cargo_id"] == cargo.id
    assert result["certification_health"] in ("healthy", "partial", "missing")
    assert "valid_certificates" in result
    assert "expired_or_inactive_certificates" in result