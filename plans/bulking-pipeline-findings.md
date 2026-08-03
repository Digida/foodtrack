# Investor Bulking Pipeline — QA Findings & Verification Report

> **Scope:** Investor bulking + escrow cycle (build, verify, fix)
> **Last Verified:** 2026-08-03
> **Status:** ✅ All verification gates green

---

## 1. Executive Summary

The investor bulking pipeline — the commercial centerpiece for the Dubai/hospitality
market — has been built end-to-end and verified error-free. An investor creates a
bulking register for a taxonomy item, members of the sourcing entity perform
collate → escrow deposit → assign jobs → pack → certify → deliver, and the escrow is
released to the buyer on receipt. The full cycle passes **9/9 Playwright tests**,
the **Puppeteer audit (ALL CLEAR)**, and a **45-check live-API harness**.

---

## 2. What Was Built

### 2.1 Backend (FastAPI + SQLite)

| Component | Details |
|-----------|---------|
| **Escrow engine** | `_escrow_basis()` / `_escrow_out()` in `commerce_service.py` — abundant items require **30%** of accepted-bid basis, rare items **65%**; basis = accepted bids × price; deposits and releases recorded with timestamps |
| **Sourcing entity** | `bulking_registers.sourcing_entity_name` — the cooperative/company supplying through the register; drives the no-self-certify rule |
| **Pipeline roles** | Clerks (collate/receive), Verifiers, Packers, Certifiers, Couriers via `bulking_job_assignments` (role enum + status transitions) |
| **Same-company block** | Certifiers cannot come from the register's sourcing entity → 400 on assign |
| **Packing records** | `packed` → `certified` transition, links the issued certificate |
| **Courier delivery** | `courier_jobs.deliver_to_buyer` flag + status flow (`posted → assigned → in_transit → delivered`) |
| **Pipeline trace** | `GET /commerce/registers/{id}/pipeline` — 8 stages (register, collate, escrow, jobs, pack, certify, deliver, receive) + per-role status, `jobs` shows `completed/total` |
| **API surface** | Register create (auto-generate), escrow get/deposit, job assign/status, packing record create/status, courier post/status, certificate issue, pipeline trace |
| **Supply band** | `taxonomy_items.supply_band` (ABUNDANT/RARE) plumbed through item create + detail |

### 2.2 Frontend (static JS/CSS)

- Register detail page: **Investor Escrow card** (percentage, basis, amount due,
  deposited/released, deposit action), Sourcing Mode/Entity, Supply Band badge.
- **7-step pipeline view** with live **8-cell trace grid** (per-stage done/status).
- **Assign Jobs** modal (5 roles, self-certify warning), **Deposit** modal,
  **Courier** modal with "Deliver to investor buyer", **Create Register** modal
  with sourcing entity field.
- Landing page updated: hero CTA **"Bulk & Invest"**, feature cards
  **"Investor Bulking & Escrow"** and **"Member Job Pipeline"**.

---

## 3. Verification Results

| Gate | Result |
|------|--------|
| `npx playwright test --workers=2` | ✅ **9/9 passed** (bulking ×2, audit ×5, smoke ×2) |
| `node puppeteer-audit.js` | ✅ **ALL CLEAR** (16 auth-guard + 16 authenticated renders; zero console/page/failed/missing/api errors) |
| Live-API 45-check harness | ✅ **45/45 checks passed** (full cycle incl. same-company block, transition guards, escrow release, trace) |
| Server health | ✅ `GET /api/v1/health` → `database: connected` |
| Syntax | ✅ `node --check` on pages.js; backend app compiles (261 routes) |

**E2E coverage added** (`e2e/tests/bulking.spec.js`):
1. Full pipeline: registers investor + 5 member users (different company for
   certifier), rare item → 65% escrow → blocked self-certification → assign all
   roles → complete → certificate → pack certified → courier delivered → escrow
   released → trace reflects every stage → UI asserts 8 trace cells + escrow card.
2. UI register modal: sourcing entity input → creates register → navigates to
   `/#bulking/{id}` → sourcing entity + escrow visible.

---

## 4. Bugs Found & Fixed During QA

| # | Bug | Fix | Verified |
|---|-----|-----|----------|
| 1 | Duplicate phone registration returned **500** | `auth_service.register_user()`: pre-check + `IntegrityError` catch → 400 "Phone number already registered" | ✅ 400 confirmed |
| 2 | Trace `jobs` stage hardcoded `"N assigned"` | `get_pipeline_trace()` now reports `completed/total` | ✅ `5/5 completed` |
| 3 | Trace grid rendered before DOM append → stuck "Loading trace…" | `bulkRenderTrace()` retry loop (25×120 ms) | ✅ renders in UI test |
| 4 | **Enum drift 500** — `taxonomy_items.supply_band` stored lowercase `'abundant'/'rare'` (463+13 rows) while SQLAlchemy enum persists names → `LookupError` on load, breaking register creation for those items | Normalized rows to `ABUNDANT`/`RARE`; migration `a5b6c7d8e9f0` now declares uppercase values + uppercase backfill with explanatory comment | ✅ smoke test (product-linked item 15) now passes |
| 5 | Puppeteer audit tripped 429 rate limit when run right after Playwright suite (public register capped 30/min/IP) | `registerUser()` retries with 60 s backoff on 429 | ✅ audit ALL CLEAR |

*(Earlier verified fixes preserved: favicon PNGs, race-condition `innerHTML` guards,
500 fixes in warehouse/shipping/collection/dashboard services, rate-limiter static-asset
skip.)*

---

## 5. Known Remaining Gaps (Not Blocking)

- **Tenant isolation sweep** — commerce is tenant-scoped; other services (warehouse,
  shipping, batch, insurance, etc.) still need `.where(Model.tenant_id == ...)`
  (see `plans/go-live-readiness.md`, B4).
- **Legacy data drift** is repaired in the live DB, but a durable Alembic migration
  for `users.role/user_type` drift from old data is still a manual UPDATE only.
- **favicon.ico** 404s (icons served as `icon-192/512.png`; add an `ico` if the client
  requires one).
- Deploy path is bare-metal (no Docker); fine for Phase 1 commercial focus.

---

## 6. How to Re-Verify

```powershell
# Backend (from backend/): python -m uvicorn app.main:app --port 8000
# Full e2e + audit (from e2e/):
npx playwright test --workers=2
node puppeteer-audit.js
```
