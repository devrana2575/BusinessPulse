# BusinessPulse

A portfolio-ready **Data Analyst / BI** project built from a real OpenStreetMap
business-POI extract across 12 Indian cities. It covers the full workflow:
polite data collection, Python cleaning and validation, MySQL modelling, 35
analytical SQL queries, EDA, a transparent opportunity analysis, automated tests,
a database dump, and a specified four-page Power BI report.

> **Scope:** this is a **snapshot of collected public map listings**, not a
> business census, demand forecast, or investment recommendation. Contact data is
> often missing in OSM and is **not invented or enriched**. See
> [`docs/limitations.md`](docs/limitations.md).

## At a glance

| Item | Result |
|---|---|
| Snapshot | **2026-11-02** |
| Source | OpenStreetMap via Overpass API (ODbL 1.0) |
| Geography | 12 Indian cities with bounded search areas |
| Raw records | **2,252** |
| Cleaned listings | **2,252** |
| Cities / categories | **12** / **12** |
| Missing phone | **92.72%** |
| Missing address | **71.71%** |
| Strict completeness | **5.73%** (phone + address + not duplicate) |
| Exact duplicates | **3** flagged (retained for audit) |
| Analytical SQL | **35** queries, **35/35** executed |
| Coverage | **123/144** city × category pairs (**85.42%**) |
| Automated tests | **119 offline tests passed** in the current audit; 9 live MySQL tests were not run. The 2026-11-02 historical run reported 99 passed with MySQL. |
| Power BI | M/DAX/model/design assets exist; Power BI Desktop is installed, but PBIP/PBIR/TMDL generation, Desktop validation, PBIX and screenshots remain pending. |

Numbers above come from the generated reports in `data/reports/`; re-run the
pipeline to reproduce them. The Power BI assets are not claimed to have been
rendered here.

## Why this project exists

The interesting part is not a high completeness rate. It is building an honest,
auditable analysis when the real public data is incomplete:

- Every row keeps its OSM provenance and license.
- Missing contact data stays missing; the quality gap is measured, not hidden.
- Exact duplicates are flagged and retained, not silently deleted.
- SQL and Python recompute the opportunity score independently.
- Automated tests protect documented rules and the database contract.
- The Power BI layer is fully specified, while unverified rendering is labelled
  as pending.
- Business claims are limited to “underrepresentation in the collected sample”.

## Key findings

- **City volume is broad in this extract.** Surat has the largest sample (206, 9.15%) and Delhi the smallest (174, 7.73%); every city has at least 174 listings. This reflects the consistent collection frame and caps, not real-world city size.
- **Retail and Food & Beverage dominate.** Retail has 452 listings (20.07%) and Food & Beverage 447 (19.85%). Education & Training (2) and Other Services (8) are too thin for reliable city comparisons.
- **Contact data is the binding constraint.** 2,088 listings (92.72%) have no phone, 1,615 (71.71%) have no address, and only 129 (5.73%) meet the strict phone + address + not-duplicate rule. Missing values are flagged, not imputed.
- **Coverage is high but uneven.** 123 of 144 city x category pairs (85.42%) have at least one listing. 12 candidate cells are High tier, but 11 of those 12 have zero collected listings; they are source/sampling signals, not demand.
- **The score is a review queue, not a forecast.** The 2026-11-02 historical run recorded 35 SQL queries and 37 reconciliation checks passing, with 99 tests passing. In the current offline audit, 106 tests pass; live MySQL tests were not run. A prior login attempt failed with error 1045. The score cannot support investment or demand claims.

## Selected EDA outputs

![City distribution](data/reports/figures/fig_city_distribution.png)

![City × category coverage heat map](data/reports/figures/fig_city_category_heatmap.png)

![Top opportunity candidates](data/reports/figures/fig_opportunity_top15.png)

These are **Matplotlib outputs from the Python EDA/opportunity scripts**, not
Power BI dashboard screenshots. The full generated report is
[`docs/eda_report.md`](docs/eda_report.md).

## Power BI status

