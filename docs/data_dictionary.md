# Data dictionary

## 1. Raw CSV (`data/raw/business_listings_raw.csv`)

Grain: one accepted OSM business element per row. Missing contact values are
blank; no enrichment.

| Column | Type | Description |
|---|---|---|
| `business_id` | text | Deterministic project ID: `BP-OSM-{N|W|R}-{osm_id}` |
| `business_name` | text | Published `name`, `name:en`, or `brand` |
| `category` | text | One of 12 analytical categories, assigned from OSM tags |
| `category_raw` | text | Rule that produced the category (e.g. `amenity=restaurant`) |
| `city` | text | Canonical city from the collection frame |
| `state_name` | text | State/UT from city metadata |
| `country` | text | `India` |
| `address` | text | Address assembled only from published `addr:*` tags |
| `phone` | text | Raw published phone value |
| `phone_raw` | text | Preserved raw phone value (same as `phone` in the raw build) |
| `latitude` | decimal | OSM node coordinate or way/relation center |
| `longitude` | decimal | OSM node coordinate or way/relation center |
| `source` | text | `OpenStreetMap (Overpass API)` |
| `source_type` | text | `Open Data - Crowdsourced Map` |
| `source_record_id` | text | OSM element key, e.g. `node/123` |
| `source_record_url` | text | Public OSM element URL |
| `collection_date` | date | Snapshot date (`2026-11-02`) |
| `created_at` | datetime | Collection timestamp at midnight UTC for the snapshot |
| `collection_group` | text | Overpass group that returned the element |
| `osm_tags_json` | JSON text | Original OSM tags for provenance/audit |

## 2. Cleaned CSV (`data/processed/cleaned_business_listings.csv`)

Grain: one accepted listing after normalisation; exact duplicates are retained
and flagged. This is the import contract.

| Column | Type | Description |
|---|---|---|
| `business_id` | text | Unique project listing ID |
| `business_name` | text | Normalised display name |
| `name_key` | text | Lowercase alphanumeric comparison key |
| `category` | text | Canonical analytical category |
| `category_raw` | text | Original OSM rule |
| `city` | text | Canonical city |
| `state_name` | text | State/UT |
| `country` | text | Country |
| `address` | text | Normalised address or blank |
| `address_key` | text | Lowercase alphanumeric comparison key |
| `phone` | text | Normalised first phone number or blank |
| `phone_raw` | text | Raw phone from source |
| `phone_key` | text | Digits only, used for duplicate detection |
| `phone_valid` | boolean | Phone passes the documented 7–15 digit rule |
| `address_valid` | boolean | Address has ≥2 tokens and ≥6 characters |
| `missing_phone` | boolean | No phone value after normalisation |
| `missing_address` | boolean | No address value after normalisation |
| `latitude` | decimal | Validated coordinate or blank |
| `longitude` | decimal | Validated coordinate or blank |
| `source` | text | Source name |
| `source_type` | text | Source type |
| `source_record_id` | text | OSM element key |
| `source_record_url` | text | OSM element URL |
| `collection_date` | date | Snapshot date |
| `created_at` | datetime | Source collection timestamp |
| `duplicate_flag` | boolean | Exact duplicate, retained for audit |
| `duplicate_group` | text | `DUP-####` group for flagged duplicates |
| `duplicate_reason` | text | `name + city + address` or `name + city + phone` |
| `kept_business_id` | text | Canonical listing retained for the group |
| `potential_duplicate_flag` | boolean | Similar address, review only |
| `potential_duplicate_reason` | text | Evidence/similarity for review |
| `is_complete` | boolean | Valid phone AND valid address AND not exact duplicate |
| `validation_status` | enum text | `valid`, `needs_review`, `invalid` |
| `quality_score` | integer | Documented 0–100 audit score |
| `quality_band` | text | High (80–100), Medium (60–79), Low (<60) |
| `audit_timestamp` | datetime | Time the audit was generated |
| `cleaning_notes` | text | Duplicate/review note |

Audit side files:

