"""Tests for email/phone verification, SSO provider list, and superuser guards."""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserRole
from app.services.auth_service import (
    register_user,
    request_email_verification,
    verify_email_address,
    request_phone_verification,
    verify_phone_number,
    list_sso_providers,
    update_user_role,
    toggle_user_active,
    serialize_user,
)


# ── email verification ────────────────────────────────────────────────────────

async def test_email_verification_flow(db: AsyncSession, monkeypatch):
    from app.services import auth_service
    monkeypatch.setattr(auth_service.settings, "RETURN_OTP_IN_DEV", True)

    user, _ = await register_user(db, "verify@example.com", "password123", "Verify User", phone="+256700000000")
    result = await request_email_verification(db, user)
    assert result["channel"] == "email"
    assert result["sent"] is False  # no email service configured
    assert "dev_code" in result  # dev echo only when RETURN_OTP_IN_DEV is enabled

    await verify_email_address(db, user, result["dev_code"])
    assert user.email_verified is True


async def test_email_verification_no_dev_code_by_default(db: AsyncSession):
    user, _ = await register_user(db, "verify0@example.com", "password123", "Verify User 0")
    result = await request_email_verification(db, user)
    assert result["channel"] == "email"
    assert "dev_code" not in result  # RETURN_OTP_IN_DEV defaults to false


async def test_email_verify_wrong_code(db: AsyncSession):
    user, _ = await register_user(db, "verify2@example.com", "password123", "Verify User 2")
    await request_email_verification(db, user)
    with pytest.raises(ValueError, match="Invalid or expired"):
        await verify_email_address(db, user, "000000")


async def test_email_verify_without_request_raises(db: AsyncSession):
    user, _ = await register_user(db, "verify3@example.com", "password123", "Verify User 3")
    with pytest.raises(ValueError, match="No verification code"):
        await verify_email_address(db, user, "123456")


# ── phone verification ────────────────────────────────────────────────────────

async def test_phone_verification_flow(db: AsyncSession, monkeypatch):
    from app.services import auth_service
    monkeypatch.setattr(auth_service.settings, "RETURN_OTP_IN_DEV", True)

    user, _ = await register_user(db, "phone1@example.com", "password123", "Phone User", phone="+256700123456")
    result = await request_phone_verification(db, user)
    assert result["channel"] == "phone"
    assert "dev_code" in result

    await verify_phone_number(db, user, result["dev_code"])
    assert user.phone_verified is True


async def test_phone_verify_requires_phone(db: AsyncSession):
    user, _ = await register_user(db, "phone2@example.com", "password123", "No Phone User")
    with pytest.raises(ValueError, match="No phone number"):
        await request_phone_verification(db, user)


# ── SSO provider list ─────────────────────────────────────────────────────────

def test_sso_providers_listed():
    providers = list_sso_providers()
    names = {p["provider"] for p in providers}
    assert names == {"google", "microsoft", "apple"}
    by_name = {p["provider"]: p for p in providers}
    assert by_name["google"]["enabled"] is True
    assert by_name["microsoft"]["enabled"] is True
    assert by_name["apple"]["enabled"] is False


# ── superuser guards ──────────────────────────────────────────────────────────

async def test_admin_cannot_promote_to_superuser(db: AsyncSession, admin_user, superuser):
    target, _ = await register_user(db, "target@example.com", "password123", "Target")
    with pytest.raises(PermissionError, match="superuser"):
        await update_user_role(db, admin_user, target.id, UserRole.SUPERUSER)


async def test_admin_cannot_toggle_superuser(db: AsyncSession, admin_user, superuser):
    with pytest.raises(PermissionError, match="superuser"):
        await toggle_user_active(db, admin_user, superuser.id)


async def test_superuser_can_manage_others(db: AsyncSession, superuser):
    target, _ = await register_user(db, "managed@example.com", "password123", "Managed")
    updated = await update_user_role(db, superuser, target.id, UserRole.ADMIN)
    assert updated.role == UserRole.ADMIN


# ── serialize_user includes new fields ────────────────────────────────────────

async def test_serialize_user_alternate_fields(db: AsyncSession):
    user, _ = await register_user(db, "serialize@example.com", "password123", "Ser User", phone="+256700111222")
    user.alternate_email = "alt@example.com"
    user.alternate_phone = "+256700333444"
    user.email_verified = True
    await db.commit()

    data = serialize_user(user)
    assert data["full_name"] == "Ser User"
    assert data["alternate_email"] == "alt@example.com"
    assert data["alternate_phone"] == "+256700333444"
    assert data["email_verified"] is True
    assert data["role"] == "enterprise"