Power BI Desktop is installed from the Microsoft Store (version **2.159.883.0**;
PBIP, PBIR and TMDL are supported by this version). The repository currently
contains M, DAX, model and four-page design source files, but no generated
`.pbip`, `.pbix` or Power BI screenshots. Desktop refresh, model/DAX validation,
visual interactions and rendered evidence remain pending.

The local database investigation found WAMP MySQL 9.1 listening on port 3306
and WAMP MariaDB 11.5 listening on port 3307. The configured BusinessPulse
application login failed with MariaDB error 1045; current database contents
were not verified. Neither WAMP service is the planned standalone Oracle MySQL
instance. See the [Phase 9 audit](reports/powerbi/final_powerbi_audit.md),
[MySQL verification report](reports/powerbi/mysql_verification_report.md),
[metric reconciliation](reports/powerbi/metric_reconciliation.csv), and
[Power BI build guide](powerbi/README.md) for verified versus pending work.

## Architecture

```text
Overpass API
  → cached JSON + collection manifest
  → raw CSV (provenance preserved)
  → Python cleaning / validation / duplicate audit / quality score
  → MySQL (8 tables, 7 views, indexes, seed data)
  → 35 analytical SQL queries → CSV exports
  → EDA tables + 9 figures + generated report
  → transparent city × category opportunity analysis
  → Power BI model/DAX/report design (manual Desktop build)
```

There is **no** FastAPI, Flask, React, Streamlit, Node service, or deployed web
application. The full stack is Python, Pandas, NumPy, MySQL, SQL, Power BI,
Power Query and DAX.

See [`docs/architecture.md`](docs/architecture.md) for layer responsibilities,
failure handling, security and the star-schema design.

## Repository map

```text
analytics/
  data_collection/   Overpass collector, cache-aware raw builder
  cleaning/          normalisation, duplicate rules, quality scoring
  validation/        blocking/warning checks and row-level evidence
  sql_analysis/      execute the 35 SQL queries and export CSVs
  eda/               EDA tables, figures and report generation
  business_insights/ opportunity score, Python recomputation, chart
  reporting/         Matplotlib theme
database/
  schema.sql         8 base tables
  views.sql          7 reporting/opportunity views
  analytical_queries.sql
  seed_data.sql, indexes.sql
  businesspulse_dump.sql   final dump (generated)
data/
  raw/               raw CSV + collection manifest (HTTP cache is gitignored)
  processed/         cleaned data, audit/reject/duplicate files
  reports/           SQL outputs, EDA, figures, insights, reconciliation
scripts/
  setup_database.py, import_data.py, verify_reconciliation.py
  run_pipeline.py, export_database_dump.py
powerbi/
  dax_measures.dax, data_model.md, power_query_guide.md
  dashboard_design.md, power_query_m/*.pq, screenshots/README.md
docs/
  data_sources.md, methodology.md, architecture.md, data_dictionary.md
  eda_report.md, business_insights.md, testing.md, limitations.md, demo_script.md
tests/
```

## Quick start

### 1. Prerequisites

- Python 3.11+ (built with Python 3.14.4).
- Oracle MySQL Community Server 8.0+ is the target; the committed dump was
  generated by MySQL 9.1. The standalone server is not installed yet.
- Power BI Desktop is optional for Python/SQL deliverables and required for
  PBIP/PBIX generation and Desktop validation. The installed version is
  2.159.883.0.

