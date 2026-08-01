"""Idempotent, incremental seed of platform accounts (tenant, superuser, admin)."""

import logging
import os
import secrets

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant import Tenant
from app.models.user import User, UserRole
from app.services.auth_service import hash_password

logger = logging.getLogger("app.startup")

# Password for seeded accounts comes from the environment. If unset, a
# one-time random secret is generated so accounts can never be logged into
# with a known default. Operators must set SEED_ADMIN_PASSWORD before seeding
# and distribute it out-of-band.
DEFAULT_PASSWORD = os.getenv("SEED_ADMIN_PASSWORD") or secrets.token_urlsafe(24)

DEMO_ACCOUNTS = [
    {
        "email": "digikiminvest@gmail.com",
        "full_name": "Ntanda Musa",
        "phone": "+256700677543",
        "alternate_email": "ntandadigi@gmail.com",
        "alternate_phone": "+256780698353",
        "company": "FoodTrack",
        "role": UserRole.SUPERUSER,
    },
    {
        "email": "digidanlpai@gmail.com",
        "full_name": "Musa Mwanguwanga",
        "phone": "+256746725134",
        "alternate_phone": "+256780135102",
        "company": "FoodTrack",
        "role": UserRole.ADMIN,
    },
]


async def seed_default_users(db: AsyncSession) -> dict:
    """
    Ensure the default tenant and the Superuser/Admin demo accounts exist.

    Accounts are matched by email; existing rows are left untouched (their
    password and contacts are never overwritten), so this is safe to re-run.
    """
    tenant = (await db.execute(select(Tenant).limit(1))).scalar_one_or_none()
    if not tenant:
        tenant = Tenant(
            name="FoodTrack",
            slug="foodtrack",
            tier="enterprise",
            is_active=True,
        )
        db.add(tenant)
        await db.commit()
        await db.refresh(tenant)
        logger.info({"msg": "Created default tenant", "slug": tenant.slug})

    created = 0
    existing = 0
    for account in DEMO_ACCOUNTS:
        row = (await db.execute(
            select(User).where(User.email == account["email"])
        )).scalar_one_or_none()
        if row:
            existing += 1
            continue
        user = User(
            email=account["email"],
            phone=account.get("phone"),
            alternate_email=account.get("alternate_email"),
            alternate_phone=account.get("alternate_phone"),
            full_name=account["full_name"],
            company=account.get("company"),
            role=account["role"],
            tenant_id=tenant.id,
            hashed_password=hash_password(DEFAULT_PASSWORD),
            email_verified=True,
            phone_verified=True,
            is_active=True,
        )
        db.add(user)
        created += 1
        logger.info({
            "msg": "Seeded demo account",
            "email": account["email"],
            "role": account["role"].value,
            "password_configured": bool(os.getenv("SEED_ADMIN_PASSWORD")),
        })

    await db.commit()
    return {"tenant_id": tenant.id, "created": created, "existing": existing}
