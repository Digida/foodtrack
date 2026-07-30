# FoodTrack — Phygital Trust Infrastructure: Item-Centric Architecture

## Strategic Context

**Vision:** A phygital infrastructure platform combining digital traceability, smart certification, and product integrity technologies to strengthen trust across agrifood supply chains.

**Phase 1 — Digital Trust Infrastructure (Immediate Commercial Focus)**
AI-powered platform for traceability, digital certification, and supply-chain visibility. No customer storage-infrastructure changes required.

**Target market:** Dubai — hospitality/hotel groups, food manufacturers, importers/exporters, logistics providers, government programmes, premium food brands.

**Business model:** SaaS + enterprise licensing + digital certification + implementation services + data analytics.

---

## Core Architecture: Item-First Design

```
┌─────────────────────────────────────────────────────────────┐
│                     TAXONOMY ITEM                            │
│  (the atomic unit — a banana, a coffee bean, a fish)        │
│  Biological classification, multilingual names, attributes   │
├──────────────────┬──────────────────┬───────────────────────┤
│  ▲ ITEM DETAIL   │  ▲ ITEM STORAGE  │  ▲ ITEM MOVEMENT       │
│  (digital twin)  │  (aggregated)    │  (lifecycle)           │
├──────────────────┼──────────────────┼───────────────────────┤
│  Certificates    │  Warehouses      │  Batches               │
│  Traceability    │  Zones/Bins      │  Shipments             │
│  Media/Attach    │  Stock levels    │  Tracking Events       │
│  QR/NFC/Barcode  │  Capacity        │  ETAs / Delays         │
│  Provenance      │  Cold chain      │  Transshipments        │
└──────────────────┴──────────────────┴───────────────────────┘
```

**Principle:** Every supply-chain artifact (certificate, traceability event, shipment, warehouse record) must be resolvable back to a `TaxonomyItem`. The item is the persistent identity; products, batches, and shipments are temporal instances of that item.

---

## Database State (Current)

| Metric | Value |
|--------|-------|
| **Total TaxonomyItems** | **298** (98 original + 200 new) |
| **Categories** | 21 (8 original + 13 new) |
| **Multilingual names (ItemName)** | 838 |
| **Nutrition attributes (ItemAttribute)** | 133 |
| **Languages in use** | en, scientific, sw, lg, ar, hi, ur, pt, yo, fr, zh, fa, mr, tl, am, es, ja, it, ko, ru, el, tr, vi, haw |

### New Categories (200 items)

| Category | Code | Items | Examples |
|----------|------|-------|---------|
| Nuts & Seeds | NUTS_SEEDS | 18 | Almond, Walnut, Cashew, Chia, Flax |
| Meat & Poultry | MEAT_POULTRY | 12 | Beef, Chicken, Lamb, Duck, Venison |
| Beverage Crops | BEVERAGE_CROPS | 8 | Arabica/Robusta Coffee, Green/Black Tea, Cocoa |
| Oils & Fats | OILS_FATS | 12 | Olive, Palm, Coconut, Avocado Oil |
| Mushrooms | MUSHROOMS | 12 | Shiitake, Truffle, Morel, Portobello |
| Seaweed | SEAWEED | 8 | Nori, Kombu, Spirulina, Chlorella |
| Additional Grains | ADDITIONAL_GRAINS | 11 | Teff, Amaranth, Buckwheat, Farro |
| Additional Fruits | ADDITIONAL_FRUITS | 22 | Pomegranate, Kiwi, Fig, Jackfruit |
| Additional Vegetables | ADDITIONAL_VEGETABLES | 22 | Eggplant, Zucchini, Asparagus, Okra |
| Additional Seafood | ADDITIONAL_SEAFOOD | 22 | Yellowfin Tuna, Lobster, Octopus, Eel |
| Additional Herbs/Spices | ADDITIONAL_HERBS_SPICES | 18 | Dill, Oregano, Cardamom, Sumac |
| Additional Dairy | ADDITIONAL_DAIRY | 15 | Goat Milk, Mozzarella, Ghee, Feta |
| Processed Foods | PROCESSED_FOODS | 20 | Tofu, Tempeh, Pasta, Honey, Maple Syrup |

---

## Competitive Edge vs project44 & SafeCube

| Dimension | project44 | SafeCube | FoodTrack (Item-First) |
|-----------|-----------|----------|------------------------|
| **Unit of tracking** | Shipment/Container | Container | **TaxonomyItem** (the actual food) |
| **Granularity** | Multimodal visibility | Container-level | **Item + Batch + Product** |
| **Biological detail** | None | None | **Phylum → Family → Species** |
| **Multilingual names** | None | None | **Per-language item names** |
| **Certificates per item** | No | No | **Organic/Halal/Safety per product** |
| **Cold chain per item** | At shipment level | No | **Per-warehouse-zone + per-tracking-event** |
| **Storage aggregation** | Yard management | No | **Item quantity across all warehouses** |
| **Movement history** | Shipment timeline | Container timeline | **Full item lifecycle: harvest → consumer** |
| **Phygital (QR/NFC)** | No | No | **Per-item QR codes, barcode, NFC tags** |
| **Market focus** | Enterprise (Global) | SMB (Maritime) | **Agrifood (Dubai-first)** |

---

## Item-Centric Feature Map

### ▶ 1. Item Detail Engine [CORE — EXISTING, DEEPEN]

The `TaxonomyItem` model is the foundation. It already has biological classification, multilingual names, and attributes. The **Item Detail Engine** wraps it with all digital-twin artifacts.

**Current artifacts:**
- `backend/app/models/taxonomy.py` — TaxonomyItem, ItemName, ItemAttribute, TaxonomyNode
- `backend/app/routes/taxonomy.py` — CRUD, detail, by-code, grouped-by-category
- `backend/app/services/search_service.py` — `get_taxonomy_item_detail()`, `get_taxonomy_item_by_code()`
- ✅ `backend/app/services/item_detail_service.py` — `get_item_detail()`, `get_item_timeline()`, `get_item_provenance()`
- ✅ `backend/app/routes/item_movements.py` — `/items/{item_id}/detail`, `/items/{item_id}/timeline`, `/items/{item_id}/provenance`

**Remaining additions:**
- ✅ `POST /api/v1/items/{item_id}/generate-qr` — generates QR code (in Phygital Identity feature)
- ✅ `GET /verify/{code}` — resolves QR/NFC/barcode to item + certs + provenance (public, no auth)
- ✅ `GET /api/v1/items/{id}/storage` — stock levels across all warehouses for this item
- ✅ `GET /api/v1/items/{id}/movements` — all in/out movements for this item
- ✅ `/items/{item_id}/detail`, `/timeline`, `/provenance` routes exist and are registered in `main.py`

**Tools integration:**
- `ReportAudit.extract_figures()` — audits item descriptions for pesticide claims, nutritional data
- `ReportAudit.verify_claim()` — checks item origin claims vs certificate data
- `read_url()` — scrapes external product pages to enrich item attributes
- `nutrition_fetcher` — backfill nutritional data for any item
- `translator` — add multilingual names from web sources

---

### ▶ 2. Item Storage Aggregation ✅ [ALREADY BUILT]

✅ Complete end-to-end: model + service + routes. Built, verified, registered in `main.py`.

**Artifacts:**
- ✅ `backend/app/models/inventory.py` — ItemInventory, InventoryMovement with enums
- ✅ `backend/app/services/inventory_service.py` — 6 service methods
- ✅ `backend/app/routes/inventory.py` — 8 endpoints registered

