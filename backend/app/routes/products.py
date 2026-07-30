from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.database import get_db
from app.models.user import User, UserRole
from app.models.product import ProductCategory
from app.services.product_service import (
    create_product, list_products, get_product_detail,
    update_product, delete_product, get_product_by_sku,
)
from app.services.traceability_service import get_product_trace, serialize_event
from app.utils.dependencies import get_current_user

router = APIRouter(prefix="/products", tags=["products"])


class ProductCreateRequest(BaseModel):
    sku: str
    name: str
    category: ProductCategory = ProductCategory.OTHER
    description: str | None = None
    origin_country: str | None = None
    origin_region: str | None = None
    producer_name: str | None = None
    weight_kg: float | None = None
    harvest_date: str | None = None
    expiry_date: str | None = None
    storage_requirements: str | None = None
    metadata_json: str | None = None


class ProductUpdateRequest(BaseModel):
    name: str | None = None
    category: ProductCategory | None = None
    description: str | None = None
    origin_country: str | None = None
    origin_region: str | None = None
    producer_name: str | None = None
    weight_kg: float | None = None
    expiry_date: str | None = None
    storage_requirements: str | None = None
    metadata_json: str | None = None


@router.post("")
async def api_create_product(req: ProductCreateRequest, user: User = Depends(get_current_user),
                              db: AsyncSession = Depends(get_db)):
    try:
        result = await create_product(
            db, user, req.sku, req.name, req.category, req.description,
            req.origin_country, req.origin_region, req.producer_name,
            req.weight_kg, req.harvest_date, req.expiry_date,
            req.storage_requirements, req.metadata_json,
        )
        return result
    except (ValueError, PermissionError) as e:
        raise HTTPException(status_code=400 if isinstance(e, ValueError) else 403, detail=str(e))


@router.get("")
async def api_list_products(
    skip: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200),
    category: ProductCategory | None = None,
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    products = await list_products(db, skip, limit, category)
    return {"products": products, "total": len(products)}


@router.get("/{product_id}")
async def api_get_product(product_id: int, user: User = Depends(get_current_user),
                           db: AsyncSession = Depends(get_db)):
    product = await get_product_detail(db, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    events = await get_product_trace(db, product_id)
    return {
        "product": {
            "id": product.id, "sku": product.sku, "name": product.name,
            "category": product.category.value, "description": product.description,
            "origin_country": product.origin_country, "origin_region": product.origin_region,
            "producer_name": product.producer_name, "weight_kg": product.weight_kg,
            "harvest_date": str(product.harvest_date) if product.harvest_date else None,
            "expiry_date": str(product.expiry_date) if product.expiry_date else None,
            "storage_requirements": product.storage_requirements,
            "qr_code": product.qr_code, "barcode": product.barcode,
            "nfc_tag_id": product.nfc_tag_id, "created_at": str(product.created_at),
        },
        "traceability_events": [serialize_event(e) for e in events],
    }


@router.put("/{product_id}")
async def api_update_product(product_id: int, req: ProductUpdateRequest,
                              user: User = Depends(get_current_user),
                              db: AsyncSession = Depends(get_db)):
    try:
        await update_product(db, user, product_id, req.model_dump(exclude_none=True))
        return {"status": "updated"}
    except (ValueError, PermissionError) as e:
        raise HTTPException(status_code=404 if isinstance(e, ValueError) else 403, detail=str(e))


@router.delete("/{product_id}")
async def api_delete_product(product_id: int, user: User = Depends(get_current_user),
                              db: AsyncSession = Depends(get_db)):
    try:
        await delete_product(db, user, product_id)
        return {"status": "deleted"}
    except (ValueError, PermissionError) as e:
        raise HTTPException(status_code=404 if isinstance(e, ValueError) else 403, detail=str(e))
