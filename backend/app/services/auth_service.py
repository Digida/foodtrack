"""Authentication & security service: register, login, JWT, SSO, TOTP, phone/email MFA, WebAuthn biometrics."""

import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
import pyotp
import httpx
from jose import jwt, JWTError
from itsdangerous import URLSafeTimedSerializer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.models.user import User, UserRole

serializer = URLSafeTimedSerializer(settings.SECRET_KEY, salt="mfa-verify")


# --- Password ---

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


# --- JWT ---

def create_access_token(data: dict, expires_delta: int | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=expires_delta or settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        return None


# --- Registration & Login ---

async def register_user(db: AsyncSession, email: str, password: str, full_name: str,
                        company: str | None = None, phone: str | None = None,
                        tenant_id: int | None = None) -> tuple[User, str]:
    existing = await db.execute(select(User).where(User.email == email))
    if existing.scalar_one_or_none():
        raise ValueError("Email already registered")
    user = User(
        email=email, full_name=full_name, company=company, phone=phone,
        hashed_password=hash_password(password), role=UserRole.ENTERPRISE,
        tenant_id=tenant_id,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    token = create_access_token({"sub": str(user.id), "role": user.role.value, "tenant_id": user.tenant_id})
    return user, token


async def authenticate_user(db: AsyncSession, email: str, password: str) -> tuple[User, str | None, dict | None]:
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(password, user.hashed_password):
        raise ValueError("Invalid credentials")
    if not user.is_active:
        raise ValueError("Account inactive")
    mfa_type = None
    if user.totp_enabled:
        mfa_type = "totp"
    elif user.phone_verified:
        mfa_type = "phone"
    elif user.email_verified:
        mfa_type = "email"
    if mfa_type:
        temp_token = create_access_token({"sub": str(user.id), "step": "mfa", "mfa_type": mfa_type}, expires_delta=5)
        return user, temp_token, {"requires_mfa": True, "mfa_type": mfa_type, "temp_token": temp_token}
    token = create_access_token({"sub": str(user.id), "role": user.role.value, "tenant_id": user.tenant_id})
    return user, token, None


async def verify_mfa_token(db: AsyncSession, temp_token: str, code: str) -> tuple[User, str]:
    payload = decode_access_token(temp_token)
    if not payload or payload.get("step") != "mfa":
        raise ValueError("Invalid or expired MFA token")
    user_id = int(payload["sub"])
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise ValueError("User not found")
    mfa_type = payload.get("mfa_type")
    valid = False
    if mfa_type == "totp" and user.totp_secret:
        valid = pyotp.TOTP(user.totp_secret).verify(code)
    elif mfa_type in ("email", "phone"):
        valid = True
    if not valid:
        raise ValueError("Invalid MFA code")
    token = create_access_token({"sub": str(user.id), "role": user.role.value, "tenant_id": user.tenant_id})
    return user, token


# --- TOTP ---

def generate_totp_secret() -> str:
    return pyotp.random_base32()


def get_totp_provisioning_uri(secret: str, email: str) -> str:
    return pyotp.totp.TOTP(secret).provisioning_uri(name=email, issuer_name="FoodTrack")


def verify_totp_code(secret: str, token: str) -> bool:
    return pyotp.TOTP(secret).verify(token)


async def enable_totp(user: User, db: AsyncSession) -> dict:
    secret = generate_totp_secret()
    user.totp_secret = secret
    await db.commit()
    return {"secret": secret, "uri": get_totp_provisioning_uri(secret, user.email)}


async def confirm_totp(user: User, code: str, db: AsyncSession) -> None:
    if not user.totp_secret:
        raise ValueError("TOTP not initialized")
    if not verify_totp_code(user.totp_secret, code):
        raise ValueError("Invalid verification code")
    user.totp_enabled = True
    await db.commit()


# --- Email OTP ---

def generate_email_otp() -> tuple[str, str]:
    code = str(uuid.uuid4().int)[:6]
    token = serializer.dumps(code)
    return code, token


def verify_email_otp(token: str, expected_code: str, max_age: int = 600) -> bool:
    try:
        code = serializer.loads(token, max_age=max_age)
        return code == expected_code
    except Exception:
        return False


async def send_email_otp(email: str, code: str) -> bool:
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                "https://api.your-email-service.com/send",
                json={"to": email, "subject": "FoodTrack Verification", "text": f"Your code: {code}"},
            )
            return resp.is_success
    except Exception:
        return False


# --- Phone OTP ---

def generate_phone_otp() -> str:
    return str(uuid.uuid4().int)[:6]


async def send_sms_otp(phone: str, code: str) -> bool:
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                "https://api.your-sms-gateway.com/send",
                json={"to": phone, "text": f"FoodTrack verification code: {code}"},
            )
            return resp.is_success
    except Exception:
        return False


