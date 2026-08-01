"""Unit tests for refresh-token lifecycle: issue, rotation, reuse rejection, revoke."""
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rbac import RefreshToken
from app.services.auth_service import (
    register_user,
    issue_refresh_token,
    rotate_refresh_token,
    revoke_refresh_token,
    revoke_all_user_tokens,
    _hash_token,
)


async def test_issue_refresh_token_persists_hash(db: AsyncSession):
    user, _ = await register_user(db, "rt1@example.com", "password123", "RT User")
    raw = await issue_refresh_token(db, user, "test-agent", "127.0.0.1")
    assert raw  # raw token is returned to the client
    stored = (await db.execute(
        __import__("sqlalchemy").select(RefreshToken).where(RefreshToken.user_id == user.id)
    )).scalars().all()
    assert len(stored) == 1
    assert stored[0].token_hash == _hash_token(raw)  # only the hash is stored
    assert stored[0].token_hash != raw
    assert stored[0].user_agent == "test-agent"
    assert stored[0].ip_address == "127.0.0.1"


async def test_rotate_issues_new_and_revokes_old(db: AsyncSession):
    user, _ = await register_user(db, "rt2@example.com", "password123", "RT User")
    raw1 = await issue_refresh_token(db, user)
    user2, raw2 = await rotate_refresh_token(db, raw1)
    assert user2.id == user.id
    assert raw2 != raw1

    rows = (await db.execute(
        __import__("sqlalchemy").select(RefreshToken).where(RefreshToken.user_id == user.id)
    )).scalars().all()
    by_hash = {r.token_hash: r for r in rows}
    assert by_hash[_hash_token(raw1)].revoked_at is not None
    assert by_hash[_hash_token(raw2)].revoked_at is None


async def test_rotate_reuse_of_consumed_token_rejected(db: AsyncSession):
    user, _ = await register_user(db, "rt3@example.com", "password123", "RT User")
    raw1 = await issue_refresh_token(db, user)
    await rotate_refresh_token(db, raw1)  # consumes raw1
    with pytest.raises(ValueError, match="Invalid or expired"):
        await rotate_refresh_token(db, raw1)  # replay is rejected


async def test_rotate_expired_token_rejected(db: AsyncSession):
    user, _ = await register_user(db, "rt4@example.com", "password123", "RT User")
    raw = await issue_refresh_token(db, user)
    row = (await db.execute(
        __import__("sqlalchemy").select(RefreshToken).where(RefreshToken.token_hash == _hash_token(raw))
    )).scalar_one()
    row.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    await db.commit()
    with pytest.raises(ValueError, match="Invalid or expired"):
        await rotate_refresh_token(db, raw)


async def test_rotate_unknown_token_rejected(db: AsyncSession):
    with pytest.raises(ValueError, match="Invalid or expired"):
        await rotate_refresh_token(db, "garbage-not-a-real-token")


async def test_revoke_refresh_token(db: AsyncSession):
    user, _ = await register_user(db, "rt5@example.com", "password123", "RT User")
    raw = await issue_refresh_token(db, user)
    await revoke_refresh_token(db, raw)
    with pytest.raises(ValueError, match="Invalid or expired"):
        await rotate_refresh_token(db, raw)


async def test_revoke_all_user_tokens(db: AsyncSession):
    user, _ = await register_user(db, "rt6@example.com", "password123", "RT User")
    raw1 = await issue_refresh_token(db, user)
    raw2 = await issue_refresh_token(db, user)
    await revoke_all_user_tokens(db, user)
    for raw in (raw1, raw2):
        with pytest.raises(ValueError, match="Invalid or expired"):
            await rotate_refresh_token(db, raw)
