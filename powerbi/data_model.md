# BusinessPulse — Power BI semantic model

## Status

**IMPLEMENTED AS FILES — NOT EXECUTED IN POWER BI DESKTOP.**

Power BI Desktop is not installed in the environment used to build this
repository. The DAX library, Power Query queries, model design and report
specification are complete source-controlled assets. A `.pbix` file and
dashboard screenshots are **PENDING MANUAL ACTION**. No screenshot or PBIX is
included, and none should be invented.

The model is intentionally small and explicit: a listing fact table, a 1:1
data-quality fact table, a city × category coverage fact table, and three
conformed dimensions. All tables import from the MySQL reporting views or
dimension tables.

## Tables

| Power BI table | MySQL object | Grain | Rows (expected) | Load |
|---|---|---|---:|---|
| `FactListings` | `vw_listing_detail` | One collected listing | Total cleaned listings | Yes |
| `FactDataQuality` | `vw_listing_detail` | One row per listing | Total cleaned listings | Yes |
| `FactCityCategoryCoverage` | `vw_market_opportunity` | One city × category | Cities with listings × 12 | Yes |
| `DimCity` | `dim_city` | One city | 12 | Yes |
| `DimCategory` | `dim_category` | One category | 12 | Yes |
| `DimSource` | `dim_source` | One source | 1 | Yes |
| `stg_Listings` | `vw_listing_detail` | One listing | Same as fact | **No** (staging only) |

`FactDataQuality` uses the same view but only the quality/audit columns. The
staging query is referenced by both fact queries. It is not loaded to the model.

## Relationships

| From | To | Cardinality | Cross-filter | Active |
|---|---|---|---|---|
| `DimCity[city_id]` | `FactListings[city_id]` | 1 → many | Single | Yes |
| `DimCategory[category_id]` | `FactListings[category_id]` | 1 → many | Single | Yes |
| `DimSource[source_id]` | `FactListings[source_id]` | 1 → many | Single | Yes |
| `FactListings[listing_id]` | `FactDataQuality[listing_id]` | 1 → 1 | Both | Yes |
| `DimCity[city_id]` | `FactCityCategoryCoverage[city_id]` | 1 → many | Single | Yes |
| `DimCategory[category_id]` | `FactCityCategoryCoverage[category_id]` | 1 → many | Single | Yes |

Do **not** relate `DimCity` or `DimCategory` directly to `FactDataQuality`.
That would create two filter paths to the quality table and make the model
ambiguous. City/category filters flow through `FactListings` to
`FactDataQuality` through the 1:1 relationship. This is why the quality query
does not import city or category IDs.

`FactCityCategoryCoverage` is a separate fact table at a different grain. It
does not relate to `FactListings`; the city and category dimensions filter it
directly. Cross-filter direction between the two fact tables is not needed for
the four report pages.

## Model properties to set manually

### Data types and summarization

| Table | Column | Type | Summarization |
|---|---|---|---|
| `FactListings` | `listing_id`, `business_id`, `city_id`, `category_id`, `source_id`, `source_record_id` | Text/whole number | Do not summarize |
| `FactListings` | `latitude`, `longitude` | Decimal number | Do not summarize; data category Latitude/Longitude |
| `FactListings` | `collection_date` | Date | Do not summarize |
| `FactDataQuality` | `listing_id` | Text/whole number | Do not summarize |
| `FactDataQuality` | flag columns (`missing_*`, `duplicate_*`, `is_complete`) | Whole number | Do not summarize |
| `FactDataQuality` | `quality_score` | Decimal number | Average (default in cards; measures still control report values) |
| `FactCityCategoryCoverage` | IDs and flag columns | Whole number | Do not summarize |
| `FactCityCategoryCoverage` | score/rate/points columns | Decimal number | Do not summarize; use explicit measures |
| `DimCity` | `city_id` | Whole number | Do not summarize |
| `DimCategory` | `category_id`, `display_order` | Whole number | Do not summarize |
| `DimSource` | `source_id` | Whole number | Do not summarize |

### Format strings

| Measure/column | Format |
|---|---|
| `Total Listings`, counts | Whole number, thousands separator |
| `Completeness %`, `Missing Phone %`, `Missing Address %`, `Duplicate Rate %`, `Category Coverage %`, all contribution/share measures | Percentage, 1 decimal |
| `Average Quality Score` | Decimal, 1 decimal |
| `Opportunity Score`, `Top Opportunity Score` | Decimal, 1 decimal |
| `Snapshot Date` | `yyyy-mm-dd` |
| `Underrepresentation Points`, `Breadth Points`, `Reliability Points` | Decimal, 1 decimal |

### Data categories and sort order

- `DimCity[city_name]`: City; `DimCity[state_name]`: State or Province;
  `DimCity[country]`: Country.
- `FactListings[latitude]` / `[longitude]`: Latitude / Longitude. The map page
  uses these fact coordinates, not the city centroids.
- Set `DimCategory[category_name]` to sort by `DimCategory[display_order]`.
- Hide `FactListings[listing_id]`, `business_id`, `source_record_id`,
  `city_id`, `category_id`, `source_id`; hide all dimension keys; hide
  `DimCategory[display_order]`; hide `FactDataQuality[listing_id]`.
- Hide the staging query and disable its load.

## Why there is no date table

There is one collection snapshot (`2026-11-02`). A month/quarter/year hierarchy
would add a misleading time series: all rows would fall on one day. The model
therefore exposes `Snapshot Date` and `Collection Snapshot Label` as cards, not
a trend line. If later snapshots are collected, add a real `DimDate` table
marked as a date table, relate it to `FactListings[collection_date]`, and only
then add time-intelligence measures.

## Storage and refresh

- Storage mode: **Import** for all tables. The dataset is a static portfolio
  snapshot; scheduled refresh is not configured.
- Recommended refresh after re-running the Python import:
  1. Run `python scripts/import_data.py --replace-data`.
  2. Open the PBIX, **Refresh** all queries.
  3. Run the manual reconciliation checks in `powerbi/README.md`.
- The MySQL server must be reachable from the machine running Power BI
  Desktop. For a public portfolio, do not expose the database port to the
  internet; use a local/private connection and document the limitation.

## Model integrity checks

- `FactDataQuality` row count = `FactListings` row count.
- `FactCityCategoryCoverage` row count = cities with listings × 12.
- Cities and categories with no listings remain in `DimCity`/`DimCategory` but
  do not inflate `FactListings`.
- The opportunity view is filtered to cities with at least one listing; the
  12-city universe used in SQL/reconciliation is a cross join of the same
  cities.
- The model has no calculated tables that could mask missing data.

## Security and privacy

The source contains publicly published business POIs, including public phone
numbers and addresses where OSM contributors supplied them. Missing values are
left blank. Do not add customer-level or private personal data. No row-level
security is implemented; this is a single-analyst portfolio project.

## Known limitations

- One source prevents source-adjusted comparison.
- Contact completeness is low in the source; the model reports it rather than
  filling it.
- The opportunity score measures underrepresentation in **collected listings**,
  not demand, revenue, footfall or competition.
- Power BI-specific validation (relationships, measure execution, visual
  rendering, accessibility checker) remains pending until Desktop is available.
