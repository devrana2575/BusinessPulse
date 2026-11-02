# Architecture

## 1. Overview

BusinessPulse is a local, file-and-database analytics project. There is no web
framework, API service, JavaScript frontend, or cloud deployment. The stack is
Python, Pandas, NumPy, MySQL, SQL, Power Query and DAX, with Power BI Desktop as
the reporting layer.

```
Overpass API
    │  bounded, polite requests + JSON cache
    ▼
data/raw/osm_responses/*.json  +  collection_manifest.json
    │  build_raw_dataset.py
    ▼
data/raw/business_listings_raw.csv
    │  run_cleaning.py (normalise, validate, duplicate rules, score)
    ▼
data/processed/cleaned_business_listings.csv  + audit/reject files
    │  run_validation.py
    ▼
validation reports / blocking-row evidence
    │  import_data.py (one transaction)
    ▼
MySQL: 8 base tables, 7 views, 35 analytical queries
    ├── analytics/sql_analysis/run_queries.py → CSV exports
    ├── analytics/eda/run_eda.py → tables, figures, EDA report
    ├── analytics/business_insights/opportunity_analysis.py → scoring/chart
    └── Power BI (manual) → four-page report
```

## 2. Layer responsibilities

| Layer | Files | Responsibility |
|---|---|---|
| Collection | `analytics/data_collection/` | Query Overpass, retry, cache, build immutable raw CSV, preserve provenance |
| Cleaning | `analytics/cleaning/` | Normalise fields, map categories, detect duplicates, score quality, write audit outputs |
| Validation | `analytics/validation/` | Severity-based checks, blocking-row evidence, summary metrics |
| Storage | `database/`, `scripts/setup_database.py`, `scripts/import_data.py` | Schema, indexes, seeds, views, transactional import |
| SQL analytics | `database/analytical_queries.sql`, `analytics/sql_analysis/` | 35 reusable business queries and CSV results |
| EDA | `analytics/eda/` | Distribution/quality tables, 9 figures, Markdown report |
| Opportunity | `analytics/business_insights/` | Recompute score in Python, export top gaps and chart, fail on SQL mismatch |
| BI assets | `powerbi/` | Import queries, star-schema design, DAX, four-page specification |
| Verification | `tests/`, `scripts/verify_reconciliation.py` | Rule tests, asset contracts, live DB reconciliation, SQL/Python checks |
| Documentation | `README.md`, `docs/`, `powerbi/*.md` | Method, dictionary, findings, limits, demo and build instructions |

## 3. Database model

Eight base tables:

- **Dimensions:** `dim_city`, `dim_category`, `dim_source`.
- **Facts:** `listing_master`, `data_quality_audit`.
- **Operations:** `import_batches`, `listing_rejects`.
- **Configuration:** `opportunity_config`.

Seven views:

- `vw_listing_detail` — listing + dimension attributes + quality flags.
- `vw_city_summary` — city-level counts, completeness, source/category diversity.
- `vw_category_summary` — category counts including zero-listing categories.
- `vw_source_summary` — descriptive source metrics.
- `vw_data_quality_summary` — one-row overall quality snapshot.
- `vw_city_category_coverage` — complete city × category universe with baselines.
- `vw_market_opportunity` — scored candidate gaps, weights and methodology text.

The schema is normalized for lookup integrity, while views expose BI-ready
denormalized shapes. Power BI imports views/dimensions and keeps the star
schema in the semantic model.

## 4. Transactional import

`scripts/import_data.py`:

1. checks extension, size and required columns;
2. runs validation and removes blocking rows;
3. computes SHA-256 of the file;
4. opens one `engine.begin()` transaction;
5. optionally deletes existing listing/audit/reject/batch rows
   (`--replace-data`);
6. rejects a previously imported source/hash pair;
7. resolves/creates dimensions by canonical name;
8. inserts listing and audit rows;
9. records validation rejects and cleaning-stage rejects;
10. marks the batch `completed` with counts;
11. commits atomically or rolls back on error.

The `uq_listing_source_record` and `uq_listing_business_id` constraints provide
a second line of defence. Duplicate flagged rows are intentionally retained for
the data-quality analysis; they are not silently deleted.

## 5. Power BI model

The star schema has:

- `DimCity`, `DimCategory`, `DimSource` → `FactListings` (1:many);
- `FactListings` → `FactDataQuality` (1:1);
- `DimCity`, `DimCategory` → `FactCityCategoryCoverage` (1:many).

`FactDataQuality` deliberately omits city/category keys to avoid two filter
paths. The opportunity fact is at a different grain and does not relate to
`FactListings`. There is no date dimension because the data is one snapshot.

See `powerbi/data_model.md`, `powerbi/power_query_m/*.pq`, and
`powerbi/dax_measures.dax`.

## 6. Failure handling

| Failure | Behaviour |
|---|---|
| Overpass 429/5xx/timeout | Exponential backoff with jitter; failed query recorded |
| Invalid cached JSON | Skipped during raw build; no crash on one corrupt file |
| Unnamed/unmapped/non-business POI | Skipped and counted in raw build summary |
| Missing contact data | Retained as missing; flagged; never imputed |
| Blocking validation row | Excluded from import, recorded in `listing_rejects` |
| Repeated import file | Rejected by hash unless `--replace-data` |
| SQL/Python score mismatch | Opportunity analysis raises and reconciliation fails |
| Power BI unavailable | Assets documented; PBIX/screenshots marked pending |
| MySQL unavailable | Integration tests skip with a reason; setup requires `.env` |

## 7. Reproducibility

- Python dependencies are pinned with minimum versions in `requirements.txt`.
- `.env` is gitignored; `.env.example` contains placeholders only.
- Collection responses are cached and the manifest records query provenance.
- Cleaning rules are pure functions with tests.
- The import is one transaction with a file hash guard.
- Analytical SQL is source-controlled and exported with row counts.
- The database dump is generated from the committed final state.
- Power BI manual validation is a checklist, not an implied automated test.

## 8. Security and privacy

- Public business POIs only; no customer records, transactions, or private data.
- Database credentials live in `.env` and are never printed in docs or dumps.
- The `.env` file is excluded from git; `.env.example` has no real password.
- The MySQL user is limited to the application database, not a superuser.
- Power BI should use the application user, not root.
- The repo does not claim a deployed public database; do not expose port 3306/3307
  to the internet without a security review.

## 9. Known architectural limitations

- One source and one snapshot; no source comparison or time intelligence.
- Capped, non-random OSM samples; city/category counts are not population
  estimates.
- Rule-based category mapping and duplicate detection.
- The opportunity score is a heuristic, not a demand model.
- Power BI Desktop validation is pending; no `.pbix` is stored.
- The local MySQL server was started manually for development; deployment is out
  of scope.