| File | Grain / use |
|---|---|
| `data/processed/rejected_records.csv` | Rejected cleaning rows with reason and raw JSON |
| `data/processed/duplicate_records.csv` | Exact duplicates and their canonical listing |
| `data/processed/potential_duplicate_records.csv` | Similar-address review pairs |
| `data/processed/cleaning_log.csv` | Step-level row counts |
| `data/reports/data_quality_summary.csv` | Metric/definition/quality KPIs |
| `data/reports/missing_values_report.csv` | Missing counts for raw and cleaned data |
| `data/reports/validation_issues.csv` | Row-level blocking/warning evidence |
| `data/reports/validation_summary.csv` | Validation counts and percentages |

## 3. MySQL base tables

### `dim_city`

| Column | Type | Notes |
|---|---|---|
| `city_id` | INT UNSIGNED PK | Surrogate key |
| `city_name` | VARCHAR(100) UNIQUE | Canonical city |
| `state_name` | VARCHAR(100) | State/UT |
| `country` | VARCHAR(100) | Default India |
| `latitude` | DECIMAL(10,7) | City centroid |
| `longitude` | DECIMAL(10,7) | City centroid |
| `created_at`, `updated_at` | TIMESTAMP | Audit timestamps |

### `dim_category`

| Column | Type | Notes |
|---|---|---|
| `category_id` | INT UNSIGNED PK | Surrogate key |
| `category_name` | VARCHAR(100) UNIQUE | Canonical category |
| `display_order` | SMALLINT | Presentation order |
| `description` | VARCHAR(255) | Category scope |
| `created_at`, `updated_at` | TIMESTAMP | Audit timestamps |

### `dim_source`

| Column | Type | Notes |
|---|---|---|
| `source_id` | INT UNSIGNED PK | Surrogate key |
| `source_name` | VARCHAR(150) UNIQUE | Source name |
| `source_type` | VARCHAR(100) | Open data type |
| `source_url` | VARCHAR(500) | Overpass endpoint |
| `license_name` | VARCHAR(150) | ODbL 1.0 |
| `license_url` | VARCHAR(500) | Licence URL |
| `attribution` | VARCHAR(255) | © OpenStreetMap contributors |
| `created_at` | TIMESTAMP | Audit timestamp |

### `listing_master`

| Column | Type | Notes |
|---|---|---|
| `id` | BIGINT UNSIGNED PK | Surrogate key |
| `business_id` | VARCHAR(40) UNIQUE | Project listing ID |
| `business_name` | VARCHAR(255) | Display name |
| `category_id` | FK → `dim_category` | Category |
| `city_id` | FK → `dim_city` | City |
| `address` | VARCHAR(500) NULL | Public address or NULL |
| `phone` | VARCHAR(64) NULL | Public phone or NULL |
| `source_id` | FK → `dim_source` | Source |
| `source_record_id` | VARCHAR(64) | OSM key; unique per source |
| `collection_date` | DATE | Snapshot date |
| `latitude`, `longitude` | DECIMAL(10,7) NULL | Coordinates |
| `created_at` | DATETIME | Source timestamp |
| `updated_at` | TIMESTAMP | Row update timestamp |

Unique keys: `business_id`; `(source_id, source_record_id)`.

### `data_quality_audit`

| Column | Type | Notes |
|---|---|---|
| `audit_id` | BIGINT UNSIGNED PK | Surrogate key |
| `listing_id` | BIGINT UNSIGNED FK UNIQUE | 1:1 with listing |
| `missing_phone` | BOOLEAN | No phone |
| `missing_address` | BOOLEAN | No address |
| `duplicate_flag` | BOOLEAN | Exact duplicate |
| `potential_duplicate_flag` | BOOLEAN | Review-only flag |
| `phone_valid` | BOOLEAN | Phone rule |
| `address_valid` | BOOLEAN | Address rule |
| `is_complete` | BOOLEAN | Strict completeness |
| `validation_status` | ENUM | `valid`/`needs_review`/`invalid` |
| `quality_score` | DECIMAL(5,2) | 0–100 check constraint |
| `audit_timestamp` | TIMESTAMP | Audit time |

### `import_batches`

| Column | Type | Notes |
|---|---|---|
| `batch_id` | BIGINT UNSIGNED PK | Import run |
| `source_id` | FK | Source |
| `file_name` | VARCHAR(255) | Cleaned CSV name |
| `file_hash` | CHAR(64) | SHA-256; unique per source |
| `rows_received` | INT UNSIGNED | CSV rows |
| `rows_inserted` | INT UNSIGNED | Listing rows inserted |
| `rows_rejected` | INT UNSIGNED | Validation + cleaning rejects |
| `rows_flagged_duplicate` | INT UNSIGNED | Retained duplicates |
| `imported_at` | TIMESTAMP | Import time |
| `status` | ENUM | started/completed/failed |
| `notes` | VARCHAR(500) | Import summary |

