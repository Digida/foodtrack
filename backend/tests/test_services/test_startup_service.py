"""Tests for startup_service (state management, migration runner, seed helpers)."""
import copy
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.models.taxonomy import TaxonomyItem
from app.services import startup_service as ss

INITIAL_STATE = {
    "ready": False,
    "phase": "pending",
    "started_at": None,
    "finished_at": None,
    "migration": {"status": "pending", "current": None, "head": None, "detail": None},
    "seeding": {"status": "pending", "sections": {}, "total_inserted": 0, "detail": None},
    "errors": [],
}


@pytest.fixture(autouse=True)
def reset_state():
    ss._state = copy.deepcopy(INITIAL_STATE)
    yield
    ss._state = copy.deepcopy(INITIAL_STATE)


def test_get_startup_status_initial():
    out = ss.get_startup_status()
    assert out["ready"] is False
    assert out["phase"] == "pending"
    assert out["uptime_seconds"] == 0
    assert out["migration"]["status"] == "pending"
    assert out["seeding"]["status"] == "pending"


def test_get_startup_status_uptime():
    ss._state["started_at"] = time.time() - 5
    out = ss.get_startup_status()
    assert 0 < out["uptime_seconds"] < 60


def test_section_ready_and_require():
    assert ss.is_section_ready("users") is False
    blocked = ss.require_section_ready("users")
    assert blocked["error"] == "data_not_ready"
    assert blocked["section"] == "users"
    ss._state["seeding"]["sections"]["users"] = {"status": "done", "expected": 1, "seeded": 1, "missing": 0}
    assert ss.is_section_ready("users") is True
    assert ss.require_section_ready("users") is None


def test_record_error():
    ss._record_error("migration", "boom")
    assert len(ss._state["errors"]) == 1
    assert ss._state["errors"][0]["phase"] == "migration"
    assert ss._state["errors"][0]["detail"] == "boom"
    assert "ts" in ss._state["errors"][0]


def _set_sqlite():
    from app.config import settings
    settings.DATABASE_URL = "sqlite+aiosqlite:///:memory:"


def _set_postgres():
    from app.config import settings
    settings.DATABASE_URL = "postgresql+asyncpg://user:pass@localhost/db"


def _fake_subprocess(results):
    def fake_run(cmd, **kwargs):
        for key, out in results.items():
            if key in cmd:
                return SimpleNamespace(returncode=0, stdout=out, stderr="")
        return SimpleNamespace(returncode=0, stdout="", stderr="")
    return fake_run


async def test_run_startup_tasks_sqlite(monkeypatch):
    _set_sqlite()
    called = []

    async def fake_seeding():
        called.append(True)
        ss._state["seeding"]["sections"]["users"] = {"status": "done", "expected": 1, "seeded": 1, "missing": 0}
    monkeypatch.setattr(ss, "_run_seeding", fake_seeding)
    await ss.run_startup_tasks(Path("."))
    assert called == [True]
    assert ss._state["migration"]["status"] == "done"
    assert ss._state["phase"] == "done"
    assert ss._state["ready"] is True
    assert ss._state["finished_at"] is not None


async def test_run_startup_tasks_migration_error_skips_seed(monkeypatch):
    _set_postgres()

    async def fail_migrations(backend_dir):
        ss._state["migration"]["status"] = "error"
        raise RuntimeError("alembic down")
    async def fake_seeding():
        raise AssertionError("seeding should be skipped")
    monkeypatch.setattr(ss, "_run_migrations", fail_migrations)
    monkeypatch.setattr(ss, "_run_seeding", fake_seeding)
    await ss.run_startup_tasks(Path("."))
    assert ss._state["phase"] == "error"
    assert ss._state["ready"] is True
    assert len(ss._state["errors"]) == 1
    assert ss._state["errors"][0]["phase"] == "migration"


async def test_run_startup_tasks_seeding_error_recorded(monkeypatch):
    _set_sqlite()

    async def ok_migrations(backend_dir):
        ss._state["migration"]["status"] = "done"
    async def fail_seeding():
        raise RuntimeError("seed blew up")
    monkeypatch.setattr(ss, "_run_migrations", ok_migrations)
    monkeypatch.setattr(ss, "_run_seeding", fail_seeding)
    await ss.run_startup_tasks(Path("."))
    assert ss._state["phase"] == "done"
    assert ss._state["ready"] is True
    assert any(e["phase"] == "seeding" for e in ss._state["errors"])


async def test_run_migrations_sqlite_skips_alembic(monkeypatch):
    _set_sqlite()
    await ss._run_migrations(Path("."))
    ms = ss._state["migration"]
    assert ms["status"] == "done"
    assert "SQLite detected" in ms["detail"]
    assert ms["current"] == "n/a (sqlite)"


async def test_run_migrations_at_head(monkeypatch):
    _set_postgres()
    fake = _fake_subprocess({"current": "abc123ef (head)\n", "heads": "abc123ef (head)\n"})
    monkeypatch.setattr(ss.subprocess, "run", fake)
    await ss._run_migrations(Path("."))
    ms = ss._state["migration"]
    assert ms["status"] == "done"
    assert "Already at head" in ms["detail"]


