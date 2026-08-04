"""Authentication & security service: register, login, JWT, SSO, TOTP, phone/email MFA, WebAuthn biometrics."""

import base64
import hashlib
import random
import secrets
import time
import uuid
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import bcrypt
import pyotp
import httpx
from jose import jwt, JWTError
from itsdangerous import URLSafeTimedSerializer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError

from app.config import settings
from app.models.user import User, UserRole, UserType
from app.models.rbac import RefreshToken

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


# --- Refresh tokens ---

def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


async def issue_refresh_token(
    db: AsyncSession, user: User,
    user_agent: str | None = None, ip_address: str | None = None,
) -> str:
    """Persist a new revocable refresh token and return the raw value.

    Only the SHA-256 hash is stored, so a DB leak does not expose usable tokens.
    """
    raw = secrets.token_urlsafe(48)
    row = RefreshToken(
        user_id=user.id,
        token_hash=_hash_token(raw),
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        user_agent=(user_agent or "")[:255] or None,
        ip_address=ip_address,
    )
    db.add(row)
    await db.commit()
    return raw


async def rotate_refresh_token(
    db: AsyncSession, raw: str,
    user_agent: str | None = None, ip_address: str | None = None,
) -> tuple[User, str]:
    """Validate a refresh token, revoke it and issue a fresh one (rotation)."""
    row = (await db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == _hash_token(raw))
    )).scalar_one_or_none()
    if not row or row.revoked_at:
        raise ValueError("Invalid or expired refresh token")
    # SQLite returns naive datetimes for DateTime(timezone=True) — normalise.
    expires_at = row.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        raise ValueError("Invalid or expired refresh token")
    user = await db.get(User, row.user_id)
    if not user or not user.is_active:
        raise ValueError("Account inactive")
    row.revoked_at = datetime.now(timezone.utc)
    await db.commit()
    new_raw = await issue_refresh_token(db, user, user_agent, ip_address)
    return user, new_raw


async def revoke_refresh_token(db: AsyncSession, raw: str) -> None:
    row = (await db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == _hash_token(raw))
    )).scalar_one_or_none()
    if row and not row.revoked_at:
        row.revoked_at = datetime.now(timezone.utc)
        await db.commit()


async def revoke_all_user_tokens(db: AsyncSession, user: User) -> None:
    await db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=datetime.now(timezone.utc))
    )
    await db.commit()


# --- Registration & Login ---

async def register_user(db: AsyncSession, email: str, password: str, full_name: str,
                        company: str | None = None, phone: str | None = None,
                        tenant_id: int | None = None) -> tuple[User, str]:
    existing = await db.execute(select(User).where(User.email == email))
    if existing.scalar_one_or_none():
        raise ValueError("Email already registered")
    if phone:
        dup = await db.execute(select(User).where(User.phone == phone))
        if dup.scalar_one_or_none():
            raise ValueError("Phone number already registered")
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters")
    user = User(
        email=email, full_name=full_name, company=company, phone=phone,
        hashed_password=hash_password(password), role=UserRole.ENTERPRISE,
        tenant_id=tenant_id, user_type=UserType.ORGANIZATION,
    )
    db.add(user)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise ValueError("Email or phone number already registered")
    await db.refresh(user)
    token = create_access_token(_user_token_payload(user))
    return user, token


async def authenticate_user(db: AsyncSession, email: str, password: str) -> tuple[User, str | None, dict | None]:
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(password, user.hashed_password):
        raise ValueError("Invalid credentials")
    if not user.is_active:
        raise ValueError("Account inactive")
    # MFA is opt-in. Email/phone verification is a separate trust level and
    # does NOT force an OTP challenge on every login — only TOTP does.
    if user.totp_enabled:
        temp_token = create_access_token({"sub": str(user.id), "step": "mfa", "mfa_type": "totp"}, expires_delta=5)
        return user, temp_token, {"requires_mfa": True, "mfa_type": "totp", "temp_token": temp_token}
    token = create_access_token(_user_token_payload(user))
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
        # Verify TOTP code using pyotp (time-based, 30s window)
        valid = pyotp.TOTP(user.totp_secret).verify(code, valid_window=1)
    elif mfa_type == "email":
        # Verify signed OTP token stored on the user record
        if user.mfa_otp_token:
            valid = verify_email_otp(user.mfa_otp_token, code)
            if valid:
                # Consume the token so it cannot be reused
                user.mfa_otp_token = None
                await db.commit()
    elif mfa_type == "phone":
        # Verify signed OTP token stored on the user record
        if user.mfa_otp_token:
            valid = verify_email_otp(user.mfa_otp_token, code)
            if valid:
                user.mfa_otp_token = None
                await db.commit()
    if not valid:
        raise ValueError("Invalid MFA code")
    token = create_access_token(_user_token_payload(user))
    return user, token


