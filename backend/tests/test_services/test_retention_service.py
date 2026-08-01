"""Unit tests for retention_service: policy creation, listing, SQL injection guard."""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import UserRole
from app.services.auth_service import register_user
from app.services.retention_service import (
    create_archive_policy,
    list_archive_policies,
    ALLOWED_ARCHIVE_TABLES,
)


async def _admin(db: AsyncSession, suffix: str = "") -> object:
    user, _ = await register_user(db, f"ret_admin{suffix}@test.com", "password123", "Admin")
    user.role = UserRole.ADMIN
    await db.commit()
    return user


async def _viewer(db: AsyncSession) -> object:
    user, _ = await register_user(db, "ret_viewer@test.com", "password123", "Viewer")
    user.role = UserRole.VIEWER
    await db.commit()
    return user


async def test_create_policy_success(db: AsyncSession):
    user = await _admin(db)
    table = next(iter(ALLOWED_ARCHIVE_TABLES))  # pick any allowed table
    policy = await create_archive_policy(db, user, table, 90)
    assert policy.id is not None
    assert policy.entity_type == table
    assert policy.retention_days == 90


async def test_create_policy_non_admin_denied(db: AsyncSession):
    user = await _viewer(db)
    with pytest.raises(PermissionError, match="Admin"):
        await create_archive_policy(db, user, "search_logs", 30)


async def test_create_policy_invalid_table_rejected(db: AsyncSession):
    """SQL injection guard: entity_type must be in the whitelist."""
    user = await _admin(db, "2")
    with pytest.raises(ValueError, match="Allowed tables"):
        await create_archive_policy(db, user, "users; DROP TABLE users;--", 30)


async def test_create_policy_unknown_table_rejected(db: AsyncSession):
    user = await _admin(db, "3")
    with pytest.raises(ValueError, match="Allowed tables"):
        await create_archive_policy(db, user, "some_random_table", 60)


async def test_list_archive_policies(db: AsyncSession):
    user = await _admin(db, "4")
    table = "search_logs"
    await create_archive_policy(db, user, table, 30)
    policies = await list_archive_policies(db)
    names = [p["entity_type"] for p in policies]
    assert table in names


async def test_all_allowed_tables_are_valid_identifiers():
    """Every table name in the whitelist must be a safe SQL identifier."""
    import re
    pattern = re.compile(r"^[a-z_][a-z0-9_]*$")
    for table in ALLOWED_ARCHIVE_TABLES:
        assert pattern.match(table), f"'{table}' is not a safe SQL identifier"