async def test_run_migrations_upgrade(monkeypatch):
    _set_postgres()
    upgraded = [False]
    def fake_run(cmd, **kwargs):
        if "upgrade" in cmd:
            upgraded[0] = True
            return SimpleNamespace(returncode=0, stdout="def456gh (head)\n", stderr="")
        if "heads" in cmd:
            return SimpleNamespace(returncode=0, stdout="def456gh (head)\n", stderr="")
        return SimpleNamespace(returncode=0,
                               stdout="def456gh (head)\n" if upgraded[0] else "abc123ef\n",
                               stderr="")
    monkeypatch.setattr(ss.subprocess, "run", fake_run)
    await ss._run_migrations(Path("."))
    ms = ss._state["migration"]
    assert ms["status"] == "done"
    assert ms["current"] == "def456gh"
    assert "Migrated to" in ms["detail"]


async def test_run_migrations_failure(monkeypatch):
    _set_postgres()
    def fail_run(cmd, **kwargs):
        return SimpleNamespace(returncode=1, stdout="", stderr="boom")
    monkeypatch.setattr(ss.subprocess, "run", fail_run)
    with pytest.raises(RuntimeError):
        await ss._run_migrations(Path("."))
    assert ss._state["migration"]["status"] == "error"
    assert "boom" in ss._state["migration"]["detail"]


async def test_alembic_multi_head_error(monkeypatch):
    _set_postgres()
    def fake_run(cmd, **kwargs):
        return SimpleNamespace(returncode=0, stdout="abc123ef\nxyz789ab\n", stderr="")
    monkeypatch.setattr(ss.subprocess, "run", fake_run)
    with pytest.raises(RuntimeError, match="multiple heads"):
        await ss._run_migrations(Path("."))
    assert ss._state["migration"]["status"] == "error"


async def test_ensure_taxonomy_idempotent(db):
    tax1 = await ss._ensure_taxonomy(db)
    assert tax1.name == "Food Kingdom"
    tax2 = await ss._ensure_taxonomy(db)
    assert tax2.id == tax1.id


async def test_get_existing_codes_and_nodes(db):
    tax = await ss._ensure_taxonomy(db)
    node = await ss._ensure_node(db, tax.id, {"code": "fruit", "description": "d"}, "Fresh Fruits", 1)
    item = TaxonomyItem(node_id=node.id, code="MANGO-1", common_name="Mango")
    db.add(item)
    await db.commit()
    codes = await ss._get_existing_codes(db)
    assert "MANGO-1" in codes
    nodes = await ss._get_existing_nodes(db, tax.id)
    assert "fruit" in nodes


async def test_insert_item(db):
    tax = await ss._ensure_taxonomy(db)
    node = await ss._ensure_node(db, tax.id, {"code": "veg", "description": "d"}, "Vegetables", 1)
    item_tuple = (
        "TOMATO-1", "Tomato", "Solanum lycopersicum", "Nightshade",
        "Magnoliophyta", "Magnoliopsida", "Solanales", "Solanaceae",
        "3-4 months", "eaten fresh",
    )
    local_names = {"TOMATO-1": [("ar", "طماطم"), ("fr", "Tomate")]}
    nutrition = {"TOMATO-1": [("calories", 18, "kcal"), ("protein", 0.9, "g")]}
    await ss._insert_item(db, node, item_tuple, local_names, nutrition)
    await db.commit()
    from sqlalchemy import select

    from app.models.taxonomy import ItemAttribute, ItemName
    item = (await db.execute(select(TaxonomyItem).where(TaxonomyItem.code == "TOMATO-1"))).scalar_one()
    assert item.gestation_period == "3-4 months"
    assert item.gestation_unit == "months"
    names = (await db.execute(select(ItemName).where(ItemName.item_id == item.id))).scalars().all()
    langs = {n.language for n in names}
    assert langs == {"en", "scientific", "ar", "fr"}
    attrs = (await db.execute(select(ItemAttribute).where(ItemAttribute.item_id == item.id))).scalars().all()
    assert {a.key for a in attrs} == {"calories", "protein"}


async def test_insert_item_no_gestation(db):
    tax = await ss._ensure_taxonomy(db)
    node = await ss._ensure_node(db, tax.id, {"code": "meat", "description": "d"}, "Meat", 1)
    item_tuple = ("BEEF-1", "Beef", "Bos taurus", "Mammal", "Chordata", "Mammalia", "Artiodactyla", "Bovidae", None, "meat")
    await ss._insert_item(db, node, item_tuple, {}, {})
    await db.commit()
    from sqlalchemy import select
    item = (await db.execute(select(TaxonomyItem).where(TaxonomyItem.code == "BEEF-1"))).scalar_one()
    assert item.gestation_period == ""
    assert item.gestation_unit == ""
