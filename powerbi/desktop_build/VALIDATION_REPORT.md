# BusinessPulse - validation report

Last updated: 2026-11-05

## 0. Automated project and current Desktop outcome

`scripts/build_powerbi_desktop_project.py` generates `generated/BusinessPulse.pbip` from the six checked-in CSV snapshots, `powerquery/BusinessPulse.m`, `measures.dax`, and the supplied theme. The generated project contains six source tables, a `_Measures` host table, six relationships, 50 measures, four PBIR pages, and 59 visual definitions. Offline validation confirms the four page definitions and their field bindings; it does not prove that Desktop can render them.

Power BI Desktop 2.159.883.0 was available. Its local Analysis Services engine loaded the model, and the following representative DAX results were observed:

| Desktop query result | Expected from snapshots | Desktop result | Match |
|---|---:|---:|---|
| Total Listings | 2,252 | 2,252 | Yes |
| Quality Issue Rows | 3,762 | 3,762 | Yes |
| Total Pairs | 144 | 144 | Yes |
| Total Cities | 12 | 12 | Yes |
| Pair Coverage % | 85.42% | 85.42% | Yes |

**Blocking limitation:** Desktop showed a blank report canvas for the generated PBIR report. The PBIR preview toggle was not present in the visible Preview features list. No report visuals or slicer interactions were confirmed in Desktop. No `.pbix` was saved and no dashboard screenshots were captured. The PBIP is therefore a generated project with a Desktop-tested semantic model, not yet a verified working dashboard.

## 1. What has and has not been validated

| Layer | Status | Evidence |
|---|---|---|
| Source data, row counts, distinct keys | **VERIFIED (offline)** | 2,252 listings, 3,762 quality-issue rows, 144 city-category pairs; source and dimension keys checked by the generator. |
| Star-schema CSV export vs Python/SQL outputs | **VERIFIED (offline)** | `scripts/export_powerbi_star_schema.py` asserts 12 reconciliations (row counts, keys, city counts vs SQL Q02, pair counts, flags vs `validation_summary.csv`, score diff <= 0.02) and exits non-zero on any failure. All passed. |
| Live MySQL | **NOT RUN** | No database was touched. The repo's own audit reports the configured login blocked; saved 2026-11-02 SQL outputs were used instead. |
| Power Query / model table load | **VERIFIED (Desktop engine)** | The local model exposed all six CSV tables and the `_Measures` table; observed row-count measures reconcile with the snapshots. |
| Relationships / cardinality | **PARTLY VERIFIED** | Six relationships and their directions/cardinalities are defined and statically checked in the generated TMDL; Desktop loaded the model and representative measures. Full Model-view inspection remains outstanding. |
| DAX measures (50) | **PARTLY VERIFIED** | Static reference validation passed; representative measures evaluated in Desktop and reconciled above. All 50 measures were not individually evaluated in Desktop. |
| Four report pages / visual bindings | **GENERATED, NOT DESKTOP-VERIFIED** | Four page definitions and 59 visual field bindings pass offline structural checks. Desktop showed a blank canvas. |
| Slicer interactions / cross-filtering | **NOT VERIFIED** | Cannot validate interactions while generated pages do not render. |
| `.pbip` project | **GENERATED; model loaded** | `generated/BusinessPulse.pbip`; visual report rendering is unresolved. |
| `.pbix` file | **NOT CREATED** | Not saved because Desktop showed a blank report canvas. |
| Dashboard screenshots | **NOT CREATED** | No genuine Desktop-rendered page screenshots are available. |
| Offline automated tests | **VERIFIED** | `python -m pytest tests/test_powerbi_desktop_project.py tests/test_powerbi_project.py -q`: 31 passed. Generator validation also passed. |

## 2. Snapshot measure reconciliation

Expected values are computed with pandas from the exported CSVs, independent of DAX.

| measure | expected_value | power_bi_result | match |
|---|---:|---:|---|
| Total Listings | 2252.0 | 2252.0 | Yes |
| Unique Businesses | 2252.0 | Not individually queried | — |
| Total Cities | 12.0 | 12.0 | Yes |
| Total Categories | 12.0 | Not individually queried | — |
| Avg Listings per City | 187.67 | Not individually queried | — |
| Total Pairs | 144.0 | 144.0 | Yes |
| Covered Pairs | 123.0 | Not individually queried | — |
| Pair Coverage % | 85.42 | 85.42 | Yes |
| Candidate Pairs | 132.0 | Not individually queried | — |
| High-tier Pairs | 12.0 | Not individually queried | — |
| Medium-tier Pairs | 5.0 | Not individually queried | — |
| Low-tier Pairs | 115.0 | Not individually queried | — |
| Insufficient-evidence Pairs | 12.0 | Not individually queried | — |
| Highest Opportunity Score | 66.92 | Not individually queried | — |
| Avg Opportunity Score (candidates) | 15.83 | Not individually queried | — |
| Duplicate Count | 3.0 | Not individually queried | — |
| Missing Phone Count | 2088.0 | Not individually queried | — |
| Missing Address Count | 1615.0 | Not individually queried | — |
| Invalid Phone Count | 5.0 | Not individually queried | — |
| Invalid Address Count | 54.0 | Not individually queried | — |
| Invalid Coordinate Count | 0.0 | Not individually queried | — |
| Outside City Bbox Count | 0.0 | Not individually queried | — |
| Missing Business Name Count | 0.0 | Not individually queried | — |
| Complete Records | 129.0 | Not individually queried | — |
| Complete Records % | 5.73 | Not individually queried | — |
| Avg Quality Score | 63.36 | Not individually queried | — |
| Needs-review Records | 2123.0 | Not individually queried | — |
| Quality Issue Rows | 3762.0 | 3762.0 | Yes |
| Data Quality Issue Count | 3765.0 | Not individually queried | — |
| Largest City Listings | 206.0 | Not individually queried | — |
| Smallest City Listings | 174.0 | Not individually queried | — |
| Top City Share % | 9.15 | Not individually queried | — |
| City HHI (0-1) | 0.0835 | Not individually queried | — |

