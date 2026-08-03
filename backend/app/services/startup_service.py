"""
Incremental background startup service.

Responsibilities
----------------
1. Run Alembic migrations (piecemeal — only pending revisions).
2. Run database seeding (incremental — only missing items are added).
3. Report live progress so API callers and the UI can show status.

Design principles
-----------------
- The application starts and accepts requests IMMEDIATELY.  The startup
  tasks run in a background asyncio task and never block the web server.
- State is held in a single module-level `_state` dict so any request
  handler can query it via `get_startup_status()`.
- Each seed "chunk" is checked with an existence query before inserting;
  nothing is duplicated across restarts.
- If a section of data a request depends on is not yet ready, the handler
  can call `require_seeded(section)` which returns a descriptive 503 with
  an ETA.
"""

import asyncio
import logging
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session

logger = logging.getLogger("app.startup")

# ── Module-level state ────────────────────────────────────────────────────────

_state: dict[str, Any] = {
    "ready":       False,          # True once ALL tasks complete
    "phase":       "pending",      # pending | migrating | seeding | done | error
    "started_at":  None,
    "finished_at": None,
    "migration": {
        "status":   "pending",     # pending | running | done | error
        "current":  None,
        "head":     None,
        "detail":   None,
    },
    "seeding": {
        "status":          "pending",
        "sections": {},            # section_name -> { status, expected, seeded, missing }
        "total_inserted":  0,
        "detail":          None,
    },
    "errors": [],
}

# ── Public API ────────────────────────────────────────────────────────────────

def get_startup_status() -> dict:
    """Return a snapshot of current startup progress (safe to serialise to JSON)."""
    return {
        "ready":       _state["ready"],
        "phase":       _state["phase"],
        "started_at":  _state["started_at"],
        "finished_at": _state["finished_at"],
        "uptime_seconds": (
            int(time.time() - _state["started_at"])
            if _state["started_at"] else 0
        ),
        "migration":   dict(_state["migration"]),
        "seeding": {
            "status":         _state["seeding"]["status"],
            "total_inserted": _state["seeding"]["total_inserted"],
            "sections":       {
                k: dict(v) for k, v in _state["seeding"]["sections"].items()
            },
            "detail": _state["seeding"]["detail"],
        },
        "errors": list(_state["errors"]),
    }


def is_section_ready(section: str) -> bool:
    """Check whether a named seed section has completed successfully."""
    sec = _state["seeding"]["sections"].get(section)
    return sec is not None and sec.get("status") == "done"


def require_section_ready(section: str) -> dict | None:
    """
    If the named section is not yet seeded, return a 503-compatible error
    payload.  Returns None if the section is ready.
    """
    if is_section_ready(section):
        return None
    sec = _state["seeding"]["sections"].get(section, {})
    return {
        "error":   "data_not_ready",
        "section": section,
        "status":  sec.get("status", "pending"),
        "message": (
            f"The '{section}' dataset is still being initialised in the background. "
            f"Please retry in a few seconds. "
            f"Check /api/v1/startup/status for live progress."
        ),
    }


# ── Main background task ──────────────────────────────────────────────────────

async def run_startup_tasks(backend_dir: Path) -> None:
    """
    Entry point — called once from the FastAPI lifespan as
    `asyncio.create_task(run_startup_tasks(backend_dir))`.
    """
    _state["started_at"] = time.time()
    _state["phase"] = "migrating"
    logger.info({"msg": "Background startup tasks starting"})

    try:
        await _run_migrations(backend_dir)
    except Exception as exc:
        _record_error("migration", str(exc))

    _state["phase"] = "seeding"
    try:
        await _run_seeding()
    except Exception as exc:
        _record_error("seeding", str(exc))

    _state["phase"] = "done"
    _state["ready"] = True
    _state["finished_at"] = time.time()
    elapsed = round(_state["finished_at"] - _state["started_at"], 1)
    logger.info({"msg": "Background startup tasks complete", "elapsed_s": elapsed})


# ── Migration ─────────────────────────────────────────────────────────────────

