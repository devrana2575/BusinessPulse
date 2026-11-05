# Testing strategy and results

## Status

**Current audit (2026-11-05):** 92 offline tests passed; all 9 live MySQL
integration tests skipped because the configured local server refused
connections. Power BI tests were not run because Desktop is not installed.
The 2026-11-02 historical run reported 99 passed, including MySQL integration;
that earlier result is not a live verification for this audit.

This page reports the actual commands and results from the build machine, not
hypothetical coverage.

## How to run

```powershell
# Offline: no database or credentials required
python -m pytest -q -m "not mysql"

# Everything, including the live MySQL integration and 35 SQL queries
python -m pytest -q
```

The live tests skip with a clear reason when MySQL is unavailable or the
database has not been imported. They never write to the database.

## Current audit results (2026-11-05)

Executed:

```text
$ python -m pytest -q
92 passed, 9 skipped
```

All 92 non-MySQL tests passed. Each of the 9 live integration tests skipped
because `127.0.0.1:3307` refused the connection. Therefore the database import,
live SQL views/queries and current database counts were not verified in this
audit. The historical MySQL results below are retained for provenance only.

## Test layers

| File | What it protects |
|---|---|
| `tests/test_cleaning.py` | Phone/address/name/city/category rules, category mapping, duplicate detection, quality score, rejects, no invented contact data |
| `tests/test_validation.py` | Blocking vs warning severities, duplicate keys, invalid coordinates, audit inconsistency, summary math |
| `tests/test_opportunity.py` | Score formula, null handling, weights, thresholds, tiers |
| `tests/test_import_helpers.py` | File/hash guards, boolean/date/null conversion, import column contract |
| `tests/test_assets.py` | 8 tables, 7 views, 35 queries, DAX/PQ/design presence, no fake PBIX/screenshots, no web framework |
| `tests/test_scripts.py` | Dump option quoting, project-root contract |
| `tests/test_mysql_integration.py` | Imported counts, quality reconciliation, city/category counts, 144-pair universe, opportunity formula, all 35 SQL queries |

The integration test is marked `mysql`; `pytest.ini` registers the marker.
Tests use the real cleaned CSV and the committed database state. A mismatch
fails rather than being silently tolerated.

## Historical results (2026-11-02)

Executed on **2026-11-02** against the final 12-city snapshot.

```text
$ python -m pytest -q
........................................................................ [ 72%]
...........................                                              [100%]
99 passed in 5.47s

$ python -m pytest -q -m "not mysql"
........................................................................ [ 80%]
..................                                                       [100%]
90 passed, 9 deselected in 2.54s
```

The nine MySQL tests cover the imported 2,252 listings, the 144-row coverage
universe, the opportunity formula, and execution of all **35/35** analytical
queries. They pass against the final MySQL database; they are not skipped.

Additional executed checks:

| Check | Actual result |
|---|---|
| SQL queries executed | 35 / 35, 0 failures (`data/reports/sql_query_results_index.csv`) |
| SQL ↔ Python reconciliation | 37 / 37 checks passed |
| Maximum SQL/Python opportunity score difference | 0.01 |
| Opportunity score mismatches / tier mismatches | 0 / 0 |
| Final database import | 2,252 listings, 2,252 audits, 0 rejects, 3 duplicates flagged |
| Database dump restore | 2,252 listings, 2,252 audits, 8 base tables, 7 views, 144 opportunity rows |
| Power BI Desktop | **NOT RUN** — not installed in the build environment |

The reconciliation report is committed at
`data/reports/reconciliation_report.md` and `.csv`. The database dump is
`database/businesspulse_dump.sql`; it was restored into a fresh database to
verify these counts and then the restore database was dropped.

## What is deliberately not tested

- Power BI Desktop rendering, relationship ambiguity, DAX execution, visual
  accessibility and screenshots. These require Desktop and are a manual
  checklist in `powerbi/README.md`.
- External validity of OSM coverage versus reality. Tests can prove internal
  consistency, not that a missing phone exists in real life.
- The opportunity score's ability to predict demand, revenue or success. The
  score is a heuristic; no such labels exist in the data.
- Network collection success under every Overpass failure mode. Retry/fallback
  behaviour is code-reviewed, but the public endpoint is outside the project's
  control.

## Why these tests matter

The most likely failures in this project are not syntax errors; they are silent
definition drift:

- a cleaning rule changes but the SQL view does not;
- a score is recomputed differently in Python and SQL;
- a dimension key is added to a fact table and creates an ambiguous relationship;
- an import rerun duplicates rows;
- a report claims completeness when contact fields are missing.

The tests and reconciliation target those risks directly. They do not turn the
dataset into a census or the opportunity score into a forecast.