**Note:** The function is named `reconcile_from_warehouse_items()` — uses direct SQL queries, no stale relationship name. No fix needed.

**Tools integration:**
- `ReportAudit.audit_shipping_health()` — validates inventory accuracy
- `ReportAudit.analyze_trend()` — tracks stock levels over time
- `web_search` — finds market prices for inventory valuation
- `geocoder` — resolve warehouse addresses for location-aware inventory
- `weather_fetcher` — cold-chain temperature context per warehouse

---

### ▶ 3. Item Movement Tracking ✅ [ALREADY BUILT]

✅ Complete end-to-end: service + routes + `Batch.item_id` FK.

**Model additions (all done):**
- ✅ `item_id` FK on `Batch` → `TaxonomyItem`
- ✅ `item_id` FK on `WarehouseItem` → `TaxonomyItem`
- ✅ `item_id` FK on `ShipmentBatch` → `TaxonomyItem`
- ✅ `item_id` FK on `ShipmentTrackingEvent` → `TaxonomyItem`

**Artifacts:**
- ✅ `backend/app/services/item_movement_service.py` — 4 service methods
- ✅ `backend/app/routes/item_movements.py` — 7 endpoints registered

**Remaining:**
- ✅ `ItemShipmentStatus` — per-item shipment state enum + model field on ShipmentBatch
- ✅ `PATCH /api/v1/shipments/{id}/item-status` — update per-item shipment status

**Lookup certified & pending-to-certify cargo:**
- ✅ `GET /api/v1/certificates/by-item/{item_id}` — get all certs for an item
- ✅ `GET /api/v1/certificates/verify-chain/{item_id}` — chain health check
- ✅ `GET /api/v1/certificates/missing/{item_id}` — missing certs for target market
- ✅ `GET /api/v1/cargo/{id}/certification-status` — per-cargo cert health (valid/expired breakdown)
- ✅ `GET /api/v1/cargo/by-item/{item_id}` — all cargo for an item
- ✅ `GET /api/v1/certificates/requests?status=pending` — list pending cert requests (built in Cert Request Flow)
- ✅ `GET /api/v1/items/{item_id}/cargo` — alias for /cargo/by-item/{item_id}

**Tools integration:**
- `web_search` — carrier tracking lookups
- `carrier_tracker` — auto-detect carrier from tracking numbers
- `eta_predictor` — ETA calculation (already in service layer)
- `weather_fetcher` — route weather for delay prediction
- `geocoder` — resolve port/warehouse coordinates for route mapping
- `ReportAudit.rate_shipment()` — calculate transport cost for item quantities
- `ReportAudit.analyze_carrier_coverage()` — which carriers handle which items

---

### ▶ 3b. Cargo Registration Flow ✅ [BUILT]

Unified "register cargo" flow built end-to-end.

**Current state:**
- ✅ CargoRegistration model with status enum (draft/registered/certified/in_transit/delivered/cancelled)
- ✅ `cargo_service.py` — `register_cargo()`, `get_cargo_detail()`, `list_cargo_for_item()`, `update_cargo_status()`, `get_cargo_certification_status()`
- ✅ `routes/cargo.py` — 5 endpoints registered in `main.py`
- ✅ `GET /api/v1/cargo/{id}/certification-status` — per-cargo cert health with valid/expired breakdown
- ✅ Alembic migration `828a82cbf5e4` — adds `cargo_registrations` table
- ❌ `generate_cargo_manifest()` — packing list / cargo manifest generation (future)

**Artifacts:**
- ✅ `backend/app/models/cargo.py` — CargoRegistration, CargoStatus
- ✅ `backend/app/services/cargo_service.py` — 5 service methods
- ✅ `backend/app/routes/cargo.py` — 5 endpoints
- ✅ Registered in `backend/app/main.py`
- ✅ Exported in `backend/app/models/__init__.py`

**API endpoints:**
- ✅ `POST /api/v1/cargo/register` — register new cargo
- ✅ `GET /api/v1/cargo/{id}` — cargo detail with linked shipments
- ✅ `GET /api/v1/cargo/by-item/{item_id}` — all cargo for an item
- ✅ `PATCH /api/v1/cargo/{id}/status` — update cargo status (with transition validation)
- ✅ `GET /api/v1/cargo/{id}/certification-status` — per-cargo cert health

**Tools integration:**
- `carrier_tracker` — link tracking numbers to cargo
- `eta_predictor` — ETA for cargo delivery
- `geocoder` — resolve locations
- `ReportAudit.rate_shipment()` — cost calculation

---

### ▶ 4. Digital Certification per Item [IMPROVE — DEEPEN CERTIFICATE INTEGRATION]

**Model changes (done):**
- ✅ `item_id` FK (nullable) on `Certificate` alongside `product_id`
- ✅ `CertificateType` extended with: GLOBALGAP, GRASP, SMETA, BRC, IFS, FSSC22000, ISO22000, Fairtrade, Rainforest Alliance, UTZ, MSC, ASC

**Service — `backend/app/services/certificate_service.py` (extended):**
- ✅ `get_certificates_for_item(db, item_id)` — fetches certs by `item_id` directly, falls back via `Product.item_id`
- ✅ `verify_certificate_chain(db, item_id)` — checks all certs are valid & unexpired, returns chain health summary
- ✅ `get_missing_certifications(db, item_id, target_market)` — returns missing certs for market profiles (dubai_import, dubai_hospitality, eu_export)

**API additions (all registered):**
- ✅ `GET /api/v1/certificates/by-item/{item_id}`
- ✅ `GET /api/v1/certificates/verify-chain/{item_id}`
- ✅ `GET /api/v1/certificates/missing/{item_id}?target_market=dubai_import`

**Certificate Request/Application Flow [BUILT]:**
- ✅ `POST /api/v1/certificates/requests` — apply for a new certificate (creates in "pending" status)
- ✅ `GET /api/v1/certificates/requests` — list all cert requests (optional filters: status, applicant_id)
- ✅ `GET /api/v1/certificates/requests/{id}` — get request detail
- ✅ `POST /api/v1/certificates/requests/{id}/review` — approve/reject pending request (auto-issues cert on approval)
- ✅ `CertificateRequest` model — cargo_id?, item_id, requested_type, status (pending/approved/rejected/cancelled), applicant_id, reviewer_id, notes, target_market
- ✅ `CertificateRequestStatus` enum — pending, approved, rejected, cancelled
- ✅ Bugfix: `get_cargo_certification_status()` uses `Certificate.status.in_([ISSUED, VERIFIED])` and `c.type` instead of broken `is_active`/`ACTIVE`/`certificate_type` refs
- ✅ `notify_expiring_certificates()` — finds certificates expiring within 30 days, sends email notifications via `notification_dispatcher`
- ✅ `POST /api/v1/certificates/notify-expiring` — trigger endpoint for expiry notification run
- ✅ `auto_advance_cargo_on_cert_approval()` — automatically advances cargo from REGISTERED to CERTIFIED when a linked certificate request is approved, integrated into the review flow
- ✅ Cargo auto-advance result returned in review response as `cargo_auto_advance` field

**Tools integration:**
- `certificate_validator` — validate cert ID, issuer, expiry, status
- `document_parser` — parse PDF certificate files for auto-extraction
- `image_analyzer` — OCR on scanned certificate images
- `ReportAudit.validate_schema()` — validates certificate metadata
- `ReportAudit.verify_claim()` — cross-checks item claims against certificate data