### 2. Install

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
# Edit .env with your MySQL host/port/user/password.
```

The application user should have privileges on `businesspulse` and
`businesspulse_test`. The optional admin user is used by `setup_database.py`
for database/user provisioning. Never commit `.env`. Provision only an
explicitly approved, empty target database. Do not use `--reset` against an
existing database; it drops and recreates the selected database.

### 3. Set up MySQL and import

```powershell
# Only for an explicitly approved new database/account:
python scripts/businesspulse.py setup --database businesspulse --confirm-database-create --confirm-account-provisioning
python scripts/businesspulse.py clean --confirm-regenerate
python scripts/businesspulse.py validate
# Import requires a second, explicit confirmation after verifying the target:
python scripts/businesspulse.py import --database businesspulse --confirm-target-empty
```

`--replace-data` deletes existing listing, audit, reject and batch rows before
reimporting. Do not use it on an existing database unless that data replacement
has been explicitly approved.

### 4. Run the analytical layers

```powershell
python scripts/businesspulse.py analyze --database businesspulse
python scripts/businesspulse.py eda
python scripts/businesspulse.py insights --database businesspulse
python scripts/businesspulse.py reconcile --database businesspulse
python scripts/businesspulse.py report
```

Or run the staged safe workflow (MySQL reads require explicit target selection;
import remains opt-in):

```powershell
python scripts/businesspulse.py workflow --database businesspulse
python scripts/businesspulse.py workflow --database businesspulse --confirm-regenerate
# To opt into import, add both flags only after independently verifying the empty target:
python scripts/businesspulse.py workflow --database businesspulse --confirm-regenerate --include-import --confirm-target-empty
```

The `scripts/run_pipeline.py` compatibility wrapper delegates to this guarded
workflow; it does not import data unless the opt-in flags are supplied. It
does not support `--reset` or `--replace-data`.

Collection is not included in the safe workflow. It is polite and slow; run
these source modules separately only when the cache is missing or intentionally
refreshing:

```powershell
python -m analytics.data_collection.collect_osm_data
python -m analytics.data_collection.build_raw_dataset
```

### 5. Tests

```powershell
python -m pytest -q                    # unit + live MySQL tests
python -m pytest -q -m "not mysql"     # offline tests only
```

## Automation entry point

Use `scripts/businesspulse.py` for staged execution. Start with the
non-database-writing repository check. A database check performs only read
queries and requires explicit target selection:

```powershell
python scripts/businesspulse.py preflight
python scripts/businesspulse.py preflight --check-database --database businesspulse
```

The automation CLI requires database stages to use a loopback host and an
explicit database name matching local configuration. Credentials are never
written to its structured log. Individual stages are:

```powershell
python scripts/businesspulse.py clean --confirm-regenerate
python scripts/businesspulse.py validate
python scripts/businesspulse.py setup --database businesspulse --confirm-database-create --confirm-account-provisioning
python scripts/businesspulse.py import --database businesspulse --confirm-target-empty
python scripts/businesspulse.py analyze --database businesspulse
python scripts/businesspulse.py eda
python scripts/businesspulse.py insights --database businesspulse
python scripts/businesspulse.py reconcile --database businesspulse
python scripts/businesspulse.py report
```

For staged orchestration, run:

```powershell
python scripts/businesspulse.py workflow --database businesspulse
```

It skips cleaning unless `--confirm-regenerate` is provided, never includes
setup, and skips import unless both `--include-import --confirm-target-empty`
are supplied. Without `--database`,
all database-dependent stages are explicitly reported as skipped. A failed
critical stage stops the remaining stages. Each invocation appends structured
JSONL events to `data/reports/businesspulse_automation.jsonl` and prints a
stage-by-stage exit summary. `report` creates a presence-only index at
`data/reports/businesspulse_report_index.md` and `.json`; it does not assert
database or Power BI validation.

`clean` replaces derived cleaning outputs and therefore requires confirmation.
`setup` refuses to operate if the database already exists and requires separate
confirmation for database creation and application-account provisioning.
The underlying setup utility restricts newly provisioned accounts to the
configured loopback host; its account currently receives all privileges on the
target schema so it can apply the schema, indexes, seeds, and views. Review this
grant model before provisioning an account.
`import` verifies the schema and refuses targets with existing listings,
audits, rejects or import batches; the wrapper does not expose a replacement
mode. `analyze`, `insights`, and `reconcile` read MySQL and write result
artifacts. `report` creates a presence-only index and does not query MySQL. Run
setup and import only after separately approving the target and required
database or account changes. `run_pipeline.py` is a compatibility wrapper for
the guarded workflow, not an independent pipeline implementation.
The SQL safety check is deliberately conservative, not a complete MySQL parser;
it screens the checked-in query set for common mutation and side-effect syntax.
Review every new query before adding it. The standalone utility scripts remain
available for expert use and have lower-level flags that bypass these wrapper
gates. The server-version check rejects MariaDB, but cannot distinguish a
standalone MySQL service from a WAMP-bundled MySQL service; verify the service
identity before any approved database writes.

The Power BI automation/validation boundary is tracked in
[`powerbi/implementation_checklist.json`](powerbi/implementation_checklist.json).
It distinguishes reusable M/DAX/model source from the PBIP build, refresh,
measure/model validation, visual QA and genuine screenshots that remain
unverified in Desktop.

### 6. Dump and Power BI

```powershell
python scripts/export_database_dump.py
```

Then follow [`powerbi/README.md`](powerbi/README.md) to build the four-page
report. Power BI Desktop is installed, but no PBIP/PBIX or screenshots have
been generated or validated yet.

## Power BI pages

1. **Executive Overview** — volume, city/category mix, quality bands.
2. **Geographic Market Analysis** — map, city ranking, city × category heat map.
3. **Data Quality Analysis** — missing contact fields, quality bands,
   review queue.
4. **Market Opportunity** — methodology banner, top gaps, score decomposition,
   candidate detail.

The report uses a star schema (`FactListings`, `FactDataQuality`,
`FactCityCategoryCoverage`, `DimCity`, `DimCategory`, `DimSource`). The
opportunity score is always interpreted as a descriptive prioritisation, never
as demand. See [`powerbi/dashboard_design.md`](powerbi/dashboard_design.md).

## Verification status

| Status | Items |
|---|---|
| **VERIFIED** | Saved OSM collection, cleaning and validation artifacts; source DDL (8 tables/7 views); 35 query definitions; EDA and opportunity outputs; historical SQL/Python and database checks dated 2026-11-02; current offline tests |
| **IMPLEMENTED, NOT VERIFIED** | Power Query M queries; DAX measures; semantic-model and four-page design specifications |
| **PENDING** | Standalone MySQL installation and live validation; PBIP/PBIR/TMDL generation; Desktop refresh, relationships/measures/visuals; genuine screenshots; current live reconciliation |
| **NOT IMPLEMENTED** | Web/API/frontend; cloud deployment; scheduled refresh; customer/demand data; forecasting; full entity resolution |

No screenshot, `.pbix`, test result, database result, or data value in this
repository is fabricated. If a layer was not run, it is labelled as such.

## Documentation

| Document | Purpose |
|---|---|
| [`docs/data_sources.md`](docs/data_sources.md) | Source, license, city boxes, query design, provenance, collection limits |
| [`docs/methodology.md`](docs/methodology.md) | Cleaning, duplicate, quality, validation and opportunity definitions |
| [`docs/architecture.md`](docs/architecture.md) | End-to-end design and failure handling |
| [`docs/data_dictionary.md`](docs/data_dictionary.md) | Raw/cleaned/MySQL/Power BI field definitions |
| [`docs/business_insights.md`](docs/business_insights.md) | Findings with generated numbers and honest interpretation |
| [`docs/eda_report.md`](docs/eda_report.md) | Generated EDA report |
| [`docs/testing.md`](docs/testing.md) | Test strategy and actual final results |
| [`docs/limitations.md`](docs/limitations.md) | What the analysis cannot support |
| [`docs/demo_script.md`](docs/demo_script.md) | 5–7 minute walkthrough |
| [`powerbi/README.md`](powerbi/README.md) | Power BI status, build order, manual validation |

## Data ethics and license

The data is public business POIs from OpenStreetMap, licensed under ODbL 1.0.
Attribution: **© OpenStreetMap contributors**. The project does not scrape
private personal data, bypass access controls, or enrich missing fields from
other providers. A missing phone/address is reported as missing.

The collection started on the main Overpass endpoint and completed missing
groups through a public Overpass mirror after the main endpoint hit capacity.
The per-query endpoint is recorded in `data/raw/collection_manifest.json`; this
is a service-availability workaround, not a second data source.

If you reuse this project, preserve the OSM attribution and review ODbL
obligations. The analysis is educational and should not be used as the sole
basis for a commercial decision.
