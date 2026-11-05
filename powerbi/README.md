# BusinessPulse — Power BI delivery README

## Status legend

- **VERIFIED IN THIS REPOSITORY:** source files exist; historical Python/MySQL
  SQL and integration checks are recorded.
- **IMPLEMENTED, NOT VERIFIED:** DAX/Power Query text exists but has not been
  opened or executed in Power BI Desktop.
- **PENDING MANUAL ACTION:** building the `.pbix`, capturing screenshots,
  visual formatting, and Power BI-specific reconciliation.
- **NOT IMPLEMENTED:** anything not listed here. There is no web app, API,
  React frontend, fabricated screenshot, or fabricated `.pbix`.

Power BI Desktop is not installed on the build machine. The assets below are an
implementation guide, not a claim that a working PBIX was tested here. In the
current 2026-11-05 audit, the local MySQL server also refused connections; the
historical successful database run is recorded separately from current status.

The current execution also could not connect to the configured local MySQL
service. See [`../reports/powerbi/mysql_verification_report.md`](../reports/powerbi/mysql_verification_report.md)
and [`../reports/powerbi/final_powerbi_audit.md`](../reports/powerbi/final_powerbi_audit.md)
for current verification status.

## What is in this folder

```
powerbi/
├── dax_measures.dax              # measure library (all six sections)
├── data_model.md                 # tables, relationships, model properties
├── documentation/data_model.md   # detailed table/column and relationship contract
├── power_query_guide.md          # connection and refresh steps
├── dashboard_design.md           # four report pages, visual by visual
├── power_query_m/
│   ├── Parameters.pq             # parameter instructions (comments only)
│   ├── stg_Listings.pq           # staging query (load disabled)
│   ├── FactListings.pq
│   ├── FactDataQuality.pq
│   ├── FactCityCategoryCoverage.pq
│   ├── DimCity.pq
│   ├── DimCategory.pq
│   └── DimSource.pq
└── screenshots/
    └── README.md                 # capture checklist; no fake images
```

## Build order (manual)

1. Install Power BI Desktop and the MySQL connector (see
   `power_query_guide.md`).
2. Open **Get data → MySQL database** and create the two parameters
   `MySqlServer` and `MySqlDatabase`.
3. Create blank queries and paste each file from `power_query_m/`, renaming the
   query exactly as documented.
4. Set `stg_Listings` to **Do not load**; load the other six tables.
5. Create the six relationships in `documentation/data_model.md`; verify cardinality and
   filter direction.
6. Add the measures from `dax_measures.dax` (or paste section by section), then
   apply the format strings and data categories.
7. Build the four pages exactly as specified in `dashboard_design.md`.
8. Refresh, run the reconciliation checks below, save as
   `businesspulse.pbix` (or another clearly named file), and capture the
   screenshots listed in `screenshots/README.md`.

## Model validation checklist (manual, Power BI Desktop)

Record the actual values in the table after refresh. Do not pre-fill them.

| Check | Expected | Actual | Result |
|---|---|---|---|
| `FactListings` row count | Equals MySQL `listing_master` count | | |
| `FactDataQuality` row count | Equals `FactListings` row count | | |
| `FactCityCategoryCoverage` row count | Equals cities-with-listings × 12 | | |
| `Distinct Cities` | Equals MySQL `vw_city_summary` count | | |
| `Distinct Categories` | Equals categories with ≥1 listing | | |
| `Complete Listings` | Equals MySQL `vw_data_quality_summary.complete_listings` | | |
| `Completeness %` | Equals SQL completeness % ± 0.1 pp | | |
| `Average Quality Score` | Equals SQL average ± 0.1 | | |
| `High Opportunity Gaps` | Equals SQL count of candidate High-tier pairs | | |
| Relationship integrity | No blank city/category rows in facts | | |
| Date table | Absent by design (single snapshot) | | |

Cross-check SQL:

```sql
SELECT * FROM vw_data_quality_summary;
SELECT COUNT(*) FROM listing_master;
SELECT COUNT(*) FROM vw_market_opportunity;
SELECT COUNT(*) FROM vw_city_summary;
```

## Page screenshot checklist

See `screenshots/README.md`. At minimum capture:
`01_executive_overview.png`, `02_geographic_coverage.png`,
`03_data_quality.png`, `04_market_opportunity.png`, plus one filter-interaction
shot. A screenshot is evidence of the rendered report only. It is not evidence
that the underlying data is complete.

## Honest limitations

- This project has **one real data source** (OpenStreetMap via Overpass API).
  Source analysis is descriptive only; no cross-source ranking is claimed.
- Contact data is missing for most records. The report displays that limitation;
  it does not impute phone numbers or addresses.
- The opportunity score is a transparent prioritization heuristic based on
  underrepresentation, city breadth and data reliability. It is not a demand,
  revenue, or competition forecast.
- Source filtering applies to listing-level visuals only. The opportunity view
  has no source key and is aggregated across sources; this snapshot has only
  one source.
- The report is a snapshot, not a time series.
- Power BI Desktop validation is pending; the DAX/PQ files are not claimed to
  have been executed here.
- Current live MySQL verification is pending when the configured local service
  is unavailable. The report distinguishes this from the historical
  SQL/Python reconciliation.

## Attribution

Data: © OpenStreetMap contributors, licensed under the Open Database License
(ODbL) 1.0. See `docs/data_sources.md`.
