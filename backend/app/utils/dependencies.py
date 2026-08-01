import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.user import User, UserRole
from app.models.tenant import Tenant
from app.services.auth_service import decode_access_token, hash_password
from app.services.rbac_service import get_user_permissions

# auto_error=False makes HTTPBearer return None instead of raising 403
# when the Authorization header is absent. We raise 401 ourselves.
bearer_scheme = HTTPBearer(auto_error=False)

# System user used to attribute anonymous (unregistered) actions. It can never
# log in (random password). It carries a restricted role so anonymous requests
# cannot pass ADMIN/ENTERPRISE role checks in the service layer — anonymous
# actions that require real privileges must be explicitly login-gated instead.
SYSTEM_USER_EMAIL = "system@foodtrack.local"


async def get_system_user(db: AsyncSession) -> User:
    result = await db.execute(select(User).where(User.email == SYSTEM_USER_EMAIL))
    user = result.scalar_one_or_none()
    if user is not None:
        return user
    user = User(
        email=SYSTEM_USER_EMAIL,
        full_name="FoodTrack System",
        company="FoodTrack",
        role=UserRole.VIEWER,
        hashed_password=hash_password(uuid.uuid4().hex),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def _user_from_credentials(
    credentials: HTTPAuthorizationCredentials | None,
    db: AsyncSession,
) -> User | None:
    if credentials is None:
        return None
    payload = decode_access_token(credentials.credentials)
    if payload is None:
        return None
    user_id = payload.get("sub")
    if user_id is None:
        return None
    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        return None
    return user


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    user = await _user_from_credentials(credentials, db)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


async def get_current_user_or_guest(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Return the authenticated user, or the system user for anonymous requests.

    Used by endpoints that must stay usable for unregistered users while still
    attributing writes to a real user record.
    """
    user = await _user_from_credentials(credentials, db)
    if user is None:
        user = await get_system_user(db)
    return user


async def get_current_tenant(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Tenant | None:
    if not user.tenant_id:
        return None
    tenant = await db.get(Tenant, user.tenant_id)
    return tenant


async def require_admin(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> User:
    """RBAC-backed admin gate — requires the `users.manage` permission
    (granted to admins and superusers by the default role matrix)."""
    perms = await get_user_permissions(db, user)
    if "users.manage" not in perms:
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


async def require_superuser(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> User:
    perms = await get_user_permissions(db, user)
    if "system.admin" not in perms:
        raise HTTPException(status_code=403, detail="Superuser access required")
    return user


async def require_enterprise_or_admin(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> User:
    perms = await get_user_permissions(db, user)
    if "enterprise.access" not in perms:
        raise HTTPException(status_code=403, detail="Enterprise or Admin access required")
    return user


async def require_verifier_or_above(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> User:
    """Operation-capable gate — blocks read-only VIEWER accounts (and the
    anonymous system user). Grants access to clerks, verifiers, couriers,
    auditors, government agents, enterprises, admins and superusers."""
    perms = await get_user_permissions(db, user)
    if "operations.access" not in perms:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    return user


def require_permission(code: str):
    """Dependency factory — require a specific permission, e.g.
    `Depends(require_permission("certificates.approve"))`."""
    async def _check(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> User:
        perms = await get_user_permissions(db, user)
        if code not in perms:
            raise HTTPException(status_code=403, detail=f"Permission required: {code}")
        return user
    return _check
