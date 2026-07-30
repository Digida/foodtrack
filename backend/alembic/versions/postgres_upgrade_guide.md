# PostgreSQL Migration Guide

This document describes the steps and SQL migration to enable PostgreSQL-specific features (full-text search, vector embeddings, geospatial queries) when migrating from SQLite.

## Prerequisites

- PostgreSQL 15+ with `pgvector` and `PostGIS` extensions installed
- Updated `DATABASE_URL` in `.env`: `postgresql+asyncpg://user:pass@host:5432/foodtrack`

## Required Extensions

```sql
CREATE EXTENSION IF NOT EXISTS pg_trgm;   -- Trigram indexing for fuzzy search
CREATE EXTENSION IF NOT EXISTS pgvector;   -- Vector similarity search
CREATE EXTENSION IF NOT EXISTS postgis;    -- Geospatial queries
```

## Migration SQL

Run the following migration after the Alembic schema migrations have been applied:

### 1. Full-Text Search Columns & Indexes

```sql
-- Add tsvector columns for full-text search
ALTER TABLE taxonomy_items ADD COLUMN search_vector tsvector
  GENERATED ALWAYS AS (
    setweight(to_tsvector('english', coalesce(common_name, '')), 'A') ||
    setweight(to_tsvector('simple', coalesce(scientific_name, '')), 'B') ||
    setweight(to_tsvector('english', coalesce(description, '')), 'C')
  ) STORED;

ALTER TABLE products ADD COLUMN search_vector tsvector
  GENERATED ALWAYS AS (
    setweight(to_tsvector('english', coalesce(name, '')), 'A') ||
    setweight(to_tsvector('simple', coalesce(sku, '')), 'B')
  ) STORED;

-- GIN indexes for fast tsquery
CREATE INDEX idx_taxonomy_items_search ON taxonomy_items USING GIN(search_vector);
CREATE INDEX idx_products_search ON products USING GIN(search_vector);

-- Trigram indexes for fuzzy prefix matching
CREATE INDEX idx_taxonomy_items_trgm ON taxonomy_items USING GIN(common_name gin_trgm_ops);
CREATE INDEX idx_item_names_trgm ON item_names USING GIN(name gin_trgm_ops);
CREATE INDEX idx_products_name_trgm ON products USING GIN(name gin_trgm_ops);
```

### 2. Vector Embeddings for Semantic Search

```sql
-- Add embedding column to taxonomy_items
ALTER TABLE taxonomy_items ADD COLUMN embedding vector(384);

-- Create IVF index for approximate nearest neighbor search
CREATE INDEX idx_taxonomy_items_embedding ON taxonomy_items
  USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Add embedding column to item_names for multilingual semantic search
ALTER TABLE item_names ADD COLUMN embedding vector(384);
CREATE INDEX idx_item_names_embedding ON item_names
  USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
```

### 3. Geospatial Indexes for Location-Aware Queries

```sql
-- Add geography columns to warehouses
ALTER TABLE warehouses ADD COLUMN location geography(Point, 4326);
UPDATE warehouses SET location = ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)
  WHERE longitude IS NOT NULL AND latitude IS NOT NULL;
CREATE INDEX idx_warehouses_location ON warehouses USING GIST(location);

-- Add geography columns to shipments (origin/destination)
ALTER TABLE shipments ADD COLUMN origin_location geography(Point, 4326);
ALTER TABLE shipments ADD COLUMN destination_location geography(Point, 4326);

-- Add geography to telemetry readings
ALTER TABLE telemetry_readings ADD COLUMN location geography(Point, 4326);
CREATE INDEX idx_telemetry_location ON telemetry_readings USING GIST(location);
```

### 4. Example Queries After Migration

```sql
-- Full-text search with highlighting
SELECT id, common_name, scientific_name,
  ts_headline('english', description, plainto_tsquery('organic coffee'),
    'StartSel=<mark>, StopSel=</mark>') AS highlighted_description,
  ts_rank(search_vector, plainto_tsquery('organic coffee')) AS rank
FROM taxonomy_items
WHERE search_vector @@ plainto_tsquery('organic coffee')
ORDER BY rank DESC
LIMIT 20;

-- Semantic similarity search
SELECT id, common_name,
  1 - (embedding <=> (SELECT embedding FROM taxonomy_items WHERE id = 42)) AS similarity
FROM taxonomy_items
WHERE id != 42
ORDER BY similarity DESC
LIMIT 10;

-- Find warehouses within 50km of a point
SELECT id, name, city,
  ST_Distance(location, ST_SetSRID(ST_MakePoint(55.27, 25.20), 4326)::geography) / 1000 AS distance_km
FROM warehouses
WHERE ST_DWithin(location, ST_SetSRID(ST_MakePoint(55.27, 25.20), 4326)::geography, 50000)
ORDER BY distance_km;
```

## Search Service Update

After migrating to PostgreSQL, update `backend/app/services/search_service.py`:

1. Replace `_trigram_similarity()` with native `pg_trgm` similarity:
   ```python
   result = await db.execute(text(
       "SELECT similarity(:term, common_name) AS sim FROM taxonomy_items WHERE similarity(:term, common_name) > 0.3"
   ), {"term": term})
   ```

2. Replace Levenshtein fallback with `pg_trgm` word similarity:
   ```sql
   SELECT word_similarity(:query, name) AS sim, name
   FROM item_names
   WHERE word_similarity(:query, name) > 0.4
   ORDER BY sim DESC LIMIT 5
   ```

3. Enable `ts_headline()` for result highlighting in search responses.

## Rollback

If migration is not yet complete, remove all PostgreSQL-specific columns:
```sql
DROP INDEX IF EXISTS idx_taxonomy_items_search;
DROP INDEX IF EXISTS idx_products_search;
DROP INDEX IF EXISTS idx_taxonomy_items_trgm;
DROP INDEX IF EXISTS idx_item_names_trgm;
DROP INDEX IF EXISTS idx_products_name_trgm;
DROP INDEX IF EXISTS idx_taxonomy_items_embedding;
DROP INDEX IF EXISTS idx_item_names_embedding;
DROP INDEX IF EXISTS idx_warehouses_location;
DROP INDEX IF EXISTS idx_telemetry_location;

ALTER TABLE taxonomy_items DROP COLUMN IF EXISTS search_vector;
ALTER TABLE taxonomy_items DROP COLUMN IF EXISTS embedding;
ALTER TABLE products DROP COLUMN IF EXISTS search_vector;
ALTER TABLE item_names DROP COLUMN IF EXISTS embedding;
ALTER TABLE warehouses DROP COLUMN IF EXISTS location;
ALTER TABLE shipments DROP COLUMN IF EXISTS origin_location;
ALTER TABLE shipments DROP COLUMN IF EXISTS destination_location;
ALTER TABLE telemetry_readings DROP COLUMN IF EXISTS location;