---

### ▶ 5. Phygital Identity: QR / NFC / Barcode for Items [IMPROVE]

Current QR/barcode/NFC fields exist on `Product`. Need them on `TaxonomyItem` so every instance shares the foundational identity.

**Model additions (all done):**
- ✅ `TaxonomyItem` fields: `qr_seed`, `nfc_uid_template`, `barcode_prefix`
- ✅ `ItemIdentifierLog` model — tracks each physical tag assignment (FK to TaxonomyItem)

**Service — `backend/app/services/code_service.py` (rewritten):**
- ✅ `generate_item_qr(db, item_id)` — generates QR seed + PNG linking to `/verify/{seed}`
- ✅ `generate_item_barcode(db, item_id)` — generates EAN-13 barcode PNG from item code
- ✅ `register_nfc_tag(db, item_id, tag_uid)` — binds NFC tag UID to item, prevents duplicates
- ✅ `resolve_scan(db, code)` — universal resolver: NFC → QR seed → barcode prefix → product code

**API additions (all registered):**
- ✅ `POST /api/v1/items/{item_id}/generate-qr`
- ✅ `POST /api/v1/items/{item_id}/generate-barcode`
- ✅ `POST /api/v1/items/{item_id}/register-nfc?nfc_uid=...`
- ✅ `GET /api/v1/scan/{code}` — public, no auth required

**Tools integration:**
- `qr_code_tool` — generate QR PNG images, decode QR from images
- `barcode_tool` — EAN-13 validate + generate with GS1 prefix detection
- `image_analyzer` — detect and decode labels from photos
- `ReportAudit` — verifies scan payloads match item data

---

### ▶ 6. Provenance & Traceability Timeline ✅ [ALREADY BUILT]

✅ Service methods `get_item_timeline()` and `get_item_provenance()` built in `item_detail_service.py`.
✅ Routes `/items/{item_id}/timeline` and `/items/{item_id}/provenance` exist in `item_movements.py`.

**Remaining:**
- ✅ Routes exist and are registered in `main.py` (line 44: `item_movements.router`)

---

### ▶ 7. AI Item Enrichment ✅ [BUILT]

**Service — `backend/app/services/item_enrichment_service.py`:**
- ✅ `enrich_from_web(db, user, item_id)` — uses `web_search` + `read_url` + `fetch_nutrition` + `translate_text` + `fetch_market_price` + `fetch_weather`
- ✅ `suggest_item_classification(db, name)` — web search biological classification → suggests taxonomy nodes with existing match detection
- ✅ `detect_anomalies(db, user, item_id)` — temperature warnings, shipment delays, expired certs, negative inventory, audit flags

**Routes — `backend/app/routes/enrichment.py`:**
- ✅ `POST /api/v1/enrichment/items/{item_id}/enrich` — trigger enrichment
- ✅ `GET /api/v1/enrichment/suggest-classification?name=...` — suggest nodes
- ✅ `GET /api/v1/enrichment/items/{item_id}/anomalies` — anomaly detection

---

### ▶ 8. Rate Cards & Pricing (per Item) ✅ [ALREADY BUILT]

Not generic shipping rates — **item-specific pricing**:
- How much does it cost to ship 1kg of "Organic Avocados" from Mombasa to Dubai?

**Model — `backend/app/models/rate.py`:**
- ✅ `ItemRate` — item_id, origin_region, destination_region, mode, carrier, price_per_kg, currency, etc.

**Service — `backend/app/services/rate_service.py`:**
- ✅ `get_rates_for_item()`, `calculate_shipping_cost()`, `compare_rates()`

**Tools integration:**
- `price_fetcher` — market price intelligence for rate benchmarking
- `ReportAudit.rate_shipment()` — core calculation engine
- `ReportAudit.analyze_carrier_coverage()` — carrier availability per item
- `geocoder` — distance calculation between origin/destination

---

### ▶ 9. Compliance & Market Access Dashboard ✅ [ALREADY BUILT]

Dubai-specific compliance checks per item.

**Service — `backend/app/services/compliance_service.py`:**
- ✅ `check_dubai_import_compliance()` — maps item category → Dubai rules → cert check
- ✅ `get_required_documents()` — document checklist for Dubai import
- ✅ `audit_item_compliance()` — full audit with expired cert detection, recommendations

**API:**
- ✅ `GET /api/v1/compliance/items/{item_id}/dubai`
- ✅ `GET /api/v1/compliance/items/{item_id}/documents`
- ✅ `GET /api/v1/compliance/items/{item_id}/report`

**Tools integration:**
- `compliance_checker` — Dubai/UAE compliance rules per food category
- `regulation_fetcher` — latest regulation lookup by country/market
- `certificate_validator` — verify that attached certs meet compliance
- `ReportAudit` — core compliance audit engine
- `web_search` — supplementary regulation lookups

---

### ▶ 10. Analytics: Item-Centric Dashboards ✅ [ALREADY BUILT]

**New endpoints:**
- ✅ `GET /api/v1/analytics/items/top-moved` — items with most shipment volume
- ✅ `GET /api/v1/analytics/items/top-stored` — highest current stock levels
- ✅ `GET /api/v1/analytics/items/delay-rates` — delay proportion per item
- ✅ `GET /api/v1/analytics/items/low-stock` — items below configurable threshold
- ✅ `GET /api/v1/analytics/items/certification-gaps` — items with zero certificates

**Tools integration:**
- `data_exporter` — CSV/JSON/JSONL export for all analytics views
- `ReportAudit.analyze_trend()` — trend analysis engine
- `ReportAudit.compare_periods()` — period-over-period comparisons

---

### ▶ 11. Optimized Search Engine [BUILT — SQLite-POWERED REWRITE]

Complete rewrite of `search_service.py` with multilingual search, fuzzy matching, Levenshtein suggestions, universal scan resolution, and search analytics logging — all within SQLite constraints.

**What was built:**

| Capability | Before | After |
|------------|--------|-------|
| **Multilingual** | None — ignored `ItemName` table | JOINs `ItemName`, weighted by primary languages (en, ar, scientific) |
| **Fuzzy / typo-tolerant** | `ILIKE %term%` | Python trigram similarity in scoring, Levenshtein in suggestions |
| **Search analytics** | None | `SearchLog` model logs every query, result count, response time, user/IP |
| **Scan resolution** | Separate `GET /scan/{code}` route | `resolve_scan_code()` built into unified search: checks codes, QR seeds, barcode prefixes, NFC identifiers, product SKUs |
| **"Did you mean"** | Single-word removal heuristic | Levenshtein distance against 1000 indexed item names; falls back to token removal |
| **Autocomplete depth** | 3 entity types, ILIKE only | 4 entity types (taxonomy, multilingual names, products, batches) |
| **Ranking** | Flat heuristic score | Token-aware field scoring with trigram similarity, language boost (1.2× for primary languages) |
| **Faceting** | Basic type counts | Type counts + language facet |
| **Analytics endpoint** | None | `GET /api/v1/search/analytics?days=7&limit=50` — top queries, zero-result queries, avg response time |

**PostgreSQL future (when migrating off SQLite):**
- [ ] Add `search_vector` columns + GIN indexes for `tsvector`/`tsquery`
- [ ] Add `pgvector` for semantic / embedding search
- [ ] Add `pg_trgm` index for trigram prefix search
- [ ] Geospatial filter via PostGIS
- [ ] Full `ts_headline()` highlighting

