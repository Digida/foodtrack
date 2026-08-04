import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.taxonomy import (
    TaxonomySuggestion, TaxonomyItem, TaxonomyNode,
    ItemName, ItemAttribute, SuggestionStatus,
)
from app.models.user import User

# Item fields a `field`-kind suggestion may target. Intentionally excludes
# identity/immutable fields (code, node_id, is_active, timestamps).
FIELD_KINDS = {
    "scientific_name", "genre", "phylum", "tax_class", "order_name",
    "family", "gestation_period", "gestation_unit", "local_uses",
    "description", "image_url",
}

VALID_KINDS = {"name", "attribute", "field", "missing_item"}


async def create_suggestion(
    db: AsyncSession,
    user: User,
    *,
    kind: str,
    value: str,
    item_id: int | None = None,
    node_id: int | None = None,
    language: str | None = None,
    key: str | None = None,
    unit: str | None = None,
) -> TaxonomySuggestion:
    if kind not in VALID_KINDS:
        raise ValueError(f"Unknown suggestion kind: {kind}")
    if not value or not value.strip():
        raise ValueError("value is required")

    if kind in ("name", "attribute", "field"):
        if not item_id:
            raise ValueError("item_id is required for this suggestion kind")
        item = await db.get(TaxonomyItem, item_id)
        if not item:
            raise ValueError("Item not found")
        if kind == "name" and not language:
            raise ValueError("language is required for name suggestions")
        if kind in ("attribute", "field") and not key:
            raise ValueError("key is required for this suggestion kind")
        if kind == "field" and key not in FIELD_KINDS:
            raise ValueError(f"Field '{key}' cannot be suggested")
    elif kind == "missing_item":
        if not node_id:
            raise ValueError("node_id is required for missing-item suggestions")
        node = await db.get(TaxonomyNode, node_id)
        if not node:
            raise ValueError("Category not found")

    suggestion = TaxonomySuggestion(
        item_id=item_id,
        node_id=node_id,
        kind=kind,
        language=language,
        key=key,
        value=value.strip(),
        unit=unit,
        status=SuggestionStatus.PENDING,
        suggested_by=user.id,
    )
    db.add(suggestion)
    await db.commit()
    await db.refresh(suggestion)
    return suggestion


async def get_suggestion(db: AsyncSession, suggestion_id: int) -> TaxonomySuggestion | None:
    return await db.get(TaxonomySuggestion, suggestion_id)


async def list_suggestions(
    db: AsyncSession,
    status: str | None = None,
    item_id: int | None = None,
) -> list[TaxonomySuggestion]:
    q = select(TaxonomySuggestion).order_by(TaxonomySuggestion.created_at.desc())
    if status:
        q = q.where(TaxonomySuggestion.status == status)
    if item_id:
        q = q.where(TaxonomySuggestion.item_id == item_id)
    result = await db.execute(q)
    return list(result.scalars().all())


async def list_my_suggestions(db: AsyncSession, user_id: int) -> list[TaxonomySuggestion]:
    result = await db.execute(
        select(TaxonomySuggestion)
        .where(TaxonomySuggestion.suggested_by == user_id)
        .order_by(TaxonomySuggestion.created_at.desc())
    )
    return list(result.scalars().all())


async def accept_suggestion(
    db: AsyncSession,
    admin: User,
    suggestion_id: int,
    note: str | None = None,
) -> TaxonomySuggestion | None:
    suggestion = await db.get(TaxonomySuggestion, suggestion_id)
    if not suggestion:
        return None
    if suggestion.status != SuggestionStatus.PENDING:
        raise ValueError("Suggestion has already been reviewed")

    if suggestion.kind == "name":
        await _apply_name(db, suggestion)
    elif suggestion.kind == "attribute":
        await _apply_attribute(db, suggestion)
    elif suggestion.kind == "field":
        await _apply_field(db, suggestion)
    elif suggestion.kind == "missing_item":
        await _apply_missing_item(db, suggestion)

    suggestion.status = SuggestionStatus.ACCEPTED
    suggestion.reviewed_by = admin.id
    suggestion.reviewed_at = datetime.now(timezone.utc)
    suggestion.review_note = note
    await db.commit()
    await db.refresh(suggestion)
    return suggestion