async def _run_migrations(backend_dir: Path) -> None:
    """
    Run `alembic upgrade head` in a thread pool so it doesn't block the
    event loop.

    SQLite (dev): tables are managed by SQLAlchemy create_all in init_db().
    Alembic is skipped — running it against a create_all DB causes conflicts.

    PostgreSQL (prod): Alembic is the sole schema authority.
    """
    from app.config import settings
    ms = _state["migration"]
    ms["status"] = "running"

    # Skip Alembic for SQLite — init_db() already ran create_all
    if settings.DATABASE_URL.startswith("sqlite"):
        ms["status"] = "done"
        ms["detail"] = "SQLite detected — schema managed by create_all, Alembic skipped"
        ms["current"] = "n/a (sqlite)"
        ms["head"] = "n/a (sqlite)"
        logger.info({"msg": "Migrations: skipped for SQLite", "detail": ms["detail"]})
        return

    try:
        current = await _alembic_current(backend_dir)
        head    = await _alembic_head(backend_dir)
        ms["current"] = current
        ms["head"]    = head

        if current == head and current is not None:
            ms["status"] = "done"
            ms["detail"] = f"Already at head ({head}) — no migrations needed"
            logger.info({"msg": "Migrations: already at head", "rev": head})
            return

        logger.info({"msg": "Migrations: running", "current": current, "head": head})
        ms["detail"] = f"Upgrading from {current or 'base'} to {head}"

        result = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: subprocess.run(
                [sys.executable, "-m", "alembic", "upgrade", "head"],
                cwd=str(backend_dir),
                capture_output=True,
                text=True,
            ),
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"Alembic exited {result.returncode}: {result.stderr.strip()}"
            )

        ms["current"] = await _alembic_current(backend_dir)
        ms["status"]  = "done"
        ms["detail"]  = f"Migrated to {ms['current']}"
        logger.info({"msg": "Migrations: complete", "rev": ms["current"]})

    except Exception as exc:
        ms["status"] = "error"
        ms["detail"] = str(exc)
        raise


async def _alembic_current(backend_dir: Path) -> str | None:
    result = await asyncio.get_event_loop().run_in_executor(
        None,
        lambda: subprocess.run(
            [sys.executable, "-m", "alembic", "current"],
            cwd=str(backend_dir),
            capture_output=True,
            text=True,
        ),
    )
    for line in result.stdout.splitlines():
        # "abc123ef (head)" or "abc123ef"
        stripped = line.strip()
        if stripped and not stripped.startswith("INFO"):
            rev = stripped.split(" ")[0]
            if len(rev) >= 8:
                return rev
    return None


async def _alembic_head(backend_dir: Path) -> str | None:
    result = await asyncio.get_event_loop().run_in_executor(
        None,
        lambda: subprocess.run(
            [sys.executable, "-m", "alembic", "heads"],
            cwd=str(backend_dir),
            capture_output=True,
            text=True,
        ),
    )
    heads: list[str] = []
    for line in result.stdout.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("INFO"):
            rev = stripped.split(" ")[0]
            if len(rev) >= 8:
                heads.append(rev)
    if len(heads) > 1:
        raise RuntimeError(
            f"Alembic has multiple heads ({', '.join(heads)}) — "
            "merge them before migrating"
        )
    return heads[0] if heads else None


# ── Seeding ───────────────────────────────────────────────────────────────────

async def _run_seeding() -> None:
    """
    Incremental seeder.  For each section we check what already exists in
    the database and only insert the missing rows.  Each section is
    committed independently so partial progress survives a restart.
    """
    ss = _state["seeding"]
    ss["status"] = "running"

    try:
        await _seed_rbac()
        await _seed_taxonomy_and_items()
        await _seed_collections()
        await _seed_users()
        ss["status"] = "done"
        logger.info({
            "msg": "Seeding complete",
            "total_inserted": ss["total_inserted"],
        })
    except Exception as exc:
        ss["status"] = "error"
        ss["detail"] = str(exc)
        raise


# ── RBAC seeding ──────────────────────────────────────────────────────────

async def _seed_rbac() -> None:
    """Idempotently seed the permission catalog + system roles (see
    rbac_service.seed_system_rbac). Must run before user seeding so seeded
    accounts could be given extra roles."""
    from app.services.rbac_service import seed_system_rbac

    sec = _state["seeding"]["sections"]["rbac"] = {
        "status":   "pending",
        "expected": 0,
        "seeded":   0,
        "missing":  0,
    }
    async with async_session() as db:
        result = await seed_system_rbac(db)
    sec["expected"] = result["permissions"] + result["roles"]
    sec["seeded"]   = result["permissions"] + result["roles"]
    sec["missing"]  = 0
    sec["status"]   = "done"
    logger.info({"msg": "RBAC roles + permissions seeded", **result})


# ── Taxonomy / item seeding ───────────────────────────────────────────────────

