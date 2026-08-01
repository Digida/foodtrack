from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.user import User, UserRole, UserType
from app.schemas import (
    TokenResponse, UserDetailResponse, UserListResponse, OKResponse,
)
from app.services.auth_service import (
    register_user, authenticate_user, verify_mfa_token,
    enable_totp, confirm_totp,
    generate_email_otp, generate_phone_otp,
    send_email_otp, send_sms_otp,
    sso_login_or_register, list_sso_providers,
    start_sso_authorization, complete_sso_code_flow,
    complete_sso_code_flow_with_verifier,
    issue_refresh_token, rotate_refresh_token, revoke_refresh_token,
    revoke_all_user_tokens,
    generate_biometric_challenge,
    update_profile, change_password,
    list_users, get_user_by_id, update_user_role, toggle_user_active,
    serialize_user,
    request_email_verification, verify_email_address,
    request_phone_verification, verify_phone_number,
)
from app.services.rbac_service import (
    list_roles, list_permissions, assign_roles_to_user, set_user_type,
    create_custom_role, delete_role,
)
from app.utils.dependencies import (
    get_current_user, require_admin, require_permission,
)

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    email: str
    password: str
    full_name: str
    company: str | None = None
    phone: str | None = None
    tenant_id: int | None = None
    user_type: UserType = UserType.ORGANIZATION


class LoginRequest(BaseModel):
    email: str
    password: str


class MFATokenRequest(BaseModel):
    temp_token: str
    code: str


class SSOLoginRequest(BaseModel):
    provider: str
    token: str


class SSOTokenRequest(BaseModel):
    code: str
    state: str
    code_verifier: str | None = None


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str | None = None


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


class AssignRolesRequest(BaseModel):
    roles: list[str] = []


class SetUserTypeRequest(BaseModel):
    user_type: UserType


class CreateRoleRequest(BaseModel):
    code: str
    name: str
    description: str | None = None
    permissions: list[str] = []


def _client_ctx(request: Request) -> tuple[str | None, str | None]:
    ua = request.headers.get("user-agent")
    ip = request.client.host if request.client else None
    return (ua or "")[:255] or None, ip


# ─── Public Endpoints ──────────────────────────────────────────────────

@router.post("/register")
async def api_register(req: RegisterRequest, request: Request, db: AsyncSession = Depends(get_db)):
    try:
        user, token = await register_user(
            db, req.email, req.password, req.full_name, req.company,
            req.phone, req.tenant_id,
        )
        user.user_type = req.user_type
        await db.commit()
        refresh = await issue_refresh_token(db, user, *_client_ctx(request))
        return {"access_token": token, "refresh_token": refresh, "token_type": "bearer", "user": serialize_user(user)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/login")
async def api_login(req: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    try:
        user, token, mfa_info = await authenticate_user(db, req.email, req.password)
        if mfa_info:
            return mfa_info
        refresh = await issue_refresh_token(db, user, *_client_ctx(request))
        return {"access_token": token, "refresh_token": refresh, "token_type": "bearer", "user": serialize_user(user)}
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))


@router.post("/mfa-verify")
async def api_mfa_verify(req: MFATokenRequest, request: Request, db: AsyncSession = Depends(get_db)):
    try:
        user, token = await verify_mfa_token(db, req.temp_token, req.code)
        refresh = await issue_refresh_token(db, user, *_client_ctx(request))
        return {"access_token": token, "refresh_token": refresh, "token_type": "bearer", "user": serialize_user(user)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/refresh")
async def api_refresh(req: RefreshRequest, request: Request, db: AsyncSession = Depends(get_db)):
    try:
        user, new_refresh = await rotate_refresh_token(db, req.refresh_token, *_client_ctx(request))
        from app.services.auth_service import create_access_token, _user_token_payload
        access = create_access_token(_user_token_payload(user))
        return {"access_token": access, "refresh_token": new_refresh, "token_type": "bearer", "user": serialize_user(user)}
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))


@router.post("/logout")
async def api_logout(req: LogoutRequest, user: User = Depends(get_current_user),
                     db: AsyncSession = Depends(get_db)):
    if req.refresh_token:
        try:
            await revoke_refresh_token(db, req.refresh_token)
        except Exception:
            pass
    else:
        await revoke_all_user_tokens(db, user)
    return {"status": "logged_out"}


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


# ─── SSO ────────────────────────────────────────────────────────────────

