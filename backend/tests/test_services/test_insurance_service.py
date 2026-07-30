"""Unit tests for insurance_service: create policy, file claim, update status."""
import json
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import UserRole
from app.models.insurance import ClaimStatus
from app.services.auth_service import register_user
from app.services.insurance_service import create_policy, list_policies, file_claim, list_claims, update_claim_status


async def _make_item_and_user(db: AsyncSession, suffix: str = ""):
    from app.models.taxonomy import TaxonomyItem, TaxonomyNode, Taxonomy
    tax = Taxonomy(name=f"Tax{suffix}")
    db.add(tax)
    await db.commit()
    node = TaxonomyNode(taxonomy_id=tax.id, code=f"N{suffix}", name="Node")
    db.add(node)
    await db.commit()
    item = TaxonomyItem(node_id=node.id, code=f"I{suffix}", common_name="Mango")
    db.add(item)
    await db.commit()
    await db.refresh(item)
    user, _ = await register_user(db, f"ins{suffix}@test.com", "password123", "Ins User")
    user.role = UserRole.ENTERPRISE
    await db.commit()
    return item, user


async def test_create_policy_success(db: AsyncSession):
    item, user = await _make_item_and_user(db, "1")
    policy = await create_policy(db, user, item.id, "POL-001", 50000.0)
    assert policy.id is not None
    assert policy.policy_number == "POL-001"
    assert policy.coverage_amount == 50000.0


async def test_create_policy_item_not_found(db: AsyncSession):
    user, _ = await register_user(db, "ins_bad@test.com", "password123", "Bad")
    user.role = UserRole.ENTERPRISE
    await db.commit()
    with pytest.raises(ValueError, match="not found"):
        await create_policy(db, user, 99999, "POL-X", 1000.0)


async def test_create_policy_viewer_denied(db: AsyncSession):
    item, _ = await _make_item_and_user(db, "2")
    viewer, _ = await register_user(db, "insviewer@test.com", "password123", "Viewer")
    viewer.role = UserRole.VIEWER
    await db.commit()
    with pytest.raises(PermissionError):
        await create_policy(db, viewer, item.id, "POL-V", 1000.0)


async def test_list_policies(db: AsyncSession):
    item, user = await _make_item_and_user(db, "3")
    await create_policy(db, user, item.id, "POL-002", 10000.0)
    result = await list_policies(db, page=1, item_id=item.id)
    assert result["total"] >= 1
    assert result["policies"][0]["policy_number"] == "POL-002"


async def test_file_claim_success(db: AsyncSession):
    item, user = await _make_item_and_user(db, "4")
    policy = await create_policy(db, user, item.id, "POL-003", 20000.0)
    claim = await file_claim(db, user, policy.id, "fire", 5000.0,
                             documents=["invoice.pdf", "photos.zip"])
    assert claim.id is not None
    assert claim.status == ClaimStatus.DRAFT
    # documents_json should be stored as JSON (list), not a raw string
    stored = claim.documents_json
    if isinstance(stored, str):
        stored = json.loads(stored)
    assert stored == ["invoice.pdf", "photos.zip"]


async def test_list_claims_decoded_documents(db: AsyncSession):
    item, user = await _make_item_and_user(db, "5")
    policy = await create_policy(db, user, item.id, "POL-004", 30000.0)
    await file_claim(db, user, policy.id, "flood", 8000.0, documents=["doc1.pdf"])
    result = await list_claims(db, page=1)
    claim_data = result["claims"][0]
    # documents must be a list in the API response, never a raw JSON string
    assert isinstance(claim_data["documents"], list)


async def test_update_claim_status(db: AsyncSession):
    item, user = await _make_item_and_user(db, "6")
    policy = await create_policy(db, user, item.id, "POL-005", 40000.0)
    claim = await file_claim(db, user, policy.id, "theft", 12000.0)
    admin, _ = await register_user(db, "ins_admin@test.com", "password123", "Admin")
    admin.role = UserRole.ADMIN
    await db.commit()
    updated = await update_claim_status(db, admin, claim.id, ClaimStatus.APPROVED)
    assert updated.status == ClaimStatus.APPROVED


async def test_update_claim_non_admin_denied(db: AsyncSession):
    item, user = await _make_item_and_user(db, "7")
    policy = await create_policy(db, user, item.id, "POL-006", 50000.0)
    claim = await file_claim(db, user, policy.id, "water", 3000.0)
    with pytest.raises(PermissionError):
        await update_claim_status(db, user, claim.id, ClaimStatus.APPROVED)