async def _seed_taxonomy_and_items() -> None:
    """
    Idempotent, incremental taxonomy seed.

    The seed data is imported lazily so we don't load ~3 000 lines of
    catalogue data on every cold start.  Each category is processed
    independently and only missing items are inserted.
    """
    # Lazy import — keeps startup time low if seeding not needed
    from seed_food_items import FOOD_CATEGORIES, LOCAL_NAMES, NUTRITION
    from seed_more_items import (
        NEW_CATEGORIES, LOCAL_NAMES_NEW, NUTRITION_NEW,
    )
    from seed_industry_categories import (
        INDUSTRY_CATEGORIES, LOCAL_NAMES_INDUSTRY, NUTRITION_INDUSTRY,
    )

    all_categories: dict = {}
    all_categories.update(FOOD_CATEGORIES)
    all_categories.update(NEW_CATEGORIES)
    all_categories.update(INDUSTRY_CATEGORIES)

    all_local_names: dict = {}
    all_local_names.update(LOCAL_NAMES)
    all_local_names.update(LOCAL_NAMES_NEW)
    all_local_names.update(LOCAL_NAMES_INDUSTRY)

    all_nutrition: dict = {}
    all_nutrition.update(NUTRITION)
    all_nutrition.update(NUTRITION_NEW)
    all_nutrition.update(NUTRITION_INDUSTRY)

    # Announce all sections up-front so the status endpoint shows them
    for cat_name in all_categories:
        n_expected = len(all_categories[cat_name]["items"])
        _state["seeding"]["sections"][cat_name] = {
            "status":   "pending",
            "expected": n_expected,
            "seeded":   0,
            "missing":  n_expected,
        }

    async with async_session() as db:
        # ── Taxonomy root ──────────────────────────────────────────────────
        tax = await _ensure_taxonomy(db)

        # ── Build lookup caches ────────────────────────────────────────────
        existing_codes = await _get_existing_codes(db)
        existing_nodes = await _get_existing_nodes(db, tax.id)

        # ── Seed each category ────────────────────────────────────────────
        cat_index = len(existing_nodes)

        for cat_name, cat_data in all_categories.items():
            sec = _state["seeding"]["sections"][cat_name]
            items_in_cat = cat_data["items"]

            # Determine how many are already seeded
            already = sum(1 for it in items_in_cat if it[0] in existing_codes)
            missing_items = [it for it in items_in_cat if it[0] not in existing_codes]

            sec["seeded"]  = already
            sec["missing"] = len(missing_items)

            if not missing_items:
                sec["status"] = "done"
                logger.debug({"msg": "seed_section_skip", "section": cat_name, "count": already})
                continue

            sec["status"] = "running"
            logger.info({
                "msg": "seed_section_start",
                "section": cat_name,
                "missing": len(missing_items),
                "already": already,
            })

            # Ensure node exists
            node = existing_nodes.get(cat_data["code"])
            if not node:
                cat_index += 1
                node = await _ensure_node(db, tax.id, cat_data, cat_name, cat_index)
                existing_nodes[cat_data["code"]] = node

            # Insert missing items one by one (incremental, not bulk)
            for item_tuple in missing_items:
                await _insert_item(
                    db, node, item_tuple,
                    all_local_names, all_nutrition,
                )
                existing_codes.add(item_tuple[0])
                sec["seeded"]  += 1
                sec["missing"] -= 1
                _state["seeding"]["total_inserted"] += 1

                # Commit in small batches to make progress durable
                if _state["seeding"]["total_inserted"] % 10 == 0:
                    await db.commit()
                    logger.debug({
                        "msg": "seed_progress",
                        "total_inserted": _state["seeding"]["total_inserted"],
                    })

            await db.commit()
            sec["status"] = "done"
            logger.info({
                "msg": "seed_section_done",
                "section": cat_name,
                "inserted": sec["seeded"],
            })

            # Yield to the event loop between categories so the server
            # stays responsive during large seed operations
            await asyncio.sleep(0)


async def _seed_collections() -> None:
    """
    Idempotent, incremental collection seed.

    Derives one collection per top-level taxonomy node so the
    categorization layer (collections) is wired into the cataloguing
    architecture (taxonomy nodes / items).
    """
    from app.services.collection_service import seed_collections_from_taxonomy

    sec = _state["seeding"]["sections"]["collections"] = {
        "status":   "pending",
        "expected": 0,
        "seeded":   0,
        "missing":  0,
    }

    async with async_session() as db:
        result = await seed_collections_from_taxonomy(db)

    sec["expected"] = result["nodes"]
    sec["seeded"]   = result["items"]
    sec["missing"]  = 0
    sec["status"]   = "done"
    _state["seeding"]["total_inserted"] += result["items"] + result["collections"]
    logger.info({"msg": "Collections seeded from taxonomy", **result})


# ── User / tenant seeding ─────────────────────────────────────────────────────