# --- TOTP ---

def generate_totp_secret() -> str:
    return pyotp.random_base32()


def get_totp_provisioning_uri(secret: str, email: str) -> str:
    return pyotp.totp.TOTP(secret).provisioning_uri(name=email, issuer_name="FoodTrack")


def verify_totp_code(secret: str, token: str) -> bool:
    return pyotp.TOTP(secret).verify(token, valid_window=1)


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

def _uniform_otp_code() -> str:
    """Return a uniformly distributed 6-digit code (000000-999999)."""
    return f"{random.SystemRandom().randrange(10 ** 6):06d}"


def generate_email_otp() -> tuple[str, str]:
    code = _uniform_otp_code()
    token = serializer.dumps(code)
    return code, token


def verify_email_otp(token: str, expected_code: str, max_age: int = 600) -> bool:
    try:
        code = serializer.loads(token, max_age=max_age)
        return code == expected_code
    except Exception:
        return False


async def send_email_otp(email: str, code: str) -> bool:
    """Send a 6-digit OTP via the configured email service.

    Requires EMAIL_API_URL and EMAIL_API_KEY to be set in environment.
    Returns False (without raising) if the service is not configured.
    """
    if not settings.EMAIL_API_URL:
        return False
    try:
        headers = {}
        if settings.EMAIL_API_KEY:
            headers["Authorization"] = f"Bearer {settings.EMAIL_API_KEY}"
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                settings.EMAIL_API_URL,
                json={"to": email, "subject": "FoodTrack Verification Code", "text": f"Your verification code: {code}"},
                headers=headers,
            )
            return resp.is_success
    except Exception:
        return False


# --- Phone OTP ---

def generate_phone_otp() -> str:
    return _uniform_otp_code()


async def send_sms_otp(phone: str, code: str) -> bool:
    """Send a 6-digit OTP via the configured SMS gateway.

    Requires SMS_API_URL and SMS_API_KEY to be set in environment.
    Returns False (without raising) if the service is not configured.
    """
    if not settings.SMS_API_URL:
        return False
    try:
        headers = {}
        if settings.SMS_API_KEY:
            headers["Authorization"] = f"Bearer {settings.SMS_API_KEY}"
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                settings.SMS_API_URL,
                json={"to": phone, "text": f"FoodTrack verification code: {code}"},
                headers=headers,
            )
            return resp.is_success
    except Exception:
        return False


# --- Email / phone verification ---

async def request_email_verification(db: AsyncSession, user: User) -> dict:
    """Generate and deliver an email verification code.

    The signed code token is stored on the user record (consumed on
    successful verification). When no email service is configured and
    RETURN_OTP_IN_DEV is enabled, the code is returned so the flow can
    be completed in a demo/test environment.
    """
    if not user.email:
        raise ValueError("No email address on file")
    code, token = generate_email_otp()
    user.mfa_otp_token = token
    await db.commit()
    sent = await send_email_otp(user.email, code)
    return _verification_result("email", user.email, code, sent)


async def verify_email_address(db: AsyncSession, user: User, code: str) -> None:
    if not user.mfa_otp_token:
        raise ValueError("No verification code has been requested")
    if not verify_email_otp(user.mfa_otp_token, code):
        raise ValueError("Invalid or expired verification code")
    user.mfa_otp_token = None
    user.email_verified = True
    await db.commit()