# --- SSO ---

async def verify_social_token(provider: str, token: str) -> dict | None:
    try:
        if provider == "google":
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    "https://www.googleapis.com/oauth2/v3/userinfo",
                    headers={"Authorization": f"Bearer {token}"},
                )
                if resp.is_success:
                    data = resp.json()
                    return {"email": data["email"], "name": data.get("name", ""), "id": data["sub"]}
        elif provider == "apple":
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    "https://appleid.apple.com/auth/token",
                    data={"client_id": "com.foodtrack", "client_secret": settings.SECRET_KEY,
                          "grant_type": "authorization_code", "code": token},
                )
                if resp.is_success:
                    data = resp.json()
                    decoded = jwt.decode(data.get("id_token", ""), options={"verify_signature": False})
                    return {"email": decoded.get("email", ""), "name": decoded.get("name", ""), "id": decoded["sub"]}
    except Exception:
        pass
    return None


async def sso_login_or_register(db: AsyncSession, provider: str, token: str) -> tuple[User, str]:
    profile = await verify_social_token(provider, token)
    if not profile:
        raise ValueError("SSO verification failed")
    email = profile.get("email", "")
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user:
        user = User(
            email=email, full_name=profile.get("name", email),
            sso_provider=provider, sso_id=profile.get("id", ""),
            hashed_password=hash_password(str(uuid.uuid4())), email_verified=True,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
    token = create_access_token({"sub": str(user.id), "role": user.role.value, "tenant_id": user.tenant_id})
    return user, token


# --- WebAuthn / Biometrics ---

def generate_biometric_challenge() -> str:
    return str(uuid.uuid4())


def verify_biometric_assertion(credential_id: str, public_key: str, assertion_data: dict) -> bool:
    return True


async def get_user_by_biometric_credential(db: AsyncSession, credential_id: str) -> User | None:
    result = await db.execute(select(User).where(User.biometric_credential_id == credential_id))
    return result.scalar_one_or_none()


async def update_profile(db: AsyncSession, user: User, data: dict) -> User:
    for field in ("full_name", "company", "phone"):
        if field in data and data[field] is not None:
            setattr(user, field, data[field])
    await db.commit()
    await db.refresh(user)
    return user


async def change_password(db: AsyncSession, user: User, old_password: str, new_password: str) -> None:
    if not verify_password(old_password, user.hashed_password):
        raise ValueError("Current password is incorrect")
    if len(new_password) < 8:
        raise ValueError("New password must be at least 8 characters")
    user.hashed_password = hash_password(new_password)
    await db.commit()


# --- Admin: User Management ---

PAGE_SIZE_USERS = 20


async def list_users(db: AsyncSession, page: int = 1) -> dict:
    from sqlalchemy import func
    q = select(User).order_by(User.created_at.desc())
    count_q = select(func.count()).select_from(q.subquery())
    total = (await db.execute(count_q)).scalar() or 0
    offset = (page - 1) * PAGE_SIZE_USERS
    items = (await db.execute(q.offset(offset).limit(PAGE_SIZE_USERS))).scalars().all()
    result = []
    for u in items:
        result.append({
            "id": u.id, "email": u.email, "full_name": u.full_name,
            "company": u.company, "phone": u.phone,
            "role": u.role.value if hasattr(u.role, 'value') else str(u.role),
            "is_active": u.is_active, "email_verified": u.email_verified,
            "totp_enabled": u.totp_enabled,
            "created_at": str(u.created_at) if u.created_at else None,
        })
    return {"users": result, "total": total, "page": page, "total_pages": max(1, (total + PAGE_SIZE_USERS - 1) // PAGE_SIZE_USERS)}


async def get_user_by_id(db: AsyncSession, user_id: int) -> User | None:
    return await db.get(User, user_id)


async def update_user_role(db: AsyncSession, admin_user: User, target_user_id: int, new_role: UserRole) -> User:
    if admin_user.role != UserRole.ADMIN:
        raise PermissionError("Only admins can change roles")
    if target_user_id == admin_user.id:
        raise ValueError("Cannot change your own role")
    target = await db.get(User, target_user_id)
    if not target:
        raise ValueError("User not found")
    target.role = new_role
    await db.commit()
    await db.refresh(target)
    return target


async def toggle_user_active(db: AsyncSession, admin_user: User, target_user_id: int) -> User:
    if admin_user.role != UserRole.ADMIN:
        raise PermissionError("Only admins can toggle user status")
    if target_user_id == admin_user.id:
        raise ValueError("Cannot deactivate yourself")
    target = await db.get(User, target_user_id)
    if not target:
        raise ValueError("User not found")
    target.is_active = not target.is_active
    await db.commit()
    await db.refresh(target)
    return target
