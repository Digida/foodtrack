"""Role-Based Access Control (RBAC) service.

Central permission catalog + default role matrix. Every role maps to a set of
permissions, and a user's effective permissions are the union of:

1. the static default matrix for their primary `role` column (always applies,
   so nothing breaks before the DB seed runs or when roles are customized), and
2. any permissions attached to Role rows in the DB for that primary role and
   for the user's extra M2M-assigned roles.

Role codes are stable strings so they can be referenced from JWT claims,
routes and the frontend: superuser, admin, enterprise, verifier, clerk,
courier, auditor, government_agent, viewer.
"""
import logging

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rbac import Role, Permission, role_permissions, user_roles
from app.models.user import User, UserRole, UserType

logger = logging.getLogger("app.rbac")

# ── Permission catalog ────────────────────────────────────────────────────
# resource -> { action -> description } — code is f"{resource}.{action}".
PERMISSION_CATALOG: dict[str, dict[str, str]] = {
    "system": {
        "admin": "Full platform configuration access (superuser only)",
        "read": "Read platform-level configuration and startup status",
    },
    "users": {
        "read": "List and view user accounts",
        "manage": "Create, update, deactivate users and assign roles/types",
    },
    "roles": {
        "read": "View roles and permissions",
        "manage": "Create roles and assign them to users",
    },
    "tenants": {
        "read": "View tenant details",
        "manage": "Create/update tenants and tiers",
    },
    "items": {
        "read": "View taxonomy items and attributes",
        "manage": "Create/update/delete taxonomy items",
    },
    "products": {
        "read": "View products",
        "manage": "Create/update/delete products",
    },
    "certificates": {
        "read": "View certificates",
        "issue": "Issue certificates",
        "verify": "Verify certificate chains and validity",
        "approve": "Approve/reject certificate requests",
    },
    "batches": {
        "read": "View batches",
        "manage": "Create/update batches and batch status",
    },
    "warehouses": {
        "read": "View warehouses, zones and items",
        "manage": "Create/update warehouses",
    },
    "inventory": {
        "read": "View inventory levels",
        "manage": "Record inventory movements and reconcile",
    },
    "shipments": {
        "read": "View shipments and tracking",
        "manage": "Create/update shipments and tracking events",
    },
    "cargo": {
        "read": "View cargo registrations",
        "manage": "Register and update cargo",
    },
    "collections": {
        "read": "View collections",
        "manage": "Create/update collections",
    },
    "rates": {
        "read": "View item rate cards",
        "manage": "Create/update item rates",
    },
    "compliance": {
        "read": "Run compliance checks and get document lists",
        "manage": "Maintain compliance rules and documents",
    },
    "analytics": {
        "read": "View analytics dashboards",
    },
    "enrichment": {
        "run": "Trigger AI item enrichment",
    },
    "events": {
        "read": "View event logs",
        "publish": "Publish events",
        "manage": "Manage webhooks",
    },
    "telemetry": {
        "read": "Query telemetry readings and alerts",
        "ingest": "Ingest sensor telemetry",
    },
    "api_keys": {
        "manage": "Create and revoke developer API keys",
    },
    "tiers": {
        "read": "View pricing tiers",
        "manage": "Update tenant tier",
    },
    "retention": {
        "manage": "Manage retention policies and run archival",
    },
    "monitoring": {
        "read": "View health, metrics and SLA",
    },
    "suppliers": {
        "read": "View suppliers and scorecards",
        "manage": "Create/update suppliers and scorecards",
    },
    "insurance": {
        "read": "View insurance policies",
        "manage": "Create policies and manage claims",
    },
    "recalls": {
        "read": "View recalls",
        "manage": "Initiate and update recalls",
    },
    "esg": {
        "read": "View ESG / carbon footprint data",
        "manage": "Record carbon footprints",
    },
    "commerce": {
        "read": "View commerce / bulking data",
        "manage": "Manage registers, deals and settlements",
        "jobs": "Accept and complete pipeline jobs (clerk/verifier/courier)",
    },
    "gov": {
        "read": "Access government system integration",
    },
    "i18n": {
        "read": "Use translation endpoints",
    },
    "search": {
        "use": "Use search",
    },
    "verify": {
        "public": "Resolve public scan verification",
    },
    "operations": {
        "access": "Meta-permission: any operational (non-read-only) account",
    },
    "enterprise": {
        "access": "Meta-permission: enterprise, admin or superuser level access",
    },
}

ALL_PERMISSIONS: list[str] = [
    f"{resource}.{action}"
    for resource, actions in PERMISSION_CATALOG.items()
    for action in actions
]


