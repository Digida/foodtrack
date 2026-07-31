"""Product service: CRUD, QR/barcode/NFC generation, categorization."""

import json
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.product import Product, ProductCategory
from app.models.user import User, UserRole
from app.services.code_service import generate_qr_code, generate_barcode, generate_nfc_payload


async def create_product(db: AsyncSession, user: User, sku: str, name: str, category: ProductCategory,
                         description: str | None = None, origin_country: str | None = None,
                         origin_region: str | None = None, producer_name: str | None = None,
                         weight_kg: float | None = None, harvest_date: str | None = None,
                         expiry_date: str | None = None, storage_requirements: str | None = None,
                         metadata_json: str | None = None) -> dict:
    if user.role not in (UserRole.SUPERUSER, UserRole.ADMIN, UserRole.ENTERPRISE):
        raise PermissionError("Insufficient permissions")
    existing = await db.execute(select(Product).where(Product.sku == sku))
    if existing.scalar_one_or_none():
        raise ValueError("SKU already exists")
    qr_data = json.dumps({"type": "FoodTrack", "sku": sku, "version": "1.0"})
    qr_b64 = generate_qr_code(qr_data)
    barcode_b64 = generate_barcode(sku)
    product = Product(
        sku=sku, name=name, category=category, description=description,
        origin_country=origin_country, origin_region=origin_region,
        producer_id=user.id, producer_name=producer_name or user.full_name,
        weight_kg=weight_kg, storage_requirements=storage_requirements,
        qr_code=qr_b64, barcode=barcode_b64, metadata_json=metadata_json,
    )
    if harvest_date:
        product.harvest_date = datetime.fromisoformat(harvest_date.replace("Z", "+00:00"))
    if expiry_date:
        product.expiry_date = datetime.fromisoformat(expiry_date.replace("Z", "+00:00"))
    db.add(product)
    await db.commit()
    await db.refresh(product)
    nfc = generate_nfc_payload(product.id)
    return {"product": {"id": product.id, "sku": product.sku, "name": product.name,
                        "category": product.category.value}, "qr_code": qr_b64,
            "barcode": barcode_b64, "nfc_payload": nfc}


async def list_products(db: AsyncSession, skip: int = 0, limit: int = 50,
                        category: ProductCategory | None = None) -> list[dict]:
    query = select(Product).where(Product.is_active == True)
    if category:
        query = query.where(Product.category == category)
    query = query.offset(skip).limit(limit).order_by(Product.created_at.desc())
    result = await db.execute(query)
    return [{"id": p.id, "sku": p.sku, "name": p.name, "category": p.category.value,
             "origin_country": p.origin_country, "producer_name": p.producer_name}
            for p in result.scalars().all()]


async def get_product_detail(db: AsyncSession, product_id: int) -> Product | None:
    result = await db.execute(select(Product).where(Product.id == product_id))
    return result.scalar_one_or_none()


async def get_product_by_sku(db: AsyncSession, sku: str) -> Product | None:
    result = await db.execute(select(Product).where(Product.sku == sku))
    return result.scalar_one_or_none()


async def update_product(db: AsyncSession, user: User, product_id: int, updates: dict) -> Product:
    if user.role not in (UserRole.SUPERUSER, UserRole.ADMIN, UserRole.ENTERPRISE):
        raise PermissionError("Insufficient permissions")
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    if not product:
        raise ValueError("Product not found")
    for field, value in updates.items():
        if value is not None and hasattr(product, field):
            if field in ("harvest_date", "expiry_date") and isinstance(value, str):
                value = datetime.fromisoformat(value.replace("Z", "+00:00"))
            setattr(product, field, value)
    await db.commit()
    return product


async def delete_product(db: AsyncSession, user: User, product_id: int) -> None:
    if user.role not in (UserRole.SUPERUSER, UserRole.ADMIN):
        raise PermissionError("Admin only")
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    if not product:
        raise ValueError("Product not found")
    product.is_active = False
    await db.commit()