async def request_phone_verification(db: AsyncSession, user: User) -> dict:
    """Generate and deliver a phone verification code (see email flow)."""
    if not user.phone:
        raise ValueError("No phone number on file")
    code = generate_phone_otp()
    token = serializer.dumps(code)
    user.mfa_otp_token = token
    await db.commit()
    sent = await send_sms_otp(user.phone, code)
    return _verification_result("phone", user.phone, code, sent)


async def verify_phone_number(db: AsyncSession, user: User, code: str) -> None:
    if not user.mfa_otp_token:
        raise ValueError("No verification code has been requested")
    if not verify_email_otp(user.mfa_otp_token, code):
        raise ValueError("Invalid or expired verification code")
    user.mfa_otp_token = None
    user.phone_verified = True
    await db.commit()


def _verification_result(channel: str, target: str, code: str, sent: bool) -> dict:
    result: dict = {
        "sent": sent,
        "channel": channel,
        "target": target,
        "message": (
            "Verification code sent" if sent else
            "No email/SMS service configured — code returned for development/testing"
        ),
    }
    if not sent and settings.RETURN_OTP_IN_DEV:
        result["dev_code"] = code
    return result


# --- SSO / OAuth ---

SSO_PROVIDERS = ("google", "microsoft", "apple", "github")


def _b64url_decode(data: str) -> bytes:
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))


def _jwk_to_ec_pem(jwk: dict) -> str:
    """Convert an EC JWK (Apple signing keys) to a PEM subject public key."""
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ec

    x = int.from_bytes(_b64url_decode(jwk["x"]), "big")
    y = int.from_bytes(_b64url_decode(jwk["y"]), "big")
    public_key = ec.EllipticCurvePublicNumbers(x, y, ec.SECP256R1()).public_key()
    return public_key.public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")


def _apple_client_secret() -> str:
    """Build Apple's 5-minute-max ES256 client_secret (we use ~10 min)."""
    if not (settings.APPLE_TEAM_ID and settings.APPLE_KEY_ID and settings.APPLE_PRIVATE_KEY):
        raise ValueError("Apple SSO is not configured (APPLE_TEAM_ID / APPLE_KEY_ID / APPLE_PRIVATE_KEY required)")
    now = int(time.time())
    claims = {
        "iss": settings.APPLE_TEAM_ID,
        "iat": now,
        "exp": now + 600,
        "aud": "https://appleid.apple.com",
        "sub": settings.APPLE_CLIENT_ID,
    }
    return jwt.encode(
        claims, settings.APPLE_PRIVATE_KEY,
        algorithm="ES256", headers={"kid": settings.APPLE_KEY_ID},
    )


def _sso_config(provider: str) -> dict:
    if provider == "google":
        return {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "authorize_url": "https://accounts.google.com/o/oauth2/v2/auth",
            "token_url": "https://oauth2.googleapis.com/token",
            "scope": "openid email profile",
            "profile_url": "https://www.googleapis.com/oauth2/v3/userinfo",
            "uses_secret": True,
            "uses_pkce": True,
        }
    if provider == "microsoft":
        return {
            "client_id": settings.MICROSOFT_CLIENT_ID,
            "client_secret": settings.MICROSOFT_CLIENT_SECRET,
            "authorize_url": "https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
            "token_url": "https://login.microsoftonline.com/common/oauth2/v2.0/token",
            "scope": "openid email profile",
            "profile_url": "https://graph.microsoft.com/v1.0/me",
            "uses_secret": True,
            "uses_pkce": True,
        }
    if provider == "apple":
        return {
            "client_id": settings.APPLE_CLIENT_ID,
            "client_secret": _apple_client_secret,
            "authorize_url": "https://appleid.apple.com/auth/authorize",
            "token_url": "https://appleid.apple.com/auth/token",
            "scope": "name email",
            "uses_secret": True,
            "uses_pkce": True,
        }
    if provider == "github":
        return {
            "client_id": settings.GITHUB_CLIENT_ID,
            "client_secret": settings.GITHUB_CLIENT_SECRET,
            "authorize_url": "https://github.com/login/oauth/authorize",
            "token_url": "https://github.com/login/oauth/access_token",
            "scope": "read:user user:email",
            "uses_secret": True,
            "uses_pkce": False,
        }
    raise ValueError(f"Unsupported SSO provider: {provider}")


