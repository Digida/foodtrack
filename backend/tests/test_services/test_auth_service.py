"""Unit tests for auth_service: registration, login, JWT, MFA, password change."""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserRole
from app.services.auth_service import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
    register_user,
    authenticate_user,
    change_password,
    verify_mfa_token,
    generate_email_otp,
    verify_email_otp,
)


# ── password helpers ────────────────────────────────────────────────────────

def test_hash_and_verify_password():
    hashed = hash_password("supersecret")
    assert verify_password("supersecret", hashed)
    assert not verify_password("wrong", hashed)


# ── JWT ─────────────────────────────────────────────────────────────────────

def test_create_and_decode_access_token():
    token = create_access_token({"sub": "42", "role": "admin"})
    payload = decode_access_token(token)
    assert payload is not None
    assert payload["sub"] == "42"
    assert payload["role"] == "admin"


def test_decode_invalid_token_returns_none():
    assert decode_access_token("not.a.token") is None


# ── registration ────────────────────────────────────────────────────────────

async def test_register_user_success(db: AsyncSession):
    user, token = await register_user(db, "test@example.com", "password123", "Test User")
    assert user.id is not None
    assert user.email == "test@example.com"
    assert user.role == UserRole.ENTERPRISE
    payload = decode_access_token(token)
    assert payload["sub"] == str(user.id)


async def test_register_duplicate_email_raises(db: AsyncSession):
    await register_user(db, "dup@example.com", "password123", "First")
    with pytest.raises(ValueError, match="already registered"):
        await register_user(db, "dup@example.com", "password123", "Second")


async def test_register_short_password_raises(db: AsyncSession):
    with pytest.raises(ValueError, match="8 characters"):
        await register_user(db, "short@example.com", "abc", "User")


# ── login ───────────────────────────────────────────────────────────────────

async def test_authenticate_user_success(db: AsyncSession):
    await register_user(db, "login@example.com", "mypassword1", "Login User")
    user, token, mfa = await authenticate_user(db, "login@example.com", "mypassword1")
    assert user.email == "login@example.com"
    assert token is not None
    assert mfa is None  # no MFA configured


async def test_authenticate_user_wrong_password(db: AsyncSession):
    await register_user(db, "fail@example.com", "correctpass1", "Fail User")
    with pytest.raises(ValueError, match="Invalid credentials"):
        await authenticate_user(db, "fail@example.com", "wrongpass")


async def test_authenticate_inactive_user(db: AsyncSession):
    user, _ = await register_user(db, "inactive@example.com", "password123", "Inactive")
    user.is_active = False
    await db.commit()
    with pytest.raises(ValueError, match="inactive"):
        await authenticate_user(db, "inactive@example.com", "password123")


# ── password change ─────────────────────────────────────────────────────────

async def test_change_password_success(db: AsyncSession):
    user, _ = await register_user(db, "change@example.com", "oldpassword1", "Change User")
    await change_password(db, user, "oldpassword1", "newpassword1")
    assert verify_password("newpassword1", user.hashed_password)


async def test_change_password_wrong_old(db: AsyncSession):
    user, _ = await register_user(db, "change2@example.com", "oldpassword1", "Change User 2")
    with pytest.raises(ValueError, match="Current password"):
        await change_password(db, user, "wrongold", "newpassword1")


async def test_change_password_too_short(db: AsyncSession):
    user, _ = await register_user(db, "change3@example.com", "oldpassword1", "Change User 3")
    with pytest.raises(ValueError, match="8 characters"):
        await change_password(db, user, "oldpassword1", "short")


# ── OTP helpers ─────────────────────────────────────────────────────────────

def test_email_otp_valid():
    code, token = generate_email_otp()
    assert verify_email_otp(token, code) is True


def test_email_otp_wrong_code():
    code, token = generate_email_otp()
    assert verify_email_otp(token, "000000") is False


def test_email_otp_invalid_token():
    assert verify_email_otp("garbage.token.value", "123456") is False


# ── MFA verify bypass is gone ───────────────────────────────────────────────

async def test_mfa_email_requires_valid_code(db: AsyncSession):
    """Ensure email MFA no longer passes any code unconditionally."""
    user, _ = await register_user(db, "mfa@example.com", "password123", "MFA User")
    # Give the user a stored OTP token
    code, token = generate_email_otp()
    user.mfa_otp_token = token
    user.email_verified = True
    await db.commit()

    # Build a temp MFA token as the login flow would
    temp = create_access_token({"sub": str(user.id), "step": "mfa", "mfa_type": "email"}, expires_delta=5)

    # Wrong code must fail
    with pytest.raises(ValueError, match="Invalid MFA code"):
        await verify_mfa_token(db, temp, "000000")

    # Correct code must succeed
    _, full_token = await verify_mfa_token(db, temp, code)
    payload = decode_access_token(full_token)
    assert payload["sub"] == str(user.id)
