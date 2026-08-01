"""Unit tests for the RBAC service: permission matrix, seeding, role/type assignment."""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserRole, UserType
from app.services.rbac_service import (
    get_user_permissions,
    has_permission,
    user_role_codes,
    seed_system_rbac,
    list_roles,
    list_permissions,
    assign_roles_to_user,
    set_user_type,
    create_custom_role,
    delete_role,
)
from app.services.auth_service import register_user


# ── default permission matrix ─────────────────────────────────────────────────

async def test_superuser_has_everything(db: AsyncSession, superuser: User):
    perms = await get_user_permissions(db, superuser)
    assert "system.admin" in perms
    assert "users.manage" in perms
    assert "certificates.approve" in perms
    assert "commerce.jobs" in perms


async def test_admin_matrix(db: AsyncSession, admin_user: User):
    perms = await get_user_permissions(db, admin_user)
    assert "users.manage" in perms
    assert "roles.manage" in perms
    assert "enterprise.access" in perms
    assert "system.admin" not in perms  # reserved for superuser
    assert "tenants.manage" not in perms


async def test_viewer_is_read_only(db: AsyncSession, viewer_user: User):
    perms = await get_user_permissions(db, viewer_user)
    assert "items.read" in perms
    assert "search.use" in perms
    assert "operations.access" not in perms  # viewer cannot operate
    assert "users.manage" not in perms
    assert "certificates.issue" not in perms