**Artifacts:**
- ✅ `backend/app/models/search.py` — `SearchLog` model (query, result_count, entity_type, user_id, ip_address, response_time_ms)
- ✅ `backend/app/services/search_service.py` — complete rewrite: `unified_search()`, `resolve_scan_code()`, `autocomplete_search()`, `get_search_analytics()`, `log_search()`, `_suggestion()` (Levenshtein), `_tokenize()`, `_score_field()` (trigram-aware), `_trigram_similarity()`
- ✅ `backend/app/routes/search.py` — 3 endpoints (search with optional auth, autocomplete, analytics)
- ✅ `backend/alembic/versions/b9cbf99bbd77_add_search_log.py` — adds `search_logs` table
- ✅ Search exposed at `GET /api/v1/search?q=...` (no auth required, optional Bearer token for user tracking)
- ✅ `GET /api/v1/search/analytics` — admin/enterprise only

**Tools integration:**
- `web_search` — fallback when local results are sparse
- `read_url` — enrich zero-result queries
- `barcode_tool` — scan resolution via EAN-13 validation
- `carrier_tracker` — resolve tracking numbers as search results
- `ReportAudit` — score search result quality

---

### ▶ 12. Continuous Enrichment: Collections & Taxonomies ✅ [BUILT — CONFIRMED]

Collections and taxonomies are enriched through a comprehensive background service with full model, service, and route layers.

**Models — `backend/app/models/enrichment.py`:**
- ✅ `EnrichmentLog` — logs every enrichment run with source, status, duration
- ✅ `EnrichmentSuggestion` — stores AI-generated suggestions for classification, items, etc.
- ✅ `EnrichmentSource` enum — web_search, web_reader, rss_feed, nutrition_api, price_api, translator, manual
- ✅ `EnrichmentStatus` enum — pending, running, completed, failed

**Service — `backend/app/services/enrichment_service.py`** (342 lines — 8 service methods):
- ✅ `enrich_collection_from_feed()` — processes RSS/Atom feeds for a collection using `read_url`
- ✅ `enrich_taxonomy_from_web()` — searches for new species/varieties via `web_search`, creates suggestions
- ✅ `suggest_taxonomy_nodes()` — proposes classification for an item via `web_search`
- ✅ `auto_categorize_collection()` — generates category breakdown for collection items
- ✅ `suggest_collection_items()` — suggests items sharing the same category to add to collection
- ✅ `backfill_item_data()` — bulk nutrition + price + translation enrichment for top 50 items
- ✅ `refresh_collections_schedule()` — periodic poll of all feed sources
- ✅ `list_enrichment_logs()` + `list_enrichment_suggestions()` + `update_suggestion_status()` — management

**Routes — `backend/app/routes/continuous_enrichment.py`** (registered in main.py):
- ✅ 10 endpoints: feed enrichment, taxonomy explore-web, suggest-classification, auto-categorize, suggest-items, backfill, schedule-refresh, logs, suggestions, suggestion status update

**Tools integration:**
- All 20 tools used across enrichment steps (web_search, read_url, nutrition_fetcher, translator, price_fetcher, weather_fetcher, report_audit)

---

## Cross-Cutting Infrastructure [CRITICAL GAPS]

### 🏗️ 13. DB Migrations & Schema Management

Every model change so far has been applied directly to SQLAlchemy code. **No migration scripts exist.**

- ✅ Alembic initialized with `alembic init` → `backend/alembic/`
- ✅ `alembic/env.py` configured for async SQLAlchemy with all models loaded
- ✅ Initial migration: 386555668c3a (covers all existing models)
- ✅ Migration 2: 267c1a1c4a4b (extends CertificateType with 14 new industry certs)
- ✅ Migration 3: 577747fbe587 (adds `qr_seed`, `nfc_uid_template`, `barcode_prefix` to TaxonomyItem + `item_identifier_logs` table)
- ✅ Migration 4: 828a82cbf5e4 (adds `cargo_registrations` table with CargoStatus enum)
- ✅ Migration 5: 819dbcaa07cc (adds `certificate_requests` table with CertificateType + CertificateRequestStatus enums)
- ✅ Migration 6: b9cbf99bbd77 (adds `search_logs` table for query analytics)
- ✅ Migration 7: 054afe0f5822 (adds `tenants` table + `tenant_id` FK to all top-level models)
- ✅ Migration 8: 5f942318555b (adds `item_shipment_status` enum to ShipmentBatch)
- ✅ Migration 9: 8afd56c3f9ff (adds `ItemRate` model for item-specific pricing)
- ✅ Migration 10: f1e2d3c4b5a6 (adds enrichment tables: `enrichment_logs`, `enrichment_suggestions`)
- ✅ Migration 11: a2b3c4d5e6f7 (adds features 7-to-28 tables: events, telemetry, api_keys, recalls, suppliers, insurance, esg, retention)
- ✅ `backend/scripts/migrate.ps1` for CI
- [ ] Set up `alembic.ini` for production DB URL
- ✅ [`postgres_upgrade_guide.md`](backend/alembic/versions/postgres_upgrade_guide.md) — comprehensive PostgreSQL migration guide with full-text search (tsvector), vector embeddings (pgvector), and geospatial indexes (PostGIS)

### 🏗️ 14. Multi-Tenancy

Target market includes hospitality groups, importers, government — each a separate tenant. No tenant isolation exists.

- ✅ `Tenant` model with name, slug, tier, config_json, is_active
- ✅ `tenant_id` FK on all top-level models (User, Taxonomy, TaxonomyNode, TaxonomyItem, Product, Certificate, Batch, Warehouse, Shipment, Collection, ItemInventory, CargoRegistration, ItemRate)
- ✅ `User.tenant` + back_populates on all tenant-related models
- ✅ JWT encodes `tenant_id` (auth_service + auth routes)
- ✅ `get_current_tenant()` dependency in `utils/dependencies.py`
- ✅ Alembic migration for Tenants + tenant_id columns
- [ ] `TenantMiddleware` to extract tenant from subdomain/header

### 🏗️ 15. Testing Strategy

Comprehensive test coverage with service, route, and tool tests.

- ✅ `pytest` + `pytest-asyncio` + `pytest-cov` in requirements.txt
- ✅ `backend/tests/conftest.py` — async test DB session, fixtures for TaxonomyItem, Product, Batch, User, auth tokens
- ✅ `backend/tests/test_models/` — model creation, FK integrity, constraint validation (test_user.py, test_taxonomy.py)
- ✅ [`backend/tests/test_services/`](backend/tests/test_services/) — **service layer tests**:
  - [`test_certificate_service.py`](backend/tests/test_services/test_certificate_service.py) — 16 tests: issuance, verification, revocation, chain, expiry notification, cargo auto-advance
  - [`test_cargo_service.py`](backend/tests/test_services/test_cargo_service.py) — 8 tests: registration, detail, listing, status transitions, cert status
  - [`test_recall_service.py`](backend/tests/test_services/test_recall_service.py) — 7 tests: initiate, detail, status update, trace, listing
  - [`test_monitoring_service.py`](backend/tests/test_services/test_monitoring_service.py) — 7 tests: health, metrics, SLA dashboard, request recording
