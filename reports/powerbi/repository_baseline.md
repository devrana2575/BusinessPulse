# Power BI Phase 9 repository baseline

Audit date: 2026-11-05
Repository: `devrana2575/BusinessPulse`
Branch/commit at audit start: `master` / `8fcd50d`

## Existing implementation

- Python pipeline: collection, cleaning, validation, MySQL import, SQL queries,
  EDA, opportunity scoring, and data-quality audit script.
- MySQL source assets: eight `CREATE TABLE` definitions, seven reporting views,
  seed/index scripts, a database dump, and 35 marked analytical queries.
- Existing Power BI assets: eight Power Query files (including a parameter
  setup note), a DAX measure library, a semantic-model description, a Power
  Query guide, a four-page visual specification, and screenshot instructions.
- Existing saved dataset: 2,252 raw and 2,252 cleaned listings; 12 cities and
  12 categories; 3 exact duplicates flagged and retained.
- No `.pbix` or Power BI screenshots are present. Python EDA figures are not
  Power BI evidence.
- `.env` exists locally and is ignored by Git. This report does not include
  credentials.

## Starting limitations

- The configured MySQL endpoint (`127.0.0.1:3307`, database `businesspulse`)
  refused a connection during this audit. Table/view declarations can be read
  from source SQL, but current live metadata and rows cannot be checked.
- Power BI Desktop is not installed/discoverable in this environment.
- Existing Power BI M/DAX and layout files are implementation assets, not proof
  of Power Query execution, DAX evaluation, report interaction or rendering.
- Existing `data/reports/reconciliation_report.csv` records 37 SQL/Python
  checks as passing; that report was generated 2026-11-02 and does not include
  Power BI values or a live database check from this audit.

## Current validation baseline

`python -m pytest -q` completed with **90 passed, 9 skipped**. The nine live
MySQL tests skipped because the configured local MySQL server refused the
connection. Power BI-specific validation was not available.

No source files or data were modified during baseline collection.
