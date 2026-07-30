from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text

from app.models.retention import ArchivePolicy
from app.models.user import User, UserRole


async def create_archive_policy(db: AsyncSession, user: User, entity_type: str, retention_days: int) -> ArchivePolicy:
    if user.role != UserRole.ADMIN:
        raise PermissionError("Admin access required")

    policy = ArchivePolicy(entity_type=entity_type, retention_days=retention_days)
    db.add(policy)
    await db.commit()
    await db.refresh(policy)
    return policy


async def list_archive_policies(db: AsyncSession) -> list[dict]:
    rows = await db.execute(select(ArchivePolicy).order_by(ArchivePolicy.entity_type))
    return [{"id": p.id, "entity_type": p.entity_type, "retention_days": p.retention_days, "is_active": p.is_active} for p in rows.scalars().all()]


async def run_archival(db: AsyncSession, user: User) -> dict:
    if user.role != UserRole.ADMIN:
        raise PermissionError("Admin access required")

    policies = await db.execute(select(ArchivePolicy).where(ArchivePolicy.is_active == True))
    cutoff = datetime.now(timezone.utc)
    archived = {}

    for policy in policies.scalars().all():
        table_name = policy.entity_type
        days = policy.retention_days
        archive_table = policy.archive_to_table or f"{table_name}_archive"

        try:
            await db.execute(text(f"CREATE TABLE IF NOT EXISTS {archive_table} (LIKE {table_name} INCLUDING ALL)"))
            result = await db.execute(text(f"WITH moved AS (DELETE FROM {table_name} WHERE created_at < :cutoff RETURNING *) INSERT INTO {archive_table} SELECT * FROM moved RETURNING id"), {"cutoff": cutoff - timedelta(days=days)})
            count = len(result.all()) if result else 0
            archived[table_name] = count
        except Exception as e:
            archived[table_name] = str(e)

    await db.commit()
    return {"archived_count": archived, "cutoff_date": str(cutoff)}