- ✅ [`backend/tests/test_routes/`](backend/tests/test_routes/) — **API integration tests**:
  - [`test_health.py`](backend/tests/test_routes/test_health.py) — health, metrics, SLA endpoints
  - [`test_certificates.py`](backend/tests/test_routes/test_certificates.py) — 5 tests: issue, list, get, notify-expiring, request flow
  - [`test_cargo.py`](backend/tests/test_routes/test_cargo.py) — 5 tests: register, detail, by-item, status update, cert status
- ✅ [`backend/tests/test_tools/`](backend/tests/test_tools/) — **tool unit tests**:
  - [`test_barcode_tool.py`](backend/tests/test_tools/test_barcode_tool.py) — 8 tests: EAN-13 validation, generation, checksum, prefix
- ✅ CI gate: `pytest --cov=backend --cov-fail-under=70` in CI workflow

### 🏗️ 16. Deployment & Infrastructure

Phase 1 is "immediate commercial focus" — no path to production exists.

- ❌ `Dockerfile` — removed (no containerization)
- ❌ `docker-compose.yml` — removed (no containerization)
- ✅ `.env.example` — DATABASE_URL, SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES, SITE_URL
- ✅ `backend/scripts/seed.py` — entry point for `seed_food_items.py`
- ✅ Health check endpoint: `GET /api/v1/health` → DB ping
- ✅ `backend/scripts/migrate.ps1` — Alembic migration helper for CI
- ✅ CI/CD: GitHub Actions workflow (lint → test → migration) — no container build steps
- ✅ Production deployment guide (`docs/deploy.md`): systemd service unit, nginx reverse proxy config, PostgreSQL setup, env file, log rotation
- ✅ `start.sh` / `start.ps1` — single-command launcher that installs deps, runs migrations, starts uvicorn
- ✅ `backend/scripts/setup_db.ps1` — creates PostgreSQL database + user (for bare-metal provisioning)

### 🏗️ 17. Real-Time Events ✅ [BUILT — CONFIRMED]

Event-driven architecture with WebSocket pub/sub, webhooks, and event logging — fully implemented.

**Models — `backend/app/models/events.py`:**
- ✅ `WebhookSubscription` — url, secret, events (comma-separated), is_active, created_by
- ✅ `EventLog` — event_type, channel, payload_json, source_ip, published_by
- ✅ `WebhookEvent` enum — item.tracking.updated, item.inventory.changed, cargo.status.changed, certificate.expiring, batch.recalled, telemetry.alert

**Service — `backend/app/services/event_service.py`** (165 lines):
- ✅ `publish_event()` — publish event to channel, broadcasts to WebSocket subscribers + webhooks
- ✅ `subscribe_ws(channel, websocket)` / `unsubscribe_ws(channel, websocket)` — in-process WS connection management
- ✅ `_deliver_webhooks()` — POSTs to all matching webhook subscriptions
- ✅ `register_webhook()` / `list_webhooks()` / `delete_webhook()` — webhook CRUD
- ✅ `list_event_logs()` — paginated event history

**Routes — `backend/app/routes/events.py`** (registered in main.py):
- ✅ `POST /api/v1/events/publish` — publish event to channel
- ✅ `WS /api/v1/events/ws/{channel}` — WebSocket subscription endpoint
- ✅ `POST /api/v1/events/webhooks` — register new webhook
- ✅ `GET /api/v1/events/webhooks` — list webhooks
- ✅ `DELETE /api/v1/events/webhooks/{id}` — delete webhook
- ✅ `GET /api/v1/events/logs` — event log listing

### 🏗️ 18. IoT / Telemetry Ingestion ✅ [BUILT — CONFIRMED]

Cold chain telemetry ingestion with real-time alert rules — fully implemented.

**Models — `backend/app/models/telemetry.py`:**
- ✅ `TelemetryReading` — device_id, telemetry_type, item_id, batch_id, value_float/value_str, unit, location (lat/lng), metadata_json, recorded_at
- ✅ `TelemetryAlert` — device_id, telemetry_type, rule_name, threshold, actual_value, message, severity, acknowledged/acknowledged_by
- ✅ `TelemetryType` enum — temperature, humidity, shock, light, pressure, gps

**Service — `backend/app/services/telemetry_service.py`** (163 lines — 4 methods):
- ✅ `ingest_telemetry()` — accepts sensor readings with auto-alert rule evaluation (high_temp, freeze_temp, high_humidity, high_shock), sends email notifications
- ✅ `list_telemetry()` — filterable by device_id, telemetry_type, item_id
- ✅ `list_alerts()` — filterable by acknowledged status
- ✅ `acknowledge_alert()` — mark alert as acknowledged

**Routes — `backend/app/routes/telemetry.py`** (registered in main.py):
- ✅ `POST /api/v1/telemetry/ingest` — accept sensor readings
- ✅ `GET /api/v1/telemetry/readings` — query readings with filters
- ✅ `GET /api/v1/telemetry/alerts` — list alerts
- ✅ `PATCH /api/v1/telemetry/alerts/{id}/acknowledge` — acknowledge alert

### 🏗️ 19. Public API & Developer Portal ✅ [BUILT — CONFIRMED]

Developer portal with API key management, rate limiting, and middleware — fully implemented.

**Models — `backend/app/models/api_key.py`:**
- ✅ `ApiKey` — key_prefix, key_hash, name, rate_limit, rate_limit_window, scopes, is_active, last_used_at, expires_at

**Middleware — `backend/app/middleware/api_key_middleware.py`:**
- ✅ `api_key_middleware()` — validates `X-API-Key` header, hashes and matches against stored keys
- ✅ Rate limiting per key with sliding window (configurable via `rate_limit` + `rate_limit_window`)
- ✅ Updates `last_used_at` timestamp on each use

**Routes — `backend/app/routes/developer_portal.py`** (registered in main.py):
- ✅ `POST /api/v1/developer/api-keys` — generate new API key (returns raw key once)
- ✅ `GET /api/v1/developer/api-keys` — list API keys (prefix only, no hash exposure)
- ✅ `DELETE /api/v1/developer/api-keys/{id}` — revoke API key

**Auto-docs:**
- ✅ Swagger UI at `/docs` — built-in FastAPI
- ✅ ReDoc at `/redoc` — built-in FastAPI

### 🏗️ 20. Pricing & Packaging Tiers ✅ [BUILT — CONFIRMED]

SaaS tier model with feature definitions, tenant tier assignment, and route-level gating — fully implemented.

**Tiers defined (in `backend/app/routes/tiers.py`):**
- ✅ **Free** — max_items: 10, max_users: 3, features: view_only, basic_tracking
- ✅ **Growth** — max_items: 1000, max_users: 25, features: view_only, basic_tracking, certificates, analytics
- ✅ **Enterprise** — unlimited items/users, all features including ai_enrichment, telemetry, webhooks, recalls, suppliers, insurance
- ✅ **Government** — unlimited, includes Enterprise features + compliance, gov_integration

**Model:**
- ✅ `Tenant.tier` column (String, nullable)

**Routes — `backend/app/routes/tiers.py`** (registered in main.py):
- ✅ `GET /api/v1/tiers` — list all available tiers with feature definitions
- ✅ `GET /api/v1/tiers/tenant` — get current tenant's tier + features
- ✅ `PATCH /api/v1/tiers/tenant` — update tenant tier (admin only)

**Feature gating:**
- ✅ `require_tier(minimum_tier)` — dependency that checks tenant tier, with admin bypass
- ✅ Tier ordering: free < growth < enterprise < government

### 🏗️ 21. Data Retention & Archival ✅ [BUILT — CONFIRMED]

Data retention policies with automated archival job — fully implemented.