def _expand(codes: set[str]) -> set[str]:
    """Expand a set of role codes into permission codes, honouring '*'.
    Falls back to the static catalog so it works before any DB seeding."""
    perms: set[str] = set()
    for code in codes:
        mapping = ROLE_PERMISSION_CODES.get(code, set())
        if "*" in mapping:
            perms |= set(ALL_PERMISSIONS)
        else:
            perms |= mapping
    return perms


# ── Default role → permission matrix ──────────────────────────────────────

# Shared read-only building blocks (kept explicit for auditability).
_READ_BASE = {
    "items.read", "products.read", "batches.read", "warehouses.read",
    "inventory.read", "shipments.read", "cargo.read", "collections.read",
    "rates.read", "compliance.read", "analytics.read", "events.read",
    "telemetry.read", "suppliers.read", "insurance.read", "recalls.read",
    "esg.read", "commerce.read", "i18n.read", "search.use", "verify.public",
    "tiers.read", "users.read", "roles.read",
}

ROLE_PERMISSION_CODES: dict[str, set[str]] = {
    "superuser": {"*"},
    "admin": set(ALL_PERMISSIONS) - {"system.admin", "tenants.manage"},
    "enterprise": {
        "items.read", "items.manage",
        "products.read", "products.manage",
        "certificates.read", "certificates.issue", "certificates.verify", "certificates.approve",
        "batches.read", "batches.manage",
        "warehouses.read", "warehouses.manage",
        "inventory.read", "inventory.manage",
        "shipments.read", "shipments.manage",
        "cargo.read", "cargo.manage",
        "collections.read", "collections.manage",
        "rates.read", "rates.manage",
        "compliance.read", "compliance.manage",
        "analytics.read", "enrichment.run",
        "events.read", "events.publish", "events.manage",
        "telemetry.read", "telemetry.ingest",
        "api_keys.manage",
        "tiers.read", "retention.manage", "monitoring.read",
        "suppliers.read", "suppliers.manage",
        "insurance.read", "insurance.manage",
        "recalls.read", "recalls.manage",
        "esg.read", "esg.manage",
        "commerce.read", "commerce.manage", "commerce.jobs",
        "gov.read", "i18n.read", "search.use", "verify.public",
        "users.read", "roles.read",
        "enterprise.access", "operations.access",
    },
    "verifier": {
        "items.read", "products.read",
        "certificates.read", "certificates.issue", "certificates.verify", "certificates.approve",
        "compliance.read", "compliance.manage",
        "batches.read", "shipments.read", "cargo.read", "inventory.read",
        "analytics.read", "telemetry.read",
        "commerce.read", "commerce.jobs",
        "events.read", "recalls.read", "suppliers.read",
        "i18n.read", "search.use", "verify.public",
        "operations.access",
    },
    "clerk": {
        "items.read", "products.read",
        "batches.read", "batches.manage",
        "warehouses.read", "inventory.read", "inventory.manage",
        "shipments.read", "cargo.read",
        "commerce.read", "commerce.manage", "commerce.jobs",
        "analytics.read", "telemetry.read", "telemetry.ingest",
        "i18n.read", "search.use", "verify.public",
        "operations.access",
    },
    "courier": {
        "items.read", "products.read",
        "shipments.read", "shipments.manage",
        "cargo.read", "inventory.read",
        "telemetry.read", "telemetry.ingest",
        "commerce.read", "commerce.jobs",
        "i18n.read", "search.use", "verify.public",
        "operations.access",
    },
    "auditor": _READ_BASE | {
        "certificates.read", "certificates.verify",
        "gov.read", "monitoring.read",
        "operations.access",
    },
    "government_agent": {
        "gov.read", "compliance.read", "compliance.manage",
        "certificates.read", "certificates.verify",
        "items.read", "products.read", "shipments.read", "cargo.read",
        "analytics.read", "recalls.read",
        "i18n.read", "search.use", "verify.public",
        "operations.access",
    },
    "viewer": {
        "items.read", "products.read",
        "i18n.read", "search.use", "verify.public",
    },
}

ROLE_NAMES: dict[str, str] = {
    "superuser": "Superuser",
    "admin": "Administrator",
    "enterprise": "Enterprise",
    "verifier": "Verifier",
    "clerk": "Clerk",
    "courier": "Courier",
    "auditor": "Auditor",
    "government_agent": "Government Agent",
    "viewer": "Viewer",
}