async def _seed_users() -> None:
    """
    Idempotent, incremental user seed.

    Creates the default tenant plus the Superuser and Admin demo accounts
    used for client walkthroughs (see user_seed_service.DEMO_ACCOUNTS).
    """
    from app.services.user_seed_service import seed_default_users

    sec = _state["seeding"]["sections"]["users"] = {
        "status":   "pending",
        "expected": 0,
        "seeded":   0,
        "missing":  0,
    }

    async with async_session() as db:
        result = await seed_default_users(db)

    sec["expected"] = result["created"] + result["existing"]
    sec["seeded"]   = result["created"]
    sec["missing"]  = 0
    sec["status"]   = "done"
    _state["seeding"]["total_inserted"] += result["created"]
    logger.info({"msg": "Users seeded", **result})


# ── DB helpers ────────────────────────────────────────────────────────────────

async def _ensure_taxonomy(db: AsyncSession):
    from app.models.taxonomy import Taxonomy
    result = await db.execute(
        select(Taxonomy).where(Taxonomy.name == "Food Kingdom")
    )
    tax = result.scalar_one_or_none()
    if not tax:
        tax = Taxonomy(
            name="Food Kingdom",
            description="Comprehensive food and agricultural product taxonomy",
            icon="🌾",
            is_active=True,
        )
        db.add(tax)
        await db.commit()
        await db.refresh(tax)
        logger.info({"msg": "Created taxonomy: Food Kingdom", "id": tax.id})
    return tax


async def _get_existing_codes(db: AsyncSession) -> set[str]:
    from app.models.taxonomy import TaxonomyItem
    result = await db.execute(select(TaxonomyItem.code))
    return set(result.scalars().all())


async def _get_existing_nodes(db: AsyncSession, taxonomy_id: int) -> dict:
    from app.models.taxonomy import TaxonomyNode
    result = await db.execute(
        select(TaxonomyNode).where(TaxonomyNode.taxonomy_id == taxonomy_id)
    )
    return {node.code: node for node in result.scalars().all()}


async def _ensure_node(
    db: AsyncSession, taxonomy_id: int, cat_data: dict,
    cat_name: str, sort_index: int,
):
    from app.models.taxonomy import TaxonomyNode
    node = TaxonomyNode(
        taxonomy_id=taxonomy_id,
        parent_id=None,
        code=cat_data["code"],
        name=cat_name.replace("_", " ").title(),
        description=cat_data["description"],
        sort_order=sort_index * 10,
        is_active=True,
    )
    db.add(node)
    await db.commit()
    await db.refresh(node)
    return node


async def _insert_item(
    db: AsyncSession,
    node,
    item_tuple: tuple,
    local_names: dict,
    nutrition: dict,
) -> None:
    from app.models.taxonomy import TaxonomyItem, ItemName, ItemAttribute

    (
        code, common_name, scientific_name, genre,
        phylum, tax_class, order_name, family,
        gestation, local_uses,
    ) = item_tuple[:10]

    parts = gestation.split("-") if gestation else []
    gestation_period = "-".join(parts[:2]) if parts else ""
    gestation_unit = ""
    if gestation_period:
        unit_match = re.search(r"(month|week|year)s?\b", gestation)
        gestation_unit = (unit_match.group(1) + "s") if unit_match else "months"

    item = TaxonomyItem(
        node_id=node.id,
        code=code,
        common_name=common_name,
        scientific_name=scientific_name,
        genre=genre,
        phylum=phylum,
        tax_class=tax_class,
        order_name=order_name,
        family=family,
        gestation_period=gestation_period,
        gestation_unit=gestation_unit,
        local_uses=local_uses,
        description=(
            f"{scientific_name} — {common_name}. {local_uses}. "
            f"Classification: {phylum} > {tax_class} > {order_name} > {family}."
        ),
        is_active=True,
    )
    db.add(item)
    await db.flush()  # get item.id without committing

    # Primary name
    db.add(ItemName(item_id=item.id, language="en",         name=common_name,      is_primary=True))
    db.add(ItemName(item_id=item.id, language="scientific", name=scientific_name,  is_primary=False))

    for lang, lname in local_names.get(code, []):
        db.add(ItemName(item_id=item.id, language=lang, name=lname, is_primary=False))

    for key, value, unit in nutrition.get(code, []):
        db.add(ItemAttribute(item_id=item.id, key=key, value=str(value), unit=unit))


# ── Error recording ───────────────────────────────────────────────────────────

def _record_error(phase: str, detail: str) -> None:
    entry = {
        "phase": phase,
        "detail": detail,
        "ts": datetime.now(timezone.utc).isoformat(),
    }
    _state["errors"].append(entry)
    logger.error({"msg": "startup_error", **entry})
