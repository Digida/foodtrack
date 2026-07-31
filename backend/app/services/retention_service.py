from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text

from app.models.retention import ArchivePolicy
from app.models.user import User, UserRole

# Tables that are permitted to be archived.
# entity_type in ArchivePolicy must match one of these exactly.
ALLOWED_ARCHIVE_TABLES = frozenset({
    "products",
    "batches",
    "shipments",
    "telemetry_readings",
    "telemetry_alerts",
    "search_logs",
    "event_logs",
    "enrichment_logs",
    "tracking_events",
})


async def create_archive_policy(
    db: AsyncSession, user: User, entity_type: str, retention_days: int
) -> ArchivePolicy:
    if user.role not in (UserRole.SUPERUSER, UserRole.ADMIN):
        raise PermissionError("Admin access required")

    if entity_type not in ALLOWED_ARCHIVE_TABLES:
        raise ValueError(
            f"Invalid entity_type '{entity_type}'. "
            f"Allowed tables: {sorted(ALLOWED_ARCHIVE_TABLES)}"
        )

    policy = ArchivePolicy(entity_type=entity_type, retention_days=retention_days)
    db.add(policy)
    await db.commit()
    await db.refresh(policy)
    return policy


async def list_archive_policies(db: AsyncSession) -> list[dict]:
    rows = await db.execute(select(ArchivePolicy).order_by(ArchivePolicy.entity_type))
    return [
        {
            "id": p.id,
            "entity_type": p.entity_type,
            "retention_days": p.retention_days,
            "is_active": p.is_active,
        }
        for p in rows.scalars().all()
    ]


async def run_archival(db: AsyncSession, user: User) -> dict:
    if user.role not in (UserRole.SUPERUSER, UserRole.ADMIN):
        raise PermissionError("Admin access required")

    policies_result = await db.execute(
        select(ArchivePolicy).where(ArchivePolicy.is_active == True)
    )
    cutoff_base = datetime.now(timezone.utc)
    archived: dict[str, int | str] = {}

    for policy in policies_result.scalars().all():
        table_name = policy.entity_type

        # Validate table name against whitelist to prevent SQL injection
        if table_name not in ALLOWED_ARCHIVE_TABLES:
            archived[table_name] = f"skipped: '{table_name}' is not in the allowed archive table list"
            continue

        archive_table = f"{table_name}_archive"
        cutoff = cutoff_base - timedelta(days=policy.retention_days)

        try:
            # PostgreSQL-specific: CREATE TABLE LIKE preserves column structure + constraints
            await db.execute(
                text(f"CREATE TABLE IF NOT EXISTS {archive_table} (LIKE {table_name} INCLUDING ALL)")
            )
            result = await db.execute(
                text(
                    f"WITH moved AS ("
                    f"  DELETE FROM {table_name} WHERE created_at < :cutoff RETURNING *"
                    f") INSERT INTO {archive_table} SELECT * FROM moved"
                ),
                {"cutoff": cutoff},
            )
            archived[table_name] = result.rowcount if result.rowcount is not None else 0
        except Exception as exc:
            archived[table_name] = f"error: {exc}"

    await db.commit()
    return {"archived_count": archived, "cutoff_date": cutoff_base.isoformat()}