ROLE_DESCRIPTIONS: dict[str, str] = {
    "superuser": "Platform owner — full access to every entity and configuration.",
    "admin": "Tenant administrator — manages users, certificates, compliance and operations for their organisation.",
    "enterprise": "Buyer/importer company account — runs products, batches, shipments, cargo, certs and commerce.",
    "verifier": "Inspects and certifies stock — verifies certificate chains and approves certificate requests.",
    "clerk": "Warehouse/field clerk — receives goods, records inventory and drives bulking pipeline packing.",
    "courier": "Moves stock — updates shipments, ingests telemetry and completes courier jobs.",
    "auditor": "Read-only reviewer — audits items, certificates, compliance, monitoring and records.",
    "government_agent": "Regulator (e.g. Dubai Municipality / MOCCAE) — compliance, certificates and gov integration.",
    "viewer": "Read-only viewer of catalogue and search.",
}


# ── Public helpers ────────────────────────────────────────────────────────

async def get_user_permissions(db: AsyncSession, user: User) -> set[str]:
    """Effective permission set for a user.

    Always starts from the static matrix for the primary role, then merges in
    any extra permissions carried by Role rows in the DB (the primary role row
    plus M2M-assigned roles). DB lookups that fail (unmigrated DB, tests
    before seeding) are tolerated so the static matrix alone still applies.
    """
    perms = _expand({user.role.value})
    role_codes = {user.role.value}
    if user.roles:
        role_codes |= {r.code for r in user.roles}
    try:
        result = await db.execute(
            select(Permission.code)
            .join(role_permissions, role_permissions.c.permission_id == Permission.id)
            .join(Role, Role.id == role_permissions.c.role_id)
            .where(Role.code.in_(list(role_codes)))
        )
        perms |= set(result.scalars().all())
    except Exception as exc:  # noqa: BLE001 — tolerate unseeded/missing tables
        logger.debug({"msg": "rbac_db_lookup_failed_falling_back_to_static", "error": str(exc)})
    return perms


async def has_permission(db: AsyncSession, user: User, code: str) -> bool:
    return code in await get_user_permissions(db, user)


def user_role_codes(user: User) -> list[str]:
    codes = [user.role.value]
    if user.roles:
        codes += [r.code for r in user.roles if r.code not in codes]
    return codes


# ── Seeding ───────────────────────────────────────────────────────────────

async def seed_system_rbac(db: AsyncSession) -> dict:
    """Idempotently create the permission catalog + system roles + links."""
    perms_by_code: dict[str, Permission] = {}
    existing_perms = (await db.execute(select(Permission))).scalars().all()
    for p in existing_perms:
        perms_by_code[p.code] = p
    created_perms = 0
    for resource, actions in PERMISSION_CATALOG.items():
        for action, description in actions.items():
            code = f"{resource}.{action}"
            if code not in perms_by_code:
                row = Permission(code=code, resource=resource, action=action, description=description)
                db.add(row)
                perms_by_code[code] = row
                created_perms += 1
    await db.flush()

    roles_by_code: dict[str, Role] = {}
    existing_roles = (await db.execute(
        select(Role).where(Role.is_system.is_(True), Role.tenant_id.is_(None))
    )).scalars().all()
    for r in existing_roles:
        roles_by_code[r.code] = r

    created_roles = 0
    for code in ROLE_PERMISSION_CODES:
        role = roles_by_code.get(code)
        if role is None:
            role = Role(
                code=code,
                name=ROLE_NAMES.get(code, code.title()),
                description=ROLE_DESCRIPTIONS.get(code),
                is_system=True,
                tenant_id=None,
            )
            db.add(role)
            roles_by_code[code] = role
            created_roles += 1
    await db.flush()

    # Refresh permission links so role changes are picked up on reseed.
    # Load the collection first: reading/assigning `role.permissions` on a
    # flushed object would trigger an async-unsafe lazy load, so preload it
    # via an explicit async refresh.
    for code, role in roles_by_code.items():
        expected = set(ALL_PERMISSIONS) if "*" in ROLE_PERMISSION_CODES[code] else ROLE_PERMISSION_CODES[code]
        await db.refresh(role, ["permissions"])
        current = {p.code for p in role.permissions}
        if current != expected:
            role.permissions = [perms_by_code[c] for c in sorted(expected)]
            logger.info({"msg": "rbac_role_permissions_synced", "role": code, "count": len(expected)})

    await db.commit()
    return {
        "permissions": len(perms_by_code),
        "roles": len(roles_by_code),
        "created_permissions": created_perms,
        "created_roles": created_roles,
    }


# ── Role / permission listing ─────────────────────────────────────────────

async def list_roles(db: AsyncSession) -> list[dict]:
    """All roles (system + tenant custom) with their permission codes."""
    rows = (await db.execute(select(Role).order_by(Role.is_system.desc(), Role.code))).scalars().all()
    result = []
    for role in rows:
        codes = {p.code for p in role.permissions}
        if not codes:
            codes = ROLE_PERMISSION_CODES.get(role.code, set())
        result.append({
            "code": role.code,
            "name": role.name,
            "description": role.description,
            "is_system": role.is_system,
            "tenant_id": role.tenant_id,
            "permissions": sorted(codes),
        })
    return result