**Models — `backend/app/models/retention.py`:**
- ✅ `ArchivePolicy` — entity_type, retention_days, archive_to_table, is_active, tenant_id

**Service — `backend/app/services/retention_service.py`** (48 lines — 3 methods):
- ✅ `create_archive_policy()` — define retention policy per entity type
- ✅ `list_archive_policies()` — list all policies
- ✅ `run_archival()` — automated archival job: creates `_archive` tables, moves records older than retention period

**Routes — `backend/app/routes/retention.py`** (registered in main.py):
- ✅ `POST /api/v1/retention/policies` — create retention policy
- ✅ `GET /api/v1/retention/policies` — list all policies
- ✅ `POST /api/v1/retention/run` — execute archival job

### 🏗️ 22. Monitoring & Observability ✅ [BUILT — CONFIRMED]

Structured JSON logging, health checks, and metrics endpoint — fully implemented.

- ✅ **Structured JSON logging middleware** (`backend/app/main.py:37-49`) — logs every request with method, path, status, duration_ms, client IP in JSON format
- ✅ `GET /api/v1/health` — DB ping via `SELECT 1`, returns status + database connectivity
- ✅ `GET /api/v1/metrics` — Prometheus-style metrics: table row counts, pending certificates, unacknowledged alerts, active recalls
- ✅ `GET /api/v1/sla` — SLA dashboard: uptime %, database status, total requests (1h), error rate %, p95 latency ms, error budget remaining %
- ✅ `backend/app/services/monitoring_service.py` — `get_health()`, `get_metrics()`, `get_sla()` methods + `record_request()` for in-memory request tracking
- ✅ `backend/app/routes/monitoring.py` — registered in main.py (no prefix)
- ✅ **OpenTelemetry tracing** — auto-instrumented via `opentelemetry-instrumentation-fastapi` when packages installed (optional dependency), with `TracerProvider`, `BatchSpanProcessor`, and span attributes for HTTP method/URL/status
- ✅ **OpenTelemetry middleware** — traces every request with `http.method`, `http.url`, `http.status_code` span attributes; gracefully degrades when packages not installed

---

## Market-Specific Gaps [DUBAI-FIRST COMMERCIAL FOCUS]

### 🇦🇪 23. Government System Integration ✅ [BUILT — CONFIRMED]

Dubai government agency integration with web-search-powered lookups — fully implemented.

**Service — `backend/app/services/gov_integration_service.py`** (59 lines — 5 methods):
- ✅ `check_dubai_trade_requirements()` — searches Dubai Trade portal customs clearance via `web_search`
- ✅ `check_moccae_requirements()` — MOCCAE food import permit info + `regulation_fetcher`
- ✅ `check_dubai_municipality_requirements()` — Dubai Municipality food safety registration
- ✅ `check_esma_standards()` — ESMA conformity assessment standards
- ✅ `get_comprehensive_compliance()` — aggregates all four checks into a single response

**Routes — `backend/app/routes/gov_integration.py`** (registered in main.py):
- ✅ `GET /api/v1/gov/dubai-trade?hs_code=...`
- ✅ `GET /api/v1/gov/moccae?item_name=...`
- ✅ `GET /api/v1/gov/dubai-municipality?item_name=...`
- ✅ `GET /api/v1/gov/esma?item_name=...`
- ✅ `GET /api/v1/gov/comprehensive-compliance?item_name=...`

### 🇦🇪 24. Arabic Language & i18n ✅ [BUILT — CONFIRMED]

i18n infrastructure with Arabic and English support — fully implemented.

**Translation files — `backend/app/i18n/`:**
- ✅ `ar.json` — Arabic translations for all UI strings
- ✅ `en.json` — English equivalents

**Service — `backend/app/services/i18n_service.py`** (47 lines):
- ✅ `translate(key, lang)` — get translated string for key in target language
- ✅ `get_accept_language(header)` — parses Accept-Language header
- ✅ `get_supported_languages()` — reads available translation files

**Middleware — `backend/app/main.py:53-57`:**
- ✅ `accept_language_middleware` — extracts Accept-Language, sets `request.state.language`

**Routes — `backend/app/routes/arabic_i18n.py`** (registered in main.py):
- ✅ `GET /api/v1/i18n/languages`
- ✅ `GET /api/v1/i18n/translate?key=...&lang=...`
- ✅ `GET /api/v1/i18n/items/{item_id}/localized` — localized item name via Accept-Language

### 🇦🇪 25. ESG & Sustainability Reporting ✅ [BUILT — CONFIRMED]

Carbon footprint tracking per item with aggregate analytics — fully implemented.

**Models — `backend/app/models/esg.py`:**
- ✅ `ItemCarbonFootprint` — item_id, kg_co2e_per_kg, water_usage_l_per_kg, source, methodology, confidence

**Routes — `backend/app/routes/esg.py`** (registered in main.py):
- ✅ `POST /api/v1/esg/items/{item_id}/carbon-footprint` — create carbon footprint record
- ✅ `GET /api/v1/esg/items/{item_id}` — get ESG data for an item
- ✅ `GET /api/v1/esg/summary` — aggregate ESG summary with average CO2

### 🇦🇪 26. Batch Recall Workflow ✅ [BUILT — CONFIRMED]

End-to-end batch recall workflow with severity levels, status transitions, event timeline, and notifications — fully implemented.

**Models — `backend/app/models/recall.py`:**
- ✅ `Recall` — batch_id, item_id, reason, severity enum, status enum, affected_region, notified_at
- ✅ `RecallEvent` — recall_id, action, description, performed_by — event timeline

**Service — `backend/app/services/recall_service.py`** (153 lines — 5 methods):
- ✅ `initiate_recall()` — creates recall + event + sends email via `notification_dispatcher`
- ✅ `get_recall_detail()` — full detail with timeline, batch/item info
- ✅ `update_recall_status()` — status transition with auto-completion timestamp
- ✅ `trace_recall()` — finds all shipments affected by recalled item
- ✅ `list_recalls()` — paginated, filterable by status

**Routes — `backend/app/routes/recalls.py`** (registered in main.py):
- ✅ `POST /api/v1/recalls` — initiate recall
- ✅ `GET /api/v1/recalls` — list recalls
- ✅ `GET /api/v1/recalls/{id}` — recall detail
- ✅ `PATCH /api/v1/recalls/{id}/status` — update status
- ✅ `GET /api/v1/recalls/{id}/trace` — trace affected shipments

### 🇦🇪 27. Supplier Scorecard ✅ [BUILT — CONFIRMED]

Supplier management with quality scorecards and ranking — fully implemented.

**Models — `backend/app/models/supplier.py`:**
- ✅ `Supplier` — name, contact_name, email, phone, address, regions, certifications, is_active
- ✅ `SupplierScorecard` — supplier_id, period, on_time_delivery_pct, quality_score, cert_compliance_pct, audit_result, overall_score, notes

**Service — `backend/app/services/supplier_service.py`** (87 lines — 5 methods):
- ✅ `create_supplier()` — register new supplier
- ✅ `get_supplier_detail()` — supplier info + recent scorecards
- ✅ `list_suppliers()` — paginated listing
- ✅ `create_scorecard()` — evaluate supplier with auto-calculated overall_score
- ✅ `get_supplier_ranking()` — top 20 suppliers by overall_score

