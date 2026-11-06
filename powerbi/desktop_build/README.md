# BusinessPulse - Power BI dashboard (Desktop build kit)

Business-listing analytics for 12 Indian cities x 12 categories, built from the project's OpenStreetMap (Overpass API) dataset.

> **Status: build kit complete and reconciled offline; the report itself is not yet built.** No `.pbix` or screenshots exist because Power BI Desktop could not be run in the environment that produced this kit. Follow `BUILD_GUIDE.md` (about 3-4 h), then fill in `VALIDATION_REPORT.md`.

## Contents

| File | Purpose |
|---|---|
| `data/*.csv` | Six star-schema tables (generated; reconciled to Python/SQL outputs) |
| `powerquery/BusinessPulse.m` | Power Query for all six tables + `DataFolder` parameter |
| `measures.dax` / `MEASURES.md` | 50 measures with explanation, source columns and expected values |
| `BusinessPulse_theme.json` | Corporate theme (navy / teal / amber / coral) |
| `BUILD_GUIDE.md` | Setup, relationships, and exact field wells for all 4 pages |
| `VALIDATION_REPORT.md` | What is verified vs pending; expected values to tick off in Desktop |
| `AUDIT_REPORT.md` | Repository audit, findings and route decision |
| `reference_values.csv` | Pandas reference values for every headline measure |

Regenerate: `python scripts/export_powerbi_star_schema.py` then `generate_powerbi_dax_docs.py`, `generate_powerbi_m_and_theme.py`, `generate_powerbi_validation_report.py`.

## Data model

Star schema, six relationships, all one-to-many, single direction.

```
DimSource --> FactListings --> FactQualityIssues
DimCity ----> FactListings         (business_id: one listing, many audit rows)
DimCategory-> FactListings
DimCity ----> FactCityCategoryCoverage
DimCategory-> FactCityCategoryCoverage
```

| Table | Grain | Rows |
|---|---|---:|
| `FactListings` | one collected listing (lat/long, quality flags, score, band) | 2,252 |
| `FactQualityIssues` | one audit warning (from `validation_issues.csv`) | 3,762 |
| `FactCityCategoryCoverage` | one city x category (SQL view output incl. score parts) | 144 |
| `DimCity` / `DimCategory` / `DimSource` | one member | 12 / 12 / 1 |

Design choices: the two fact tables share conformed dimensions and never join directly (no ambiguous paths); the opportunity score is imported, not recomputed, so there is one formula (SQL, mirrored in Python); `FactDataQuality` was not created as a separate table because it would be a 1:1 copy of `FactListings` flags - the audit warnings table adds real new grain instead; no Date table because there is a single collection date.

## Pages

1. **Executive Overview** - KPIs, listings by category, listings by city, executive interpretation.
2. **Geographic Market Analysis** - listing map, top/bottom cities, concentration (top-city share, HHI), category mix and category coverage by city.
3. **Data Quality Analysis** - audit warnings by type, score bands, missing phone/address by city and category, duplicates.
4. **Market Opportunity Analysis** - city x category coverage matrix, ranked opportunity pairs, score breakdown, High/Medium counts by city and category.

## Executive interpretation (data-derived)

* **Scale and coverage.** 2,252 listings across 12 cities and 12 categories; 123 of 144 city-category cells (85.4%) contain at least one listing.
* **Categories are concentrated.** Retail (452) and Food & Beverage (447) are 39.9% of listings; the top three categories (adding Automotive) are 55.5%. Education & Training (2), Other Services (8) and Home & Repair Services (21) are thin.
* **Cities look even, by design.** Listings range from 174 (Delhi) to 206 (Surat); HHI is 0.0835 vs 0.0833 for a perfectly even split. This reflects capped collection queries, so city ranking is not a market-size ranking.
* **Data completeness is the main weakness.** 92.7% of listings lack a phone and 71.7% lack an address; only 129 (5.73%) meet the strict completeness rule. Average quality score is 63.4/100; 1,592 listings score below 60.
* **Quality varies.** Surat is best (14.6% complete, score 73.4); Hyderabad is worst on completeness (0.5%) and Delhi on score (57.6). Professional Services is the most complete category (19.4%); Finance & Banking (0.9% complete, 98.7% no phone) and Automotive (1.7%) are weakest.
* **Opportunity signal.** 132 cells are scoreable; 12 rate High and 5 Medium. Chandigarh has the most flagged cells (4). Other Services appears in 6 of the 12 High cells, and 11 of the 12 High cells have no listings at all.

## Analytical impact of the data-quality problems

Missing contact fields do not change counts or category/city comparisons, but they cap any contactability or lead-generation use: only about 7% of listings have a phone. The 3 retained duplicates inflate counts by 0.13%, which is immaterial. Because quality is uneven across cities, the opportunity score's reliability term and any cross-city comparison inherit that bias. Zero invalid coordinates and zero missing names or categories mean location and classification analysis is on solid footing.

## Opportunity score: what it is and is not

Methodology v1.0 (from the repository, unchanged): `100 x (0.60 x underrepresentation + 0.25 x city category-breadth gap + 0.15 x city completeness)`; High >= 60, Medium >= 40; candidates need a city with >= 20 listings and a category with >= 5 national listings. It is a **data-derived signal that a cell is thin in this capped OpenStreetMap sample**. A gap can mean mapper neglect, tagging conventions or query caps rather than an unserved market. It is **not** evidence of demand, revenue or low competition; validating it needs external data (population, footfall, spend, competitor registries).

## Data source and licence

Listings are from OpenStreetMap via the Overpass API, collected 2 Nov 2026. (c) OpenStreetMap contributors, available under the Open Database License (ODbL) 1.0: https://opendatacommons.org/licenses/odbl/1-0/ . Keep this attribution visible on the dashboard (page subtitle) and in any export.

## Honest limits

OSM is volunteered data, not a business census; the sample is capped and non-random; the dataset is a single snapshot with one source, so source and time comparisons are not possible; there is no revenue, rating or population data.
