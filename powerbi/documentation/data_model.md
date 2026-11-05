# BusinessPulse Power BI model contract

## Status and grain

This document describes the intended Import-mode semantic model. The queries
and relationships have **not** been loaded or validated in Power BI Desktop.
Column names and types below are derived from `database/schema.sql`,
`database/views.sql`, and the Power Query files; live database metadata was not
available during this audit.

| Model table | Source | Grain | Intended rows | Purpose |
|---|---|---|---:|---|
| `FactListings` | `vw_listing_detail` | One collected listing | 2,252 in the saved snapshot | Listing identity, category/city/source keys, published contact fields, date and coordinates |
| `FactDataQuality` | `vw_listing_detail` | One audit row per listing | 2,252 in the saved snapshot | Missing/valid flags, exact/potential duplicate flags, validation status and audit score |
| `FactCityCategoryCoverage` | `vw_market_opportunity` | One city × category | 12 × 12 = 144 in the saved snapshot | Counts, coverage, candidate criteria, score components and tier |
| `DimCity` | `dim_city` | One canonical city | 12 | City, state, country and centroid |
| `DimCategory` | `dim_category` | One analytical category | 12 | Category label, display order and description |
| `DimSource` | `dim_source` | One source | 1 | Source, license and attribution metadata |
| `stg_Listings` | `vw_listing_detail` | One collected listing | Same as listing fact | Typed, shared staging query; disable load |

Expected counts are saved-snapshot expectations, not fresh live-DB results.
`FactCityCategoryCoverage` is generated for cities represented in
`vw_city_summary` crossed with every dimension category.

## Column contract

All columns selected by the M queries are listed below. `listing_id`, dimension
IDs, and fact foreign keys are technical whole-number keys. `business_id` and
`source_record_id` are identifiers and must remain text. Flags are whole-number
0/1 values, not strings or Power BI booleans.

| Table | Columns | Type / meaning |
|---|---|---|
| `FactListings` | `listing_id` | Whole number; MySQL listing primary key |
| | `business_id`, `business_name`, `address`, `phone`, `source_record_id` | Text; stable project ID, name and public source values; missing contact remains null/blank |
| | `city_id`, `category_id`, `source_id` | Whole number foreign keys |
| | `collection_date` | Date; single snapshot date, not a time series |
| | `latitude`, `longitude` | Decimal number; listing coordinates, categorized as Latitude/Longitude |
| `FactDataQuality` | `listing_id` | Whole number; unique key matching one listing |
| | `missing_phone`, `missing_address` | Whole-number flags; missing in the source |
| | `duplicate_flag`, `potential_duplicate_flag` | Whole-number flags; exact duplicate retained, potential duplicate for review |
| | `phone_valid`, `address_valid` | Whole-number flags under the documented minimum usability rules |
| | `is_complete` | Whole-number flag; valid phone AND valid address AND not exact duplicate |
| | `validation_status`, `quality_band` | Text; validation state and derived audit-score band |
| | `quality_score` | Decimal 0–100; record usability score, not business quality |
| `FactCityCategoryCoverage` | `city_id`, `category_id` | Whole-number foreign keys to conformed dimensions |
| | `city_name`, `state_name`, `category_name` | Text attributes retained by the SQL view for tooltips/detail |
| | `listing_count`, `city_total`, `category_total`, `total_listings`, `categories_present`, `total_categories` | Whole-number counts |
| | `category_share_in_city_pct`, `national_category_share_pct`, `relative_representation` | Decimal ratios/percentages as defined by the SQL view |
| | `is_covered`, `is_candidate` | Whole-number flags |
| | `city_category_coverage_pct`, `city_completeness_pct`, `city_avg_quality_score` | Decimal city-level context |
| | `coverage_status`, `opportunity_tier`, `methodology_note` | Text interpretations supplied by SQL |
| | `underrepresentation_index`, `city_breadth_gap`, `reliability_index` | Decimal normalized score inputs |
| | `underrepresentation_points`, `breadth_points`, `reliability_points`, `opportunity_score` | Decimal score components and total; do not sum across pairs |
| | `underrepresentation_weight`, `city_breadth_weight`, `reliability_weight`, `high_threshold`, `medium_threshold` | Decimal configuration values from SQL |
| `DimCity` | `city_id`, `city_name`, `state_name`, `country`, `latitude`, `longitude` | Whole-number key; text geography; decimal centroid coordinates |
| `DimCategory` | `category_id`, `category_name`, `display_order`, `description` | Whole-number key/order and text attributes |
| `DimSource` | `source_id`, `source_name`, `source_type`, `source_url`, `license_name`, `license_url`, `attribution` | Whole-number key and source/license text |

The staging query also contains `FactListings` and `FactDataQuality` fields in
one typed rowset. It is not loaded. It intentionally does not impute blanks or
repeat cleaning already performed in Python.

## Relationships

| One side | Many/one side | Cardinality | Direction | Active |
|---|---|---|---|---|
| `DimCity[city_id]` | `FactListings[city_id]` | 1:* | Single | Yes |
| `DimCategory[category_id]` | `FactListings[category_id]` | 1:* | Single | Yes |
| `DimSource[source_id]` | `FactListings[source_id]` | 1:* | Single | Yes |
| `FactListings[listing_id]` | `FactDataQuality[listing_id]` | 1:1 | Both | Yes |
| `DimCity[city_id]` | `FactCityCategoryCoverage[city_id]` | 1:* | Single | Yes |
| `DimCategory[category_id]` | `FactCityCategoryCoverage[category_id]` | 1:* | Single | Yes |

Do not add direct city/category relationships to `FactDataQuality`: it is
filtered from `FactListings` over the 1:1 relationship. Do not relate the
city-category coverage fact to the listing fact; their grains differ. A source
filter does not affect opportunity scores because the opportunity view is
source-aggregated and contains no `source_id`.

Verify one-to-one uniqueness and relationship activation after loading. The
Power BI engine has not verified these relationships in this environment.

## Model properties and definitions

- Hide technical IDs from report view; retain them for relationships.
- Mark city/state/country columns with their appropriate geographic data
  categories. Set listing coordinate categories on the fact coordinates.
- Sort `DimCategory[category_name]` by `display_order`; do not aggregate IDs,
  flags, or coordinates.
- Keep `quality_score` and opportunity components numeric. Ratios in SQL views
  are expressed as percentage points where their names end in `_pct`; DAX
  measures that return fractions should use Power BI percentage formatting.
- Completeness is intentionally strict:
  `phone_valid = 1 AND address_valid = 1 AND duplicate_flag = 0`.
  Missing, present-but-invalid and exact duplicate states remain distinguishable.
- There is no `DimDate`: every listing belongs to the single 2026-11-02
  collection snapshot. A date hierarchy would suggest nonexistent trends.
- Use Import mode. Refresh after Python import and rerun the documented manual
  reconciliation checklist.

## Measure groups

The source measure library is `powerbi/dax_measures.dax`. It includes listing
counts, represented cities/categories/sources, listings per city, phone and
address availability, strict completeness, duplicate rates, quality bands,
city/category ranking and contribution, coverage, and the opportunity score
plus its three additive components.

`Listings with Complete Addresses` counts `address_valid = 1` under the
minimum address usability rule. `Address Availability Percentage` counts
nonblank addresses, including present-but-invalid values. Likewise, phone
availability means a source value is present; it is not a validity or
contactability claim. All measures remain subject to report filter context.

The opportunity score is SQL-authored and only exposed in DAX, not recomputed
in Power Query. It is a relative review-priority heuristic, not evidence of
demand, revenue, market share, profitability, or complete competition.