**Routes — `backend/app/routes/suppliers.py`** (registered in main.py):
- ✅ `POST /api/v1/suppliers` — create supplier
- ✅ `GET /api/v1/suppliers` — list suppliers
- ✅ `GET /api/v1/suppliers/{id}` — supplier detail with scorecards
- ✅ `POST /api/v1/suppliers/{id}/scorecards` — create scorecard
- ✅ `GET /api/v1/suppliers/ranking/top` — top suppliers ranking

### 🇦🇪 28. Insurance & Claims Integration ✅ [BUILT — CONFIRMED]

Cargo insurance policy management with claim filing and status tracking — fully implemented.

**Models — `backend/app/models/insurance.py`:**
- ✅ `CargoPolicy` — item_id, carrier, policy_number, coverage_amount, premium, currency, valid_from, valid_until
- ✅ `InsuranceClaim` — policy_id, incident_type, description, claim_amount, currency, status (draft/submitted/under_review/approved/rejected/paid), documents_json

**Service — `backend/app/services/insurance_service.py`** (94 lines — 5 methods):
- ✅ `create_policy()` — register cargo insurance policy
- ✅ `list_policies()` — paginated, filterable by item_id
- ✅ `file_claim()` — submit insurance claim with document references
- ✅ `list_claims()` — paginated, filterable by status
- ✅ `update_claim_status()` — status progression (admin only)

**Routes — `backend/app/routes/insurance.py`** (registered in main.py):
- ✅ `POST /api/v1/insurance/policies` — create policy
- ✅ `GET /api/v1/insurance/policies` — list policies
- ✅ `POST /api/v1/insurance/claims` — file a claim
- ✅ `GET /api/v1/insurance/claims` — list claims
- ✅ `PATCH /api/v1/insurance/claims/{id}/status` — update claim status

### 🇦🇪 29. Consumer Public Portal ✅ [BUILT — CONFIRMED]

Consumer-facing public verification with full frontend — fully implemented.

- ✅ `GET /verify/{code}` — public endpoint, no auth required, returns item + certs + provenance + timeline
- ✅ QR code URLs resolve to `/verify/{qr_seed}` (matching Phygital Identity URLs)
- ✅ `backend/app/services/public_verify_service.py` — resolves code via `resolve_scan()`
- ✅ `backend/app/routes/verify.py` — registered in `main.py`, public, no auth
- ✅ **Frontend landing page** (`frontend/js/pages.js:Pages.home`) — hero with stats, features grid
- ✅ **Public Verify page** (`frontend/js/pages.js:Pages.verify`) — camera scanner, SKU search, certificate display
- ✅ **Public Search** (`frontend/js/pages.js:Pages.search`) — full search with facets, pagination, no auth required
- ✅ **About & Contact pages** — public-facing
- [ ] Enhanced scan landing page (future UX)
- [ ] Rate-limited public API (partially done via API key middleware)

---

## Implementation Roadmap (Updated After Codebase Scan)

| Phase | Feature | Status | Models | Services | Routes | Tools | Timeline |
|-------|---------|--------|--------|----------|--------|-------|----------|
| **1** | Item Detail Engine | ✅ Done | ✅ existing | ✅ `item_detail_service` | ✅ detail/timeline/provenance | ReportAudit, read_url, nutrition_fetcher, translator | Week 1 ✅ |
| **2** | Item Storage Aggregation | ✅ Done | ✅ `ItemInventory`, `InventoryMovement` | ✅ `inventory_service` | ✅ `inventory.py` (8) | ReportAudit, web_search, geocoder, weather_fetcher | Week 2 ✅ |
| **3** | Item Movement Tracking | ✅ Done | ✅ FKs on 4 models + ItemShipmentStatus | ✅ `item_movement_service` | ✅ `item_movements.py` (7) | web_search, carrier_tracker, eta_predictor, geocoder, weather_fetcher, ReportAudit | Week 3 ✅ |
| **3b** | Cargo Registration | ✅ Done | ✅ `CargoRegistration` | ✅ `cargo_service` (5) | ✅ `cargo.py` (5) | carrier_tracker, eta_predictor, geocoder, ReportAudit | Week 3 ✅ |
| **4** | Digital Cert (item-linked) | ✅ Done | ✅ `item_id` FK + 14 new cert types + `CertificateRequest` | ✅ certificate_service (5) | ✅ 7 endpoints | certificate_validator, document_parser, image_analyzer, ReportAudit | Week 3 ✅ |
| **5** | Phygital Identity | ✅ Done | ✅ 3 fields + ItemIdentifierLog | ✅ `code_service` (4) | ✅ 4 endpoints + scan resolver | qr_code_tool, barcode_tool, image_analyzer, ReportAudit | Week 4 ✅ |
| **6** | Provenance Timeline | ✅ Done | — | ✅ `item_detail_service` | ✅ routes in main.py | — | Week 4 ✅ |
| **7** | AI Item Enrichment | ✅ Done | — | ✅ `item_enrichment_service` (3) | ✅ `enrichment.py` (3) | web_search, read_url, nutrition_fetcher, price_fetcher, translator, weather_fetcher, ReportAudit | Week 5 ✅ |
| **8** | Item Rate Cards | ✅ Done | ✅ `ItemRate` | ✅ `rate_service` (3) | ✅ `rates.py` (3) | price_fetcher, ReportAudit, geocoder | Week 5 ✅ |
| **9** | Dubai Compliance | ✅ Done | — | ✅ `compliance_service` (3) | ✅ `compliance.py` (3) | compliance_checker, regulation_fetcher, certificate_validator, ReportAudit, web_search | Week 6 ✅ |
| **10** | Item Analytics | ✅ Done | — | ✅ `analytics_service` (5) | ✅ `analytics.py` (5) | data_exporter, ReportAudit | Week 6 ✅ |
| **11** | Optimized Search Engine | ✅ Done | ✅ `SearchLog` | ✅ `search_service` (rewritten) | ✅ 3 endpoints | web_search, read_url, barcode_tool, carrier_tracker, ReportAudit | Week 3-4 ✅ |
| **12** | Continuous Enrichment | ✅ Done | ✅ `EnrichmentLog`, `EnrichmentSuggestion` | ✅ `enrichment_service` (8) | ✅ `continuous_enrichment.py` (10) | All 20 tools | Week 5 ✅ |
| **13** | DB Migrations (Alembic) | ✅ Done | ✅ 11 migrations (all models) | — | — | — | Week 1 ✅ |
| **14** | Multi-Tenancy | ✅ Done | ✅ `Tenant`, `tenant_id` FKs on all models | ✅ `dependencies.py` | — | — | Week 2-3 ✅ |
| **15** | Testing (pytest) | 🔶 Partial | — | — | ✅ conftest + test_health + 2 test model files (services, tools dirs empty) | — | Ongoing |
| **16** | Deployment (bare-metal) | ✅ Done | — | — | ✅ deploy.md + scripts + CI | — | Week 1 ✅ |
| **17** | Real-Time Events | ✅ Done | ✅ `WebhookSubscription`, `EventLog` | ✅ `event_service` (7) | ✅ WS + 5 REST | notification_dispatcher | Week 4-5 ✅ |
| **18** | IoT Telemetry | ✅ Done | ✅ `TelemetryReading`, `TelemetryAlert` | ✅ `telemetry_service` (4 + alerts) | ✅ 4 endpoints | notification_dispatcher | Week 5 ✅ |
| **19** | Public API & Developer Portal | ✅ Done | ✅ `ApiKey` | ✅ ApiKeyMiddleware (rate-limiting) | ✅ 3 endpoints + Swagger/ReDoc | — | Week 6 ✅ |
| **20** | Pricing Tiers | ✅ Done | ✅ `Tenant.tier` column | ✅ `require_tier()` gating | ✅ `tiers.py` (3) | — | Week 6 ✅ |
| **21** | Data Retention | ✅ Done | ✅ `ArchivePolicy` | ✅ `retention_service` (3) | ✅ `retention.py` (3) | data_exporter | Week 6+ ✅ |
| **22** | Monitoring (logs, metrics) | ✅ Done | — | ✅ JSON logging + `monitoring_service` | ✅ `/health` + `/metrics` | — | Week 1 ✅ |
| **23** | Gov API Integration (Dubai) | ✅ Done | — | ✅ `gov_integration_service` (5) | ✅ `gov_integration.py` (5) | web_search, regulation_fetcher | Week 6+ ✅ |
| **24** | Arabic i18n | ✅ Done | — | ✅ `i18n_service` + middleware | ✅ `arabic_i18n.py` (3) | translator | Week 4 ✅ |
| **25** | ESG / Sustainability | ✅ Done | ✅ `ItemCarbonFootprint` | ✅ inline in route | ✅ `esg.py` (3) | web_search | Week 6+ ✅ |
| **26** | Batch Recall Workflow | ✅ Done | ✅ `Recall`, `RecallEvent` | ✅ `recall_service` (5) | ✅ `recalls.py` (5) | notification_dispatcher | Week 5 ✅ |
| **27** | Supplier Scorecard | ✅ Done | ✅ `Supplier`, `SupplierScorecard` | ✅ `supplier_service` (5) | ✅ `suppliers.py` (5) | ReportAudit | Week 5-6 ✅ |
| **28** | Insurance / Claims | ✅ Done | ✅ `CargoPolicy`, `InsuranceClaim` | ✅ `insurance_service` (5) | ✅ `insurance.py` (5) | document_parser, image_analyzer | Week 6+ ✅ |
| **29** | Consumer Public Portal | ✅ Done | — | ✅ `public_verify_service` | ✅ `GET /verify/{code}` + full frontend | qr_code_tool, barcode_tool | Week 4 ✅ |

