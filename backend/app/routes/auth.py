from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User, UserRole
from app.schemas import (
    TokenResponse, UserDetailResponse, UserListResponse, OKResponse,
)
from app.services.auth_service import (
    register_user, authenticate_user, verify_mfa_token,
    enable_totp, confirm_totp,
    generate_email_otp, generate_phone_otp,
    send_email_otp, send_sms_otp,
    sso_login_or_register, list_sso_providers,
    generate_biometric_challenge,
    update_profile, change_password,
    list_users, get_user_by_id, update_user_role, toggle_user_active,
    serialize_user,
    request_email_verification, verify_email_address,
    request_phone_verification, verify_phone_number,
)
from app.utils.dependencies import get_current_user, require_admin

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    email: str
    password: str
    full_name: str
    company: str | None = None
    phone: str | None = None
    tenant_id: int | None = None


class LoginRequest(BaseModel):
    email: str
    password: str


class MFATokenRequest(BaseModel):
    temp_token: str
    code: str


class SSOLoginRequest(BaseModel):
    provider: str
    token: str


class TOTPVerifyRequest(BaseModel):
    code: str


class UpdateProfileRequest(BaseModel):
    full_name: str | None = None
    company: str | None = None
    phone: str | None = None
    alternate_email: str | None = None
    alternate_phone: str | None = None


class VerifyCodeRequest(BaseModel):
    code: str


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


class UpdateRoleRequest(BaseModel):
    user_id: int
    role: UserRole


# ─── Public Endpoints ──────────────────────────────────────────

@router.post("/register")
async def api_register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    try:
        user, token = await register_user(db, req.email, req.password, req.full_name, req.company, req.phone, req.tenant_id)
        return {"access_token": token, "token_type": "bearer", "user": serialize_user(user)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/login")
async def api_login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    try:
        user, token, mfa_info = await authenticate_user(db, req.email, req.password)
        if mfa_info:
            return mfa_info
        return {"access_token": token, "token_type": "bearer", "user": serialize_user(user)}
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))


@router.post("/mfa-verify")
async def api_mfa_verify(req: MFATokenRequest, db: AsyncSession = Depends(get_db)):
    try:
        user, token = await verify_mfa_token(db, req.temp_token, req.code)
        return {"access_token": token, "token_type": "bearer", "user": serialize_user(user)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/setup-totp")
async def setup_totp(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await enable_totp(user, db)
    return result


@router.post("/verify-totp")
async def verify_totp_setup(req: TOTPVerifyRequest, user: User = Depends(get_current_user),
                             db: AsyncSession = Depends(get_db)):
    try:
        await confirm_totp(user, req.code, db)
        return {"status": "totp_enabled"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/sso")
async def api_sso_login(req: SSOLoginRequest, db: AsyncSession = Depends(get_db)):
    try:
        user, token = await sso_login_or_register(db, req.provider, req.token)
        return {"access_token": token, "token_type": "bearer", "user": serialize_user(user)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/sso-providers")
async def api_sso_providers():
    return {"providers": list_sso_providers()}


# ─── Email / phone verification ───────────────────────────────

@router.post("/email-otp")
async def api_email_otp(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    try:
        return await request_email_verification(db, user)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/verify-email")
async def api_verify_email(req: VerifyCodeRequest, user: User = Depends(get_current_user),
                           db: AsyncSession = Depends(get_db)):
    try:
        await verify_email_address(db, user, req.code)
        return {"status": "email_verified", "email_verified": True}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/phone-otp")
async def api_phone_otp(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    try:
        return await request_phone_verification(db, user)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/verify-phone")
async def api_verify_phone(req: VerifyCodeRequest, user: User = Depends(get_current_user),
                           db: AsyncSession = Depends(get_db)):
    try:
        await verify_phone_number(db, user, req.code)
        return {"status": "phone_verified", "phone_verified": True}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/biometric-challenge")
async def biometric_challenge(user: User = Depends(get_current_user)):
    return {"challenge": generate_biometric_challenge()}


# ─── Authenticated User Endpoints ─────────────────────────────

@router.get("/me", response_model=UserDetailResponse)
async def get_me(user: User = Depends(get_current_user)):
    return serialize_user(user)


@router.put("/me", response_model=UserDetailResponse)
async def update_me(req: UpdateProfileRequest, user: User = Depends(get_current_user),
                    db: AsyncSession = Depends(get_db)):
    try:
        updated = await update_profile(db, user, req.model_dump(exclude_unset=True))
        return serialize_user(updated)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/change-password", response_model=OKResponse)
async def api_change_password(req: ChangePasswordRequest, user: User = Depends(get_current_user),
                               db: AsyncSession = Depends(get_db)):
    try:
        await change_password(db, user, req.old_password, req.new_password)
        return {"status": "password_changed"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ─── Admin Endpoints ──────────────────────────────────────────

@router.get("/users")
async def api_list_users(
    page: int = Query(1, ge=1),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await list_users(db, page)


@router.get("/users/{user_id}")
async def api_get_user(
    user_id: int,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    u = await get_user_by_id(db, user_id)
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    return serialize_user(u)


@router.put("/users/role")
async def api_update_role(
    req: UpdateRoleRequest,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    try:
        target = await update_user_role(db, admin, req.user_id, req.role)
        return {"id": target.id, "role": target.role.value}
    except (ValueError, PermissionError) as e:
        raise HTTPException(status_code=400 if isinstance(e, ValueError) else 403, detail=str(e))


@router.post("/users/{user_id}/toggle-active")
async def api_toggle_active(
    user_id: int,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    try:
        target = await toggle_user_active(db, admin, user_id)
        return {"id": target.id, "is_active": target.is_active}
    except (ValueError, PermissionError) as e:
        raise HTTPException(status_code=400 if isinstance(e, ValueError) else 403, detail=str(e))
