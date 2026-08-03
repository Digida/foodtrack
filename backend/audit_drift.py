"""Audit: compare model metadata (Base.metadata) against the schema produced
by `alembic upgrade head` on a fresh SQLite DB. Reports columns/table drift
and type mismatches. Read-only against the DB; does NOT modify anything."""
import sys
from sqlalchemy import create_engine, MetaData, inspect

DB = sys.argv[1] if len(sys.argv) > 1 else "/tmp/audit_ft.db"

from app.models import *  # noqa: F401,F403
from app.database import Base

model_meta: MetaData = Base.metadata

eng = create_engine(f"sqlite:///{DB}")
db_meta = MetaData()
db_meta.reflect(bind=eng)
db_insp = inspect(eng)

model_tables = set(model_meta.tables.keys())
db_tables = set(db_meta.tables.keys())

print("=== TABLES missing FROM migration (in models only) ===")
for t in sorted(model_tables - db_tables):
    print("  MODEL-ONLY TABLE:", t)
print("=== TABLES missing FROM models (in migration only) ===")
for t in sorted(db_tables - model_tables):
    print("  MIGR-ONLY TABLE:", t)

print("\n=== COLUMN DRIFT per shared table ===")
for t in sorted(model_tables & db_tables):
    mcols = {c.name: c for c in model_meta.tables[t].columns}
    dcols = {c["name"]: c for c in db_insp.get_columns(t)}
    only_m = set(mcols) - set(dcols)
    only_d = set(dcols) - set(mcols)
    if only_m:
        print(f"  [{t}] MODEL-ONLY columns: {sorted(only_m)}")
    if only_d:
        print(f"  [{t}] MIGR-ONLY columns: {sorted(only_d)}")

print("\n=== TYPE MISMATCHES (str != str) ===")
for t in sorted(model_tables & db_tables):
    mcols = {c.name: c for c in model_meta.tables[t].columns}
    dcols = {c["name"]: c for c in db_insp.get_columns(t)}
    for name in set(mcols) & set(dcols):
        mt = str(mcols[name].type)
        dt = str(dcols[name]["type"])
        # normalize enum/varchar reporting
        if mt != dt:
            print(f"  [{t}.{name}] model={mt}  migr={dt}")