async def reject_suggestion(
    db: AsyncSession,
    admin: User,
    suggestion_id: int,
    note: str | None = None,
) -> TaxonomySuggestion | None:
    suggestion = await db.get(TaxonomySuggestion, suggestion_id)
    if not suggestion:
        return None
    if suggestion.status != SuggestionStatus.PENDING:
        raise ValueError("Suggestion has already been reviewed")

    suggestion.status = SuggestionStatus.REJECTED
    suggestion.reviewed_by = admin.id
    suggestion.reviewed_at = datetime.now(timezone.utc)
    suggestion.review_note = note
    await db.commit()
    await db.refresh(suggestion)
    return suggestion


# ─── Apply helpers ───────────────────────────────────────────

async def _apply_name(db: AsyncSession, suggestion: TaxonomySuggestion) -> None:
    existing = await db.execute(
        select(ItemName).where(
            ItemName.item_id == suggestion.item_id,
            ItemName.language == suggestion.language,
            ItemName.name == suggestion.value,
        )
    )
    if existing.scalar_one_or_none() is not None:
        return
    db.add(ItemName(item_id=suggestion.item_id, language=suggestion.language, name=suggestion.value))


async def _apply_attribute(db: AsyncSession, suggestion: TaxonomySuggestion) -> None:
    existing = await db.execute(
        select(ItemAttribute).where(
            ItemAttribute.item_id == suggestion.item_id,
            ItemAttribute.key == suggestion.key,
            ItemAttribute.value == suggestion.value,
        )
    )
    if existing.scalar_one_or_none() is not None:
        return
    db.add(ItemAttribute(item_id=suggestion.item_id, key=suggestion.key, value=suggestion.value, unit=suggestion.unit))


async def _apply_field(db: AsyncSession, suggestion: TaxonomySuggestion) -> None:
    item = await db.get(TaxonomyItem, suggestion.item_id)
    if item is None:
        raise ValueError("Item not found")
    setattr(item, suggestion.key, suggestion.value)
    item.updated_at = datetime.now(timezone.utc)


async def _apply_missing_item(db: AsyncSession, suggestion: TaxonomySuggestion) -> None:
    node = await db.get(TaxonomyNode, suggestion.node_id)
    if node is None:
        raise ValueError("Category not found")
    code = f"SUG-{uuid.uuid4().hex[:8].upper()}"
    item = TaxonomyItem(node_id=node.id, code=code, common_name=suggestion.value)
    db.add(item)


# ─── Serialization ──────────────────────────────────────────

async def serialize_suggestion(db: AsyncSession, s: TaxonomySuggestion) -> dict:
    item = await db.get(TaxonomyItem, s.item_id) if s.item_id else None
    node = await db.get(TaxonomyNode, s.node_id) if s.node_id else None
    suggester = await db.get(User, s.suggested_by)
    reviewer = await db.get(User, s.reviewed_by) if s.reviewed_by else None
    return {
        "id": s.id,
        "item_id": s.item_id,
        "item_code": item.code if item else None,
        "item_name": item.common_name if item else None,
        "node_id": s.node_id,
        "node_name": node.name if node else None,
        "kind": s.kind,
        "language": s.language,
        "key": s.key,
        "value": s.value,
        "unit": s.unit,
        "status": s.status.value if s.status else None,
        "suggested_by": s.suggested_by,
        "suggester_email": suggester.email if suggester else None,
        "reviewed_by": s.reviewed_by,
        "review_note": s.review_note,
        "created_at": s.created_at.isoformat() if s.created_at else None,
        "reviewed_at": s.reviewed_at.isoformat() if s.reviewed_at else None,
    }