def _pkce_pair() -> tuple[str, str]:
    """Generate a PKCE code_verifier / code_challenge pair (S256)."""
    verifier = secrets.token_urlsafe(48)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    return verifier, challenge


def _sso_redirect_uri(provider: str) -> str:
    """Callback URL used to complete the OAuth flow for a provider.

    Derives the per-provider callback from SITE_URL so that configuring one
    provider (e.g. GOOGLE via SSO_REDIRECT_URI) never leaks its redirect URI
    onto another provider's authorize/exchange calls.
    """
    derived = f"{settings.SITE_URL}/api/v1/auth/sso/{provider}/callback"
    if settings.SSO_REDIRECT_URI and settings.SSO_REDIRECT_URI.endswith(f"/sso/{provider}/callback"):
        return settings.SSO_REDIRECT_URI
    return derived


def list_sso_providers() -> list[dict]:
    """Advertise SSO providers to the frontend.

    `client_id` is public and only used to build provider authorize URLs.
    `authorize_endpoint` is the backend endpoint the SPA should redirect to.
    """
    providers = [
        {
            "provider": "google",
            "enabled": bool(settings.GOOGLE_CLIENT_ID),
            "client_id": settings.GOOGLE_CLIENT_ID or None,
            "redirect_uri": _sso_redirect_uri("google"),
            "authorize_endpoint": "/api/v1/auth/sso/google/authorize",
        },
        {
            "provider": "microsoft",
            "enabled": bool(settings.MICROSOFT_CLIENT_ID),
            "client_id": settings.MICROSOFT_CLIENT_ID or None,
            "redirect_uri": _sso_redirect_uri("microsoft"),
            "authorize_endpoint": "/api/v1/auth/sso/microsoft/authorize",
        },
        {
            "provider": "apple",
            "enabled": bool(settings.APPLE_CLIENT_ID and settings.APPLE_TEAM_ID and settings.APPLE_KEY_ID and settings.APPLE_PRIVATE_KEY),
            "client_id": settings.APPLE_CLIENT_ID or None,
            "redirect_uri": _sso_redirect_uri("apple"),
            "authorize_endpoint": "/api/v1/auth/sso/apple/authorize",
            "reason": "Requires ES256 key configuration (APPLE_CLIENT_ID / APPLE_TEAM_ID / APPLE_KEY_ID / APPLE_PRIVATE_KEY)",
        },
        {
            "provider": "github",
            "enabled": bool(settings.GITHUB_CLIENT_ID and settings.GITHUB_CLIENT_SECRET),
            "client_id": settings.GITHUB_CLIENT_ID or None,
            "redirect_uri": _sso_redirect_uri("github"),
            "authorize_endpoint": "/api/v1/auth/sso/github/authorize",
        },
    ]
    return providers


