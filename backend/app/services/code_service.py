import io
import base64
import hashlib
import uuid
from datetime import datetime, timezone

import qrcode
from barcode import get_barcode_class
from barcode.writer import ImageWriter
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_

from app.config import settings
from app.models.taxonomy import TaxonomyItem, ItemIdentifierLog


def _to_barcode_digits(s: str, length: int = 12) -> str:
    h = hashlib.sha256(s.encode()).hexdigest()[:length]
    return "".join(str(int(c, 16)) for c in h)[:length]


def generate_qr_code(data: str) -> str:
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=10, border=4)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def _sku_to_barcode_num(sku: str) -> str:
    return _to_barcode_digits(sku, 12)


def generate_barcode(sku: str) -> str:
    code = _sku_to_barcode_num(sku)
    cls = get_barcode_class("ean13")
    rv = cls(code, writer=ImageWriter())
    buf = io.BytesIO()
    rv.write(buf)
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def generate_nfc_payload(product_id: int, certificate_id: str | None = None) -> dict:
    payload = {"type": "FoodTrack", "version": "1.0", "product_id": product_id}
    if certificate_id:
        payload["certificate_id"] = certificate_id
    return payload


async def ensure_item_seed(db: AsyncSession, item: TaxonomyItem) -> str:
    if not item.qr_seed:
        item.qr_seed = hashlib.sha256(f"{item.id}-{item.code}-{uuid.uuid4().hex}".encode()).hexdigest()[:16]
        db.add(item)
        await db.flush()
    return item.qr_seed


async def generate_item_qr(db: AsyncSession, item_id: int) -> dict:
    item = await db.get(TaxonomyItem, item_id)
    if not item:
        raise ValueError("Item not found")
    seed = await ensure_item_seed(db, item)
    url = f"{settings.SITE_URL}/verify/{seed}"
    return {
        "item_id": item_id,
        "qr_seed": seed,
        "verify_url": url,
        "qr_image_base64": generate_qr_code(url),
    }


async def generate_item_barcode(db: AsyncSession, item_id: int) -> dict:
    item = await db.get(TaxonomyItem, item_id)
    if not item:
        raise ValueError("Item not found")
    prefix = item.barcode_prefix or item.code
    sku = f"{prefix}-{item_id}"
    return {
        "item_id": item_id,
        "barcode_image_base64": generate_barcode(sku),
    }


async def register_nfc_tag(db: AsyncSession, item_id: int, tag_uid: str, assigned_by: int | None = None) -> dict:
    item = await db.get(TaxonomyItem, item_id)
    if not item:
        raise ValueError("Item not found")
    existing = await db.execute(
        select(ItemIdentifierLog).where(
            ItemIdentifierLog.identifier_value == tag_uid,
            ItemIdentifierLog.is_active == True,
        )
    )
    if existing.scalar_one_or_none():
        raise ValueError("NFC tag UID already registered to another item")

    log = ItemIdentifierLog(
        item_id=item_id,
        identifier_type="nfc",
        identifier_value=tag_uid,
        assigned_by=assigned_by,
    )
    db.add(log)
    await db.commit()
    return {"item_id": item_id, "nfc_uid": tag_uid, "registered": True}


async def resolve_scan(db: AsyncSession, code: str) -> dict:
    log = await db.execute(
        select(ItemIdentifierLog).where(
            ItemIdentifierLog.identifier_value == code,
            ItemIdentifierLog.is_active == True,
        )
    )
    log_entry = log.scalar_one_or_none()
    if log_entry:
        item = await db.get(TaxonomyItem, log_entry.item_id)
        if item:
            return {"type": "nfc", "item_id": item.id, "common_name": item.common_name, "code": item.code}

    item = await db.execute(
        select(TaxonomyItem).where(
            or_(
                TaxonomyItem.qr_seed == code,
                TaxonomyItem.barcode_prefix == code[:len(code)],
            )
        )
    )
    item_row = item.scalar_one_or_none()
    if item_row:
        return {"type": "qr" if item_row.qr_seed == code else "barcode", "item_id": item_row.id, "common_name": item_row.common_name, "code": item_row.code}

    code_clean = code.lstrip("0")[:12]
    item_by_code = await db.execute(
        select(TaxonomyItem).where(TaxonomyItem.code == code_clean)
    )
    item_row2 = item_by_code.scalar_one_or_none()
    if item_row2:
        return {"type": "product_code", "item_id": item_row2.id, "common_name": item_row2.common_name, "code": item_row2.code}

    return {"type": "unknown", "message": "No item found for this scan code"}