## 3. Slicer-state checks

Expected values for per-city and per-category views. Compare with Page 1/2/3 visuals.

### By city

| city_name | listings | categories | missing_phone | missing_address | duplicates | complete | avg_quality | pbi_listings | pbi_categories | pbi_avg_quality |
|---|---|---|---|---|---|---|---|---|---|---|
| Surat | 206 | 10 | 176 | 76 | 1 | 30 | 73.45 |  |  |  |
| Chennai | 201 | 10 | 191 | 174 | 0 | 10 | 59.33 |  |  |  |
| Pune | 192 | 11 | 177 | 141 | 0 | 10 | 63.1 |  |  |  |
| Ahmedabad | 192 | 11 | 178 | 119 | 2 | 12 | 65.42 |  |  |  |
| Bengaluru | 190 | 11 | 177 | 119 | 0 | 9 | 65.61 |  |  |  |
| Jaipur | 189 | 10 | 165 | 130 | 0 | 21 | 65.11 |  |  |  |
| Hyderabad | 186 | 9 | 182 | 168 | 0 | 1 | 57.77 |  |  |  |
| Mumbai | 185 | 10 | 175 | 126 | 0 | 8 | 63.86 |  |  |  |
| Kolkata | 182 | 11 | 169 | 130 | 0 | 7 | 63.38 |  |  |  |
| Chandigarh | 179 | 9 | 167 | 145 | 0 | 8 | 60.95 |  |  |  |
| Lucknow | 176 | 11 | 164 | 126 | 0 | 9 | 63.38 |  |  |  |
| Delhi | 174 | 10 | 167 | 161 | 0 | 4 | 57.61 |  |  |  |

### By category

| category_name | listings | cities | complete | avg_quality | pbi_listings |
|---|---|---|---|---|---|
| Retail | 452 | 12 | 33 | 64.78 |  |
| Food & Beverage | 447 | 12 | 28 | 63.3 |  |
| Automotive | 351 | 12 | 6 | 61.48 |  |
| Hospitality | 275 | 12 | 26 | 63.33 |  |
| Health & Pharmacy | 244 | 12 | 14 | 67.15 |  |
| Finance & Banking | 224 | 12 | 2 | 58.93 |  |
| Fitness & Recreation | 124 | 11 | 3 | 59.76 |  |
| Professional Services | 62 | 11 | 12 | 71.05 |  |
| Beauty & Personal Care | 42 | 11 | 2 | 63.69 |  |
| Home & Repair Services | 21 | 10 | 2 | 67.62 |  |
| Other Services | 8 | 6 | 1 | 63.75 |  |
| Education & Training | 2 | 2 | 0 | 55.0 |  |

## 4. Interaction tests

| # | Action | Expected | Result |
|---|---|---|---|
| 1 | City slicer = Hyderabad | Listings 186; Total Categories 9; Uncovered Pairs 3; Covered Pairs 9 | |
| 2 | Category slicer = Retail | Listings 452; City Coverage % 100% | |
| 3 | Category slicer = Education & Training | Listings 2; City Coverage % 16.7%; Avg Opportunity Score blank (no candidates) | |
| 4 | City = Chandigarh | High Opportunity Pairs = 2 (Other Services, Home & Repair Services) | |
| 5 | Any slicer state | `[Pair Listings]` = `[Total Listings]` | |
| 6 | Click Surat on Page 2 bar | Map shows only Surat points | |
| 7 | Tier slicer = High | Page 4 ranking table shows 12 rows; High Opportunity Pairs = 12 | |

## 5. Known honest limits

* "Unique" listings: 2,252 distinct `business_id`s, but 3 exact duplicate groups are flagged and retained, so distinct real-world businesses are about 2,249.
* City listing counts come from capped collection queries (`docs/limitations.md`); do not read them as market size.
* Invalid-coordinate and missing-name/category counts are genuinely 0.
* The reliability term in the opportunity score adds points for better-completed cities; read scores as a ranked review list, not a forecast.