def start_sso_authorization(provider: str, redirect_uri: str | None = None,
                            client_state: str | None = None) -> dict:
    """Step 1 of the OAuth2 authorization-code + PKCE flow.

    Builds the provider authorize URL. The `state` token is a short-lived
    signed JWT that carries the PKCE code_verifier and the client's redirect
    target, so the whole flow stays stateless server-side.
    """
    cfg = _sso_config(provider)
    if not cfg["client_id"]:
        raise ValueError(f"SSO provider '{provider}' is not configured (missing client id)")
    verifier, challenge = _pkce_pair()
    redirect_uri = redirect_uri or _sso_redirect_uri(provider)
    state = create_access_token(
        {"step": "sso", "provider": provider, "verifier": verifier,
         "redirect": redirect_uri, "cs": client_state or ""},
        expires_delta=10,
    )
    params: dict = {
        "client_id": cfg["client_id"],
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": cfg["scope"],
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    if provider == "apple":
        params["response_mode"] = "query"
    return {
        "provider": provider,
        "authorize_url": f"{cfg['authorize_url']}?{urlencode(params)}",
        "state": state,
        "code_verifier": verifier,
        "expires_in": 600,
    }


def _state_payload(state: str, provider: str) -> dict:
    payload = decode_access_token(state)
    if not payload or payload.get("step") != "sso" or payload.get("provider") != provider:
        raise ValueError("Invalid or expired SSO state")
    return payload


async def _exchange_code_for_tokens(
    provider: str, cfg: dict, code: str, verifier: str | None,
    redirect_uri: str | None = None,
) -> dict:
    """Step 2 — exchange the authorization code for provider tokens."""
    data: dict = {
        "grant_type": "authorization_code",
        "code": code,
        "client_id": cfg["client_id"],
        "redirect_uri": redirect_uri or _sso_redirect_uri(provider),
    }
    if cfg.get("uses_secret"):
        secret = cfg["client_secret"]() if callable(cfg["client_secret"]) else cfg["client_secret"]
        data["client_secret"] = secret
    if cfg.get("uses_pkce") and verifier:
        data["code_verifier"] = verifier

    headers = {"Accept": "application/json"}
    if provider == "github":
        headers["Accept"] = "application/json"
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(cfg["token_url"], data=data, headers=headers)
    if not resp.is_success:
        raise ValueError(f"SSO token exchange failed ({provider}): {resp.status_code}")
    body = resp.json()
    if "error" in body:
        raise ValueError(f"SSO token exchange error ({provider}): {body.get('error')}")
    return body


async def _profile_from_tokens(provider: str, cfg: dict, tokens: dict) -> dict:
    """Step 3 — resolve the authenticated profile from provider tokens."""
    access_token = tokens.get("access_token", "")
    if provider == "apple":
        id_token = tokens.get("id_token")
        if not id_token:
            raise ValueError("Apple SSO did not return an id_token")
        claims = await _verify_apple_id_token(id_token)
        return {
            "email": claims.get("email", ""),
            "name": claims.get("name", ""),
            "id": claims.get("sub", ""),
        }
    if provider == "github":
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                "https://api.github.com/user",
                headers={"Authorization": f"Bearer {access_token}", "Accept": "application/vnd.github+json"},
            )
            if not resp.is_success:
                raise ValueError("GitHub profile fetch failed")
            data = resp.json()
            email = data.get("email")
            if not email:
                emails_resp = await client.get(
                    "https://api.github.com/user/emails",
                    headers={"Authorization": f"Bearer {access_token}", "Accept": "application/vnd.github+json"},
                )
                if emails_resp.is_success:
                    emails = emails_resp.json()
                    primary = next((e for e in emails if e.get("primary")), emails[0] if emails else None)
                    email = (primary or {}).get("email", "")
            return {"email": email or "", "name": data.get("name") or data.get("login", ""), "id": str(data.get("id", ""))}
    # google / microsoft — userinfo endpoint with the provider access token
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            cfg["profile_url"],
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if not resp.is_success:
            raise ValueError(f"SSO profile fetch failed ({provider})")
        data = resp.json()
    if provider == "google":
        return {"email": data.get("email", ""), "name": data.get("name", ""), "id": data.get("sub", "")}
    if provider == "microsoft":
        email = data.get("mail") or data.get("userPrincipalName") or ""
        return {"email": email, "name": data.get("displayName", ""), "id": data.get("id", "")}
    raise ValueError(f"Unsupported SSO provider: {provider}")


async def _verify_apple_id_token(id_token: str) -> dict:
    """Verify Apple's id_token signature against Apple's public JWKS and
    validate issuer/audience claims."""
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get("https://appleid.apple.com/auth/keys")
        if not resp.is_success:
            raise ValueError("Apple signing keys unavailable")
        keys = resp.json().get("keys", [])
    header = jwt.get_unverified_header(id_token)
    jwk = next((k for k in keys if k.get("kid") == header.get("kid")), None)
    if not jwk:
        raise ValueError("Apple signing key not found")
    pem = _jwk_to_ec_pem(jwk)
    return jwt.decode(
        id_token, pem, algorithms=["ES256"],
        audience=settings.APPLE_CLIENT_ID,
        issuer="https://appleid.apple.com",
    )


