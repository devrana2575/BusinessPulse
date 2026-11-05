# MySQL verification report

Audit date: 2026-11-05
Status: **BLOCKED** for live verification; source-level checks and historical
evidence are reported separately.

## Subsequent status update

The earlier connection-refused result below was superseded after MariaDB was
started manually. The WAMP `wampmariadb64` service was subsequently verified as
running, with port `3307` listening, but the configured `bp_user` login failed
with MariaDB error 1045. No password was tested or changed. An authorized
administrator session was not available, so account hosts, grants, server
version, schema contents and current row counts could not be inspected.

Port `3306` belongs to WAMP-bundled MySQL 9.1; port `3307` belongs to WAMP
MariaDB 11.5. Neither is the planned standalone Oracle MySQL instance. The
standalone server has not been installed or verified. Do not treat either
service as a successfully migrated target.

## Connection and import status

The application configuration was inspected without exposing credentials and
resolves the endpoint to host `127.0.0.1`, port `3307`, database `businesspulse`.
The initial read-only connection attempt failed with connection refused
(Windows socket error 10061). After the service was started manually, the
configured application login failed with error 1045. No database query was
successfully run and no schema or data was changed during these checks.

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

- Earlier command: `python -m pytest -q -m mysql`
- Earlier result: **9 skipped** when MySQL at `127.0.0.1:3307` refused the
  connection. The subsequent error 1045 means the listener is available, but
  does not verify database access.
- Current offline audit command: `python -m pytest -p no:cacheprovider -q -m
  "not mysql"`; result: **119 passed, 9 deselected**. Live MySQL tests were not
  run in this audit.
- Historical repository evidence dated 2026-11-02 reports 2,252 listings and
  audit rows, zero rejects, 35/35 SQL queries, and 37/37 SQL/Python
  reconciliation checks. See `docs/testing.md` and
  `data/reports/reconciliation_report.md`; these historical checks do not
  replace a live verification now.

## Required follow-up

After approval, establish an authorized standalone MySQL target or provide an
authorized administrator session for the intended instance. Verify the target
before querying it, then run:

```powershell
python -m pytest -q -m mysql
python -m analytics.sql_analysis.run_queries
python scripts/verify_reconciliation.py
```

Record the actual server version, schema inventory, counts, SQL NULL results
and test outcomes after those commands succeed. Do not publish credentials or
database connection strings containing passwords.