async def test_clerk_has_operations_access(db: AsyncSession):
    user = User(
        email="clerk@test.com", full_name="Clerk",
        hashed_password="x", role=UserRole.CLERK, is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    perms = await get_user_permissions(db, user)
    assert "operations.access" in perms
    assert "inventory.manage" in perms
    assert "commerce.jobs" in perms
    assert "enterprise.access" not in perms
    assert "certificates.approve" not in perms


async def test_courier_matrix(db: AsyncSession):
    user = User(
        email="courier@test.com", full_name="Courier",
        hashed_password="x", role=UserRole.COURIER, is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    perms = await get_user_permissions(db, user)
    assert "shipments.manage" in perms
    assert "telemetry.ingest" in perms
    assert "enterprise.access" not in perms


async def test_government_agent_matrix(db: AsyncSession):
    user = User(
        email="gov@test.com", full_name="Gov",
        hashed_password="x", role=UserRole.GOVERNMENT_AGENT, is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    perms = await get_user_permissions(db, user)
    assert "gov.read" in perms
    assert "compliance.manage" in perms
    assert "certificates.verify" in perms
    assert "operations.access" in perms
    assert "users.manage" not in perms


async def test_auditor_is_read_only_plus_verify(db: AsyncSession):
    user = User(
        email="audit@test.com", full_name="Auditor",
        hashed_password="x", role=UserRole.AUDITOR, is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    perms = await get_user_permissions(db, user)
    assert "certificates.verify" in perms
    assert "operations.access" in perms
    assert "certificates.issue" not in perms
    assert "inventory.manage" not in perms


async def test_has_permission_helper(db: AsyncSession, admin_user: User):
    assert await has_permission(db, admin_user, "users.manage") is True
    assert await has_permission(db, admin_user, "system.admin") is False


def test_user_role_codes_primary_only():
    user = User(role=UserRole.ADMIN, hashed_password="x", full_name="x", email="x@x.com")
    assert user_role_codes(user) == ["admin"]


def test_list_permissions_catalog():
    codes = {p["code"] for p in list_permissions()}
    assert "certificates.approve" in codes
    assert "commerce.jobs" in codes
    assert "operations.access" in codes


# ── seeding ──────────────────────────────────────────────────────────────────

async def test_seed_system_rbac_idempotent(db: AsyncSession):
    first = await seed_system_rbac(db)
    second = await seed_system_rbac(db)
    assert first["permissions"] == second["permissions"]
    assert first["roles"] == second["roles"]
    assert second["created_permissions"] == 0
    assert second["created_roles"] == 0
    assert first["permissions"] > 50  # catalog is comprehensive
    assert first["roles"] >= 9  # all system roles present


async def test_list_roles_after_seed(db: AsyncSession):
    await seed_system_rbac(db)
    roles = await list_roles(db)
    codes = {r["code"] for r in roles}
    assert {"clerk", "courier", "verifier", "auditor", "government_agent", "admin", "superuser"} <= codes


# ── role / type assignment ───────────────────────────────────────────────────

async def test_assign_roles_to_user(db: AsyncSession, admin_user: User):
    await seed_system_rbac(db)
    target, _ = await register_user(db, "target@example.com", "password123", "Target")
    updated = await assign_roles_to_user(db, admin_user, target.id, ["clerk", "courier"])
    codes = user_role_codes(updated)
    assert "clerk" in codes
    assert "courier" in codes
    perms = await get_user_permissions(db, updated)
    assert "operations.access" in perms  # extra roles widen permissions


async def test_assign_roles_unknown_role_raises(db: AsyncSession, admin_user: User):
    await seed_system_rbac(db)
    target, _ = await register_user(db, "target2@example.com", "password123", "Target")
    with pytest.raises(ValueError, match="Unknown roles"):
        await assign_roles_to_user(db, admin_user, target.id, ["nope"])


async def test_assign_roles_self_forbidden(db: AsyncSession, admin_user: User):
    await seed_system_rbac(db)
    with pytest.raises(ValueError, match="own roles"):
        await assign_roles_to_user(db, admin_user, admin_user.id, ["clerk"])


async def test_assign_roles_superuser_grant_requires_superuser(db: AsyncSession, admin_user: User):
    await seed_system_rbac(db)
    target, _ = await register_user(db, "target3@example.com", "password123", "Target")
    with pytest.raises(PermissionError, match="superuser"):
        await assign_roles_to_user(db, admin_user, target.id, ["superuser"])


async def test_assign_roles_superuser_grant_allowed(db: AsyncSession, superuser: User):
    await seed_system_rbac(db)
    target, _ = await register_user(db, "target4@example.com", "password123", "Target")
    updated = await assign_roles_to_user(db, superuser, target.id, ["superuser"])
    assert "superuser" in user_role_codes(updated)


async def test_assign_roles_non_admin_denied(db: AsyncSession, viewer_user: User):
    await seed_system_rbac(db)
    target, _ = await register_user(db, "target5@example.com", "password123", "Target")
    with pytest.raises(PermissionError, match="Only superusers and admins"):
        await assign_roles_to_user(db, viewer_user, target.id, ["clerk"])


async def test_set_user_type(db: AsyncSession, admin_user: User):
    target, _ = await register_user(db, "target6@example.com", "password123", "Target")
    updated = await set_user_type(db, admin_user, target.id, UserType.GOVERNMENT)
    assert updated.user_type == UserType.GOVERNMENT


async def test_register_sets_organization_type(db: AsyncSession):
    user, _ = await register_user(db, "type@example.com", "password123", "Typed")
    assert user.user_type == UserType.ORGANIZATION


# ── custom roles ─────────────────────────────────────────────────────────────

async def test_create_and_delete_custom_role(db: AsyncSession, admin_user: User):
    await seed_system_rbac(db)
    role = await create_custom_role(
        db, admin_user, "inspector", "Inspector", ["items.read", "certificates.verify"]
    )
    assert role.code == "inspector"
    assert role.is_system is False
    assert {p.code for p in role.permissions} == {"items.read", "certificates.verify"}

    await delete_role(db, admin_user, "inspector")
    roles = await list_roles(db)
    assert "inspector" not in {r["code"] for r in roles}


async def test_create_custom_role_duplicate_raises(db: AsyncSession, admin_user: User):
    await seed_system_rbac(db)
    await create_custom_role(db, admin_user, "dup", "Dup", ["items.read"])
    with pytest.raises(ValueError, match="already exists"):
        await create_custom_role(db, admin_user, "dup", "Dup Again", [])


async def test_create_custom_role_unknown_permission_raises(db: AsyncSession, admin_user: User):
    await seed_system_rbac(db)
    with pytest.raises(ValueError, match="Unknown permissions"):
        await create_custom_role(db, admin_user, "bad", "Bad", ["not.a.perm"])


async def test_delete_system_role_denied(db: AsyncSession, admin_user: User):
    await seed_system_rbac(db)
    with pytest.raises(PermissionError, match="System roles"):
        await delete_role(db, admin_user, "admin")