### `listing_rejects`

| Column | Type | Notes |
|---|---|---|
| `reject_id` | BIGINT UNSIGNED PK | Reject row |
| `import_batch_id` | FK NULL | Batch |
| `source_record_id` | VARCHAR(64) NULL | OSM key |
| `business_name` | VARCHAR(255) NULL | Name |
| `city_name`, `category_name` | VARCHAR(100) NULL | Raw context |
| `rejection_reason` | VARCHAR(500) | Documented reason |
| `raw_record` | JSON | Original row |
| `rejected_at` | TIMESTAMP | Time |

### `opportunity_config`

| Column | Type | Notes |
|---|---|---|
| `config_id` | TINYINT PK | 1 for the active definition |
| `underrepresentation_weight` | DECIMAL(5,4) | 0.60 |
| `city_breadth_weight` | DECIMAL(5,4) | 0.25 |
| `reliability_weight` | DECIMAL(5,4) | 0.15 |
| `high_threshold` | DECIMAL(5,2) | 60 |
| `medium_threshold` | DECIMAL(5,2) | 40 |
| `min_city_listings` | SMALLINT | 20 |
| `min_category_national_count` | SMALLINT | 5 |
| `updated_at` | TIMESTAMP | Config update |

## 4. Reporting views

### `vw_listing_detail`

One row per listing; joins city/category/source and left-joins audit. Adds
`phone_available`, `address_available`, `review_required` and `quality_band`.
Use this for the Power BI listing fact and quality fact staging.

### `vw_city_summary`

One row per city with at least one listing. Includes listing count, categories
present, source count, missing phone/address counts and percentages, duplicate
count/rate, complete count/percentage, average quality, review count, category
coverage % and city share %.

### `vw_category_summary`

One row per seeded category, including zero-listing categories. Includes counts,
cities present, completeness, duplicates, quality and category/city coverage.

### `vw_source_summary`

One row per seeded source. Descriptive metrics only; the current dataset has one
source, so this is not a comparison.

### `vw_data_quality_summary`

One row overall: total listings, missing phone/address, duplicate and potential
duplicate counts, completeness, valid/review counts, average/min/max quality.

### `vw_city_category_coverage`

One row per city with listings × all 12 categories. Includes listing count,
city/category totals, within-city share, national category share, relative
representation, coverage status, candidate flag, category coverage, completeness
and quality. This is the analytical universe.

### `vw_market_opportunity`

One row per city × category candidate/universe with the documented decomposition:
underrepresentation, breadth gap, reliability, points, opportunity score, tier,
weights, thresholds and methodology note.

## 5. Power BI field names

The semantic model uses the same snake_case columns for auditability:

- `FactListings`: listing and contact attributes, city/category/source keys,
  coordinates and collection date.
- `FactDataQuality`: flags, validation status, score and band only; no
  city/category keys.
- `FactCityCategoryCoverage`: opportunity metrics and raw counts.
- `DimCity`, `DimCategory`, `DimSource`: descriptive dimensions.

Measures and format strings are in `powerbi/dax_measures.dax` and
`powerbi/data_model.md`.

## 6. Output files

| Path | Content |
|---|---|
| `data/reports/sql/Q01…Q35_*.csv` | One CSV per analytical query |
| `data/reports/sql_query_results_index.csv` | Query status/row-count index |
| `data/reports/eda_report.md` | Generated EDA report |
| `data/reports/figures/*.png` | Nine Matplotlib EDA figures |
| `data/reports/market_opportunities.csv` | Full 144-row opportunity universe |
| `data/reports/top_opportunities.csv` | Top 25 candidate gaps |
| `data/reports/underrepresented_categories_by_city.csv` | Candidates below 0.50 relative representation |
| `data/reports/coverage_summary.csv` | Coverage KPI summary + score check |
| `data/reports/opportunity_score_check.csv` | SQL vs Python score/tier evidence |
| `data/reports/reconciliation_report.csv` / `.md` | Cross-layer checks |
| `database/businesspulse_dump.sql` | Schema + seed + final data dump |