def list_permissions() -> list[dict]:
    return [
        {"code": f"{resource}.{action}", "resource": resource, "action": action, "description": description}
        for resource, actions in PERMISSION_CATALOG.items()
        for action, description in actions.items()
    ]


# ── User role / type assignment (admin) ───────────────────────────────────

async def assign_roles_to_user(
    db: AsyncSession, admin_user: User, target_user_id: int, role_codes: list[str],
) -> User:
    """Set the extra (M2M) roles for a user, replacing the previous set.

    Admin/superuser role escalation is guarded exactly like the primary-role
    flow in auth_service.update_user_role. Role codes are validated against
    existing Role rows (system roles are always seeded).
    """
    if admin_user.role not in (UserRole.SUPERUSER, UserRole.ADMIN):
        raise PermissionError("Only superusers and admins can assign roles")
    target = await db.get(User, target_user_id)
    if not target:
        raise ValueError("User not found")
    if target_user_id == admin_user.id:
        raise ValueError("Cannot change your own roles")
    if target.role == UserRole.SUPERUSER and admin_user.role != UserRole.SUPERUSER:
        raise PermissionError("Only a superuser can manage superuser accounts")
    if any(c == "superuser" for c in role_codes) and admin_user.role != UserRole.SUPERUSER:
        raise PermissionError("Only a superuser can grant the superuser role")

    roles = []
    if role_codes:
        rows = (await db.execute(select(Role).where(Role.code.in_(role_codes)))).scalars().all()
        by_code = {r.code: r for r in rows}
        missing = set(role_codes) - set(by_code)
        if missing:
            raise ValueError(f"Unknown roles: {', '.join(sorted(missing))}")
        roles = [by_code[c] for c in role_codes]
    await db.refresh(target, ["roles"])
    target.roles = roles
    await db.commit()
    await db.refresh(target, ["roles"])
    return target


async def set_user_type(db: AsyncSession, admin_user: User, target_user_id: int, user_type: UserType) -> User:
    if admin_user.role not in (UserRole.SUPERUSER, UserRole.ADMIN):
        raise PermissionError("Only superusers and admins can set user types")
    target = await db.get(User, target_user_id)
    if not target:
        raise ValueError("User not found")
    if target.role == UserRole.SUPERUSER and admin_user.role != UserRole.SUPERUSER:
        raise PermissionError("Only a superuser can manage superuser accounts")
    target.user_type = user_type
    await db.commit()
    await db.refresh(target)
    return target


async def create_custom_role(
    db: AsyncSession, admin_user: User, code: str, name: str,
    permission_codes: list[str], description: str | None = None,
) -> Role:
    """Create a tenant-scoped custom role (roles.manage permission)."""
    if admin_user.role not in (UserRole.SUPERUSER, UserRole.ADMIN):
        raise PermissionError("Only superusers and admins can create roles")
    code = code.strip().lower().replace(" ", "_")
    if not code or not name:
        raise ValueError("Role code and name are required")
    existing = (await db.execute(select(Role).where(Role.code == code, Role.tenant_id == admin_user.tenant_id))).scalar_one_or_none()
    if existing:
        raise ValueError(f"Role '{code}' already exists for this tenant")
    permissions = []
    if permission_codes:
        rows = (await db.execute(select(Permission).where(Permission.code.in_(permission_codes)))).scalars().all()
        by_code = {p.code: p for p in rows}
        missing = set(permission_codes) - set(by_code)
        if missing:
            raise ValueError(f"Unknown permissions: {', '.join(sorted(missing))}")
        permissions = list(by_code.values())
    role = Role(
        code=code, name=name, description=description,
        is_system=False, tenant_id=admin_user.tenant_id,
        permissions=permissions,
    )
    db.add(role)
    await db.commit()
    await db.refresh(role)
    return role


async def delete_role(db: AsyncSession, admin_user: User, role_code: str) -> None:
    """Delete a tenant custom role. System roles cannot be deleted."""
    role = (await db.execute(
        select(Role).where(Role.code == role_code, Role.tenant_id == admin_user.tenant_id)
    )).scalar_one_or_none()
    if not role:
        raise ValueError("Role not found for this tenant")
    if role.is_system:
        raise PermissionError("System roles cannot be deleted")
    await db.execute(delete(user_roles).where(user_roles.c.role_id == role.id))
    await db.delete(role)
    await db.commit()