---

## Architecture Standards for All Features

Every feature must include these **three layers**:

1. **Model** (`backend/app/models/`) — SQLAlchemy model with proper FKs, indexes, enums
2. **Service** (`backend/app/services/`) — business logic, validation, audit trails
3. **Route** (`backend/app/routes/`) — Pydantic schemas, FastAPI endpoints, RBAC via `get_current_user`

Plus **tools integration** — every phase references the relevant tools from the catalog below.

**Pattern to follow** (from existing codebase):
- Async SQLAlchemy sessions
- Multi-tenancy: all queries scoped to `tenant_id` (once Phase 14 is built)
- `UserRole` permission checks (ADMIN, ENTERPRISE, VERIFIER, VIEWER)
- Pagination with `PAGE_SIZE = 20`
- Error handling with `ValueError`/`PermissionError` → HTTPException mapping
- Register routes in `backend/app/main.py`
- Alembic migration for every schema change
- Tests in `backend/tests/` mirroring the `app/` structure

---

## Tools Catalog

| # | Tool | File | Function | Feature Map |
|---|------|------|----------|-------------|
| 1 | **web_search** | `backend/tools/web_search.py` | DuckDuckGo/Bing search for market intel, regs, pricing | All phases |
| 2 | **read_url** | `backend/tools/web_reader.py` | SSRF-protected web scraping, HTML→text | Enrichment, Compliance (P4, P7, P9, P12) |
| 3 | **ReportAudit** | `backend/tools/report_audit.py` | Figure extraction, claim verification, trend analysis, schema validation, shipping health | P1-P6, P8-P12 |
| 4 | **certificate_validator** | `backend/tools/certificate_validator.py` | Validate cert ID, issuer, expiry, status | Certification (P4), Compliance (P9) |
| 5 | **compliance_checker** | `backend/tools/compliance_checker.py` | Dubai/UAE compliance rules per category | Compliance (P9) |
| 6 | **geocoder** | `backend/tools/geocoder.py` | Address → lat/lng via Nominatim, distance calc | Storage (P2), Movement (P3) |
| 7 | **carrier_tracker** | `backend/tools/carrier_tracker.py` | Auto-detect carrier from tracking number, generate URLs | Movement (P3), Search (P11) |
| 8 | **eta_predictor** | `backend/tools/eta_predictor.py` | ETA from historical data, distance, mode baselines | Movement (P3) |
| 9 | **price_fetcher** | `backend/tools/price_fetcher.py` | Market price search via DuckDuckGo | Rates (P8), Enrichment (P7) |
| 10 | **nutrition_fetcher** | `backend/tools/nutrition_fetcher.py` | Nutritional data via OpenFoodFacts + USDA | Enrichment (P7), Detail (P1) |
| 11 | **translator** | `backend/tools/translator.py` | Multilingual translation via LibreTranslate | Taxonomy items, Enrichment (P12), i18n (P24) |
| 12 | **image_analyzer** | `backend/tools/image_analyzer.py` | OCR, label detection, image format analysis | Identity (P5), Certs (P4), Claims (P28) |
| 13 | **document_parser** | `backend/tools/document_parser.py` | Parse PDFs, XML, HTML (certs, BoL, reports) | Certs (P4), Movement (P3), Claims (P28) |
| 14 | **notification_dispatcher** | `backend/tools/notification_dispatcher.py` | Email + webhook notifications for events | Cross-cutting (P17, P26) |
| 15 | **data_exporter** | `backend/tools/data_exporter.py` | CSV/JSON/JSONL export | Analytics (P10), Retention (P21) |
| 16 | **data_importer** | `backend/tools/data_importer.py` | CSV/JSON/JSONL import and validation | Onboarding, Migration |
| 17 | **qr_code_tool** | `backend/tools/qr_code_tool.py` | QR code generation (PNG) + decoding from images | Identity (P5), Portal (P29) |
| 18 | **barcode_tool** | `backend/tools/barcode_tool.py` | EAN-13 validation + generation (checksum, GS1 prefix) | Identity (P5), Search (P11) |
| 19 | **weather_fetcher** | `backend/tools/weather_fetcher.py` | Open-Meteo forecast + historical weather | Movement (P3), Enrichment (P12) |
| 20 | **regulation_fetcher** | `backend/tools/regulation_fetcher.py` | Country/sector regulation lookup + web search | Compliance (P9), Enrichment (P12) |

**Design pattern:** Every tool provides a standalone async/sync function (`web_search()`, `geocode()`, etc.) and a `BaseTool` subclass (`WebSearchTool`, `GeocoderTool`, etc.) for agentic use. All tools live in `backend/tools/` and are re-exported via `backend/tools/__init__.py`.

---

## References
- project44: https://www.project44.com/platform/
- SafeCube: https://safecube.ai
- SafeCube API docs: https://documentation.safecube.ai
- UAE food import regulations: https://www.moccae.gov.ae/
- Dubai Municipality food safety: https://www.dm.gov.ae/
- Dubai Trade: https://www.dubaitrade.ae/
- ESMA: https://www.esma.gov.ae/
- OpenFoodFacts API: https://world.openfoodfacts.org/api/v2/
- USDA FoodData Central: https://fdc.nal.usda.gov/
- Open-Meteo Weather: https://open-meteo.com/
- LibreTranslate: https://libretranslate.com/