@router.post("/sso")
async def api_sso_login(req: SSOLoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    try:
        user, token = await sso_login_or_register(db, req.provider, req.token)
        refresh = await issue_refresh_token(db, user, *_client_ctx(request))
        return {"access_token": token, "refresh_token": refresh, "token_type": "bearer", "user": serialize_user(user)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/sso-providers")
async def api_sso_providers():
    return {"providers": list_sso_providers()}


@router.get("/sso/{provider}/authorize")
async def api_sso_authorize(
    provider: str,
    redirect_uri: str | None = Query(None, description="Frontend page to land on after login"),
    state: str | None = Query(None, description="Opaque client state echoed back"),
):
    try:
        return start_sso_authorization(provider, redirect_uri, state)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/sso/{provider}/callback")
async def api_sso_callback(
    provider: str,
    code: str = Query(...),
    state: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """Provider → browser → backend. Exchanges the code server-side, then
    redirects the browser to the SPA callback page with fresh tokens."""
    try:
        user = await complete_sso_code_flow(db, provider, code, state)
        access = await _sso_tokens(db, user)
        return RedirectResponse(url=f"{settings.SITE_URL}/sso.html#access_token={access[0]}&refresh_token={access[1]}")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/sso/{provider}/token")
async def api_sso_token(req: SSOTokenRequest, provider: str, request: Request,
                        db: AsyncSession = Depends(get_db)):
    """SPA-driven PKCE completion — exchange the code using a verifier supplied
    by the client (from /authorize) and return tokens as JSON."""
    try:
        user = await complete_sso_code_flow_with_verifier(db, provider, req.code, req.state, req.code_verifier)
        from app.services.auth_service import create_access_token, _user_token_payload
        refresh = await issue_refresh_token(db, user, *_client_ctx(request))
        return {"access_token": create_access_token(_user_token_payload(user)),
                "refresh_token": refresh, "token_type": "bearer", "user": serialize_user(user)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


async def _sso_tokens(db: AsyncSession, user: User) -> tuple[str, str]:
    from app.services.auth_service import create_access_token, _user_token_payload
    return create_access_token(_user_token_payload(user)), await issue_refresh_token(db, user)


# ─── Email / phone verification ───────────────────────────────────────

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


# ─── Authenticated User Endpoints ─────────────────────────────────────

@router.get("/me", response_model=UserDetailResponse)
async def get_me(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from app.services.rbac_service import get_user_permissions
    data = serialize_user(user)
    data["permissions"] = sorted(await get_user_permissions(db, user))
    return data


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


# ─── RBAC: roles & permissions ────────────────────────────────────────

@router.get("/roles")
async def api_list_roles(user: User = Depends(require_permission("roles.read")),
                         db: AsyncSession = Depends(get_db)):
    return {"roles": await list_roles(db)}


@router.get("/permissions")
async def api_list_permissions(user: User = Depends(require_permission("roles.read"))):
    return {"permissions": list_permissions()}


@router.post("/roles")
async def api_create_role(req: CreateRoleRequest,
                          user: User = Depends(require_permission("roles.manage")),
                          db: AsyncSession = Depends(get_db)):
    try:
        role = await create_custom_role(db, user, req.code, req.name, req.permissions, req.description)
        return {"code": role.code, "name": role.name, "is_system": role.is_system}
    except (ValueError, PermissionError) as e:
        raise HTTPException(status_code=400 if isinstance(e, ValueError) else 403, detail=str(e))


@router.delete("/roles/{role_code}")
async def api_delete_role(role_code: str,
                          user: User = Depends(require_permission("roles.manage")),
                          db: AsyncSession = Depends(get_db)):
    try:
        await delete_role(db, user, role_code)
        return {"deleted": True}
    except (ValueError, PermissionError) as e:
        raise HTTPException(status_code=404 if isinstance(e, ValueError) else 403, detail=str(e))


# ─── Admin Endpoints ──────────────────────────────────────────────────

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
        return {"id": target.id, "role": target.role.value, "user_type": target.user_type.value}
    except (ValueError, PermissionError) as e:
        raise HTTPException(status_code=400 if isinstance(e, ValueError) else 403, detail=str(e))


@router.post("/users/{user_id}/roles")
async def api_assign_roles(
    user_id: int,
    req: AssignRolesRequest,
    admin: User = Depends(require_permission("users.manage")),
    db: AsyncSession = Depends(get_db),
):
    try:
        target = await assign_roles_to_user(db, admin, user_id, req.roles)
        from app.services.rbac_service import user_role_codes
        return {"id": target.id, "roles": user_role_codes(target)}
    except (ValueError, PermissionError) as e:
        raise HTTPException(status_code=400 if isinstance(e, ValueError) else 403, detail=str(e))


@router.put("/users/{user_id}/type")
async def api_set_user_type(
    user_id: int,
    req: SetUserTypeRequest,
    admin: User = Depends(require_permission("users.manage")),
    db: AsyncSession = Depends(get_db),
):
    try:
        target = await set_user_type(db, admin, user_id, req.user_type)
        return {"id": target.id, "user_type": target.user_type.value}
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
