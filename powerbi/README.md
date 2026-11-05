# BusinessPulse — Power BI delivery README

## Status legend

- **VERIFIED IN THIS REPOSITORY:** source files exist; historical Python/MySQL
  SQL and integration checks are recorded.
- **GENERATED, NOT DESKTOP-VERIFIED:** a PBIP project with PBIR pages and a
  TMDL model exists. Static project and saved-data checks pass.
- **PENDING MANUAL ACTION:** opening/refreshing the PBIP, checking model/DAX and
  visual behavior, saving a PBIX, and capturing genuine screenshots.
- **NOT IMPLEMENTED:** anything not listed here. There is no web app, API,
  React frontend, fabricated screenshot, or fabricated `.pbix`.

Power BI Desktop is installed from the Microsoft Store (version **2.159.883.0**).
This version supports PBIP, PBIR and TMDL. The generated project is
[`generated/BusinessPulse.pbip`](./generated/BusinessPulse.pbip); it has not
yet been opened or validated in Desktop. No PBIX or Power BI screenshots exist.
If Desktop does not recognize the enhanced report format, enable PBIR support
in its report-format options before opening the project.

The PBIP uses a **self-contained offline snapshot** generated from the checked-in
`data/processed/cleaned_business_listings.csv` and
`data/reports/market_opportunities.csv`. Its Power Query M expressions embed
compressed copies of those files; refresh does not connect to MySQL and does
not read `.env`. Re-run the generator after updating the source CSVs. This
provides a saved-snapshot report while the planned standalone MySQL instance
remains unverified; it is not a live MySQL refresh.

The configured BusinessPulse application login previously failed against the
WAMP MariaDB service with error 1045. WAMP MySQL 9.1 and MariaDB 11.5 are
separate bundled services; neither is the planned standalone Oracle MySQL
instance. See [`../reports/powerbi/mysql_verification_report.md`](../reports/powerbi/mysql_verification_report.md)
and [`../reports/powerbi/final_powerbi_audit.md`](../reports/powerbi/final_powerbi_audit.md)
for the distinction between saved evidence and current live verification.

## Generate and validate

From the repository root:

```powershell
python scripts/build_powerbi_project.py
python scripts/build_powerbi_project.py --validate-only
```

The generator writes only to the dedicated `powerbi/generated/` directory. It
refuses to write into an existing unmarked directory and never touches MySQL,
services, credentials, or `.env`.
Its static checks inspect all 10 generated TMDL documents for valid document
headers, `///` documentation comments, table nesting/indentation, model table
references, relationships, description-property scope, and LF line endings.
Relationship properties are checked against the generated relationship
contract. TMDL `///` lines are object descriptions, not neutral file-header
comments; the relationship document therefore has no generated marker comment,
and static validation rejects documentation comments there because Power BI
Desktop reports that relationship descriptions are unsupported. Descriptions
remain allowed on other model objects at the owning object's property
indentation. See Microsoft's
[TMDL description syntax](https://learn.microsoft.com/en-us/analysis-services/tmdl/tmdl-overview?view=power-bi-premium-current#descriptions).
These checks are not a substitute for opening the project in Power BI Desktop.
The PBIR definition requires `definition/report.json`; it is generated with
the report schema alongside the pages and visuals. Power BI Desktop rejects
the separate legacy `BusinessPulse.Report/report.json` at the report-folder
root when it coexists with PBIR. During regeneration, the script removes only
an empty root-level legacy report with no sections and recognized hidden
Power BI auto-date table documents. It preserves non-empty or unrecognized
root report files and unknown table documents rather than deleting them.
Static validation requires `definition/report.json` and rejects a root-level
legacy report. After regeneration, verify the output with
`python scripts/build_powerbi_project.py --validate-only`.

The existing MySQL-view M templates under `power_query_m/` remain the future
live-source contract. The generated PBIP embeds offline data so the report can
be prepared without the prohibited database connection.

## Open and validate in Power BI Desktop

1. Open `powerbi/generated/BusinessPulse.pbip` in Power BI Desktop 2.159.883.0.
2. If prompted, enable PBIR enhanced report format. Confirm the local semantic
   model opens and the report shows all four pages.
3. Use **Refresh**. The project reads its embedded snapshot; it should not ask
   for MySQL credentials or make a database connection.
4. Verify the six tables, six relationships, 72 measures, query refresh, visual
   field bindings, and all 55 visuals. Check layout/formatting and test
   city/category/source slicers plus fact-to-quality filtering.
5. Reconcile Desktop values to the saved CSV/SQL/Python snapshot outputs. Record
   actual Desktop results before changing the checklist.
6. Only after these checks, save a `.pbix` and capture genuine screenshots.
   Do not describe the PBIX or screenshots as existing before they do.

## Generated model summary

The generated semantic model has six imported tables: `FactListings`,
`FactDataQuality`, `FactCityCategoryCoverage`, `DimCity`, `DimCategory`, and
`DimSource`. It has single-direction city/category/source dimension
relationships to the listing fact and coverage fact, and a bidirectional 1:1
`business_id` relationship between listings and quality. The saved source has
2,252 unique business IDs, 12 cities, 12 categories, 144 city-category pairs,
and 123 covered pairs. The listing collection date is typed as a date; a date
dimension and time-series visuals are intentionally absent.

`business_id` is the stable string key in this snapshot project. The retained
`listing_id` compatibility column aliases `business_id`; it is hidden and is
not marked as a second key. The snapshot does not fabricate database
auto-increment `listing_id` values. Offline source quality flags are converted
from CSV Boolean text to whole-number 0/1 columns.
`DimCity` and `DimCategory` keys come from the saved opportunity output, and
the single OSM source uses the seeded source ID. This is a snapshot model; the
MySQL-view templates and model contract document the later live database
source.

## Historical MySQL reconciliation checklist

These checks are for a later, separately approved MySQL-backed build. They
were not run in this phase. Do not connect this PBIP to MySQL.

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

Cross-check SQL for that later migration:

```sql
SELECT * FROM vw_data_quality_summary;
SELECT COUNT(*) FROM listing_master;
SELECT COUNT(*) FROM vw_market_opportunity;
SELECT COUNT(*) FROM vw_city_summary;
```

## Page screenshot checklist

See `screenshots/README.md`. At minimum capture:
`01_executive_overview.png`, `02_geographic_market_analysis.png`,
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
- Power BI Desktop is available, but project validation is pending. The
  generated embedded-snapshot M/DAX has not been evaluated there.
- Current live MySQL verification is pending when the configured local service
  is unavailable. The report distinguishes this from the historical
  SQL/Python reconciliation.

## Attribution

Data: © OpenStreetMap contributors, licensed under the Open Database License
(ODbL) 1.0. See `docs/data_sources.md`.
