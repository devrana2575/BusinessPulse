# MySQL verification report

Audit date: 2026-11-05
Status: **BLOCKED** for live verification; source-level checks and historical
evidence are reported separately.

## Connection and import status

The application configuration resolves the MySQL endpoint to host
`127.0.0.1`, port `3307`, database `businesspulse`. Credentials are configured
locally and are intentionally not included here. A read-only connection attempt
failed with connection refused (Windows socket error 10061). No database query
ran and no schema or data was changed.

The database cannot be marked verified from this execution. The tracked
`database/businesspulse_dump.sql`, import scripts and reports document a prior
import, but are not evidence of the current live database contents.

## Source-declared schema inventory

The following inventory is from `database/schema.sql`, not live
`information_schema` metadata.

| Base table | Declared primary key | Notable declared foreign keys |
|---|---|---|
| `dim_city` | `city_id` | — |
| `dim_category` | `category_id` | — |
| `dim_source` | `source_id` | — |
| `import_batches` | `batch_id` | `source_id → dim_source.source_id` |
| `listing_master` | `id` | `city_id → dim_city.city_id`; `category_id → dim_category.category_id`; `source_id → dim_source.source_id` |
| `data_quality_audit` | `audit_id` | `listing_id → listing_master.id` (unique, one audit per listing) |
| `listing_rejects` | `reject_id` | `import_batch_id → import_batches.batch_id` |
| `opportunity_config` | `config_id` | — |

Unique constraints declared by DDL include city/category/source names,
`listing_master.business_id`, `(source_id, source_record_id)`, and
`data_quality_audit.listing_id`. Listing address and phone are nullable; other
required columns use `NOT NULL` constraints. IDs are integer types, contact
fields are text types, coordinates and audit scores are decimals, and dates
use `DATE`/timestamps as appropriate.

Seven reporting views are declared in `database/views.sql`:
`vw_listing_detail`, `vw_city_summary`, `vw_category_summary`,
`vw_source_summary`, `vw_data_quality_summary`,
`vw_city_category_coverage`, and `vw_market_opportunity`.
`database/analytical_queries.sql` contains 35 marked queries.

## Saved-data findings (not current live-DB results)

The checked-in output files describe the 2026-11-02 data snapshot:

| Measure | Saved result |
|---|---:|
| Raw / cleaned listings | 2,252 / 2,252 |
| City / category dimensions | 12 / 12 |
| Missing phone values | 2,088 (92.72%) |
| Missing address values | 1,615 (71.71%) |
| Exact duplicate flags | 3 (0.13%); retained for audit |
| Strictly complete records | 129 (5.73%) |
| City-category coverage | 123 / 144 (85.42%) |

These are CSV-derived missingness/quality figures, not a new inspection of
database NULLs. A SQL NULL count, current live row count, current table/view
inventory, actual distributions, and current import-batch status remain
unverified.

## Test results and historical verification

- Current command: `python -m pytest -q -m mysql`
- Result: **9 skipped** because MySQL at `127.0.0.1:3307` refused the connection.
- Full current suite after the Power BI asset/documentation updates:
  **92 passed, 9 skipped**.
- Historical repository evidence dated 2026-11-02 reports 2,252 listings and
  audit rows, zero rejects, 35/35 SQL queries, and 37/37 SQL/Python
  reconciliation checks. See `docs/testing.md` and
  `data/reports/reconciliation_report.md`; these historical checks do not
  replace a live verification now.

## Required follow-up

Start or configure the project MySQL service, confirm the imported database,
then run:

```powershell
python -m pytest -q -m mysql
python -m analytics.sql_analysis.run_queries
python scripts/verify_reconciliation.py
```

Record the actual server version, schema inventory, counts, SQL NULL results
and test outcomes after those commands succeed. Do not publish credentials or
database connection strings containing passwords.