async def verify_social_token(provider: str, token: str) -> dict | None:
    """Validate an already-issued provider access token (legacy client-token
    flow used by /auth/sso). Apple validates the id_token instead."""
    try:
        if provider == "apple":
            return await _verify_apple_id_token(token)
        cfg = _sso_config(provider)
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                cfg["profile_url"],
                headers={"Authorization": f"Bearer {token}"},
            )
            if resp.is_success:
                data = resp.json()
                if provider == "google":
                    return {"email": data.get("email", ""), "name": data.get("name", ""), "id": data.get("sub", "")}
                if provider == "microsoft":
                    email = data.get("mail") or data.get("userPrincipalName") or ""
                    return {"email": email, "name": data.get("displayName", ""), "id": data.get("id", "")}
                if provider == "github":
                    email = data.get("email") or ""
                    return {"email": email, "name": data.get("name") or data.get("login", ""), "id": str(data.get("id", ""))}
    except (NotImplementedError, ValueError):
        raise
    except Exception:
        pass
    return None


async def sso_login_or_register_profile(db: AsyncSession, provider: str, profile: dict) -> User:
    """Upsert a user from an SSO profile and return the user."""
    email = profile.get("email", "")
    if not email:
        raise ValueError("SSO provider did not return an email address")
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user:
        user = User(
            email=email, full_name=profile.get("name", email),
            sso_provider=provider, sso_id=profile.get("id", ""),
            hashed_password=hash_password(str(uuid.uuid4())), email_verified=True,
            user_type=UserType.ORGANIZATION,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
    elif not user.email_verified:
        user.email_verified = True
        await db.commit()
    return user


async def sso_login_or_register(db: AsyncSession, provider: str, token: str) -> tuple[User, str]:
    profile = await verify_social_token(provider, token)
    if not profile:
        raise ValueError("SSO verification failed")
    user = await sso_login_or_register_profile(db, provider, profile)
    jwt_token = create_access_token(_user_token_payload(user))
    return user, jwt_token


async def complete_sso_code_flow(db: AsyncSession, provider: str, code: str, state: str) -> User:
    """Server-side OAuth2 callback: verify state, exchange the code, upsert user."""
    payload = _state_payload(state, provider)
    cfg = _sso_config(provider)
    tokens = await _exchange_code_for_tokens(
        provider, cfg, code, payload.get("verifier"), payload.get("redirect"),
    )
    profile = await _profile_from_tokens(provider, cfg, tokens)
    return await sso_login_or_register_profile(db, provider, profile)


async def complete_sso_code_flow_with_verifier(
    db: AsyncSession, provider: str, code: str, state: str, code_verifier: str | None,
) -> User:
    """SPA-driven PKCE completion: the client supplies the code_verifier it
    received from /authorize instead of the one embedded in the state token."""
    payload = _state_payload(state, provider)
    cfg = _sso_config(provider)
    tokens = await _exchange_code_for_tokens(
        provider, cfg, code, code_verifier or payload.get("verifier"), payload.get("redirect"),
    )
    profile = await _profile_from_tokens(provider, cfg, tokens)
    return await sso_login_or_register_profile(db, provider, profile)


# --- WebAuthn / Biometrics ---

def generate_biometric_challenge() -> str:
    return str(uuid.uuid4())


def verify_biometric_assertion(credential_id: str, public_key: str, assertion_data: dict) -> bool:
    """Stub — WebAuthn assertion verification requires a proper FIDO2 library
    (e.g. py_webauthn). This function must not be called in production until
    a real implementation is in place."""
    raise NotImplementedError(
        "WebAuthn biometric assertion verification is not implemented. "
        "Integrate py_webauthn and configure relying-party origin before enabling."
    )


async def get_user_by_biometric_credential(db: AsyncSession, credential_id: str) -> User | None:
    result = await db.execute(select(User).where(User.biometric_credential_id == credential_id))
    return result.scalar_one_or_none()


async def update_profile(db: AsyncSession, user: User, data: dict) -> User:
    for field in ("full_name", "company", "phone", "alternate_email", "alternate_phone"):
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


def _user_token_payload(user: User) -> dict:
    return {
        "sub": str(user.id),
        "role": user.role.value,
        "user_type": user.user_type.value,
        "tenant_id": user.tenant_id,
    }


def serialize_user(u: User) -> dict:
    role_codes = [u.role.value]
    if u.roles:
        role_codes += [r.code for r in u.roles if r.code not in role_codes]
    return {
        "id": u.id,
        "email": u.email,
        "full_name": u.full_name,
        "company": u.company,
        "phone": u.phone,
        "alternate_email": u.alternate_email,
        "alternate_phone": u.alternate_phone,
        "role": u.role.value if hasattr(u.role, "value") else str(u.role),
        "user_type": u.user_type.value if hasattr(u.user_type, "value") else str(u.user_type),
        "roles": role_codes,
        "is_active": u.is_active,
        "email_verified": u.email_verified,
        "phone_verified": u.phone_verified,
        "totp_enabled": u.totp_enabled,
        "sso_provider": u.sso_provider,
        "tenant_id": u.tenant_id,
        "created_at": u.created_at.isoformat() if u.created_at else None,
    }


async def list_users(db: AsyncSession, page: int = 1) -> dict:
    from sqlalchemy import func
    q = select(User).order_by(User.created_at.desc())
    count_q = select(func.count()).select_from(q.subquery())
    total = (await db.execute(count_q)).scalar() or 0
    offset = (page - 1) * PAGE_SIZE_USERS
    items = (await db.execute(q.offset(offset).limit(PAGE_SIZE_USERS))).scalars().all()
    result = [serialize_user(u) for u in items]
    return {"users": result, "total": total, "page": page, "total_pages": max(1, (total + PAGE_SIZE_USERS - 1) // PAGE_SIZE_USERS)}


async def get_user_by_id(db: AsyncSession, user_id: int) -> User | None:
    return await db.get(User, user_id)


# Role → default account type, kept in sync when an admin assigns a role.
_DEFAULT_USER_TYPE_FOR_ROLE: dict[UserRole, UserType] = {
    UserRole.CLERK: UserType.OPERATIONS,
    UserRole.VERIFIER: UserType.OPERATIONS,
    UserRole.COURIER: UserType.OPERATIONS,
    UserRole.GOVERNMENT_AGENT: UserType.GOVERNMENT,
    UserRole.SUPERUSER: UserType.ORGANIZATION,
    UserRole.ADMIN: UserType.ORGANIZATION,
    UserRole.ENTERPRISE: UserType.ORGANIZATION,
    UserRole.VIEWER: UserType.ORGANIZATION,
}


async def update_user_role(db: AsyncSession, admin_user: User, target_user_id: int, new_role: UserRole) -> User:
    if admin_user.role not in (UserRole.SUPERUSER, UserRole.ADMIN):
        raise PermissionError("Only superusers and admins can change roles")
    if target_user_id == admin_user.id:
        raise ValueError("Cannot change your own role")
    target = await db.get(User, target_user_id)
    if not target:
        raise ValueError("User not found")
    # Superuser accounts can only be managed by another superuser
    if target.role == UserRole.SUPERUSER and admin_user.role != UserRole.SUPERUSER:
        raise PermissionError("Only a superuser can manage superuser accounts")
    # Granting superuser requires superuser privileges
    if new_role == UserRole.SUPERUSER and admin_user.role != UserRole.SUPERUSER:
        raise PermissionError("Only a superuser can grant the superuser role")
    target.role = new_role
    # Keep the account type coherent with field/regulator roles.
    target.user_type = _DEFAULT_USER_TYPE_FOR_ROLE.get(new_role, target.user_type)
    await db.commit()
    await db.refresh(target)
    return target


async def toggle_user_active(db: AsyncSession, admin_user: User, target_user_id: int) -> User:
    if admin_user.role not in (UserRole.SUPERUSER, UserRole.ADMIN):
        raise PermissionError("Only superusers and admins can toggle user status")
    if target_user_id == admin_user.id:
        raise ValueError("Cannot deactivate yourself")
    target = await db.get(User, target_user_id)
    if not target:
        raise ValueError("User not found")
    if target.role == UserRole.SUPERUSER and admin_user.role != UserRole.SUPERUSER:
        raise PermissionError("Only a superuser can manage superuser accounts")
    target.is_active = not target.is_active
    await db.commit()
    await db.refresh(target)
    return target
