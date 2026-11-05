# BusinessPulse - repository audit and route decision

Audit date: 5 Nov 2026. Method: extracted the uploaded ZIP (336 files), profiled the CSVs with pandas, read the Python, SQL, docs and existing Power BI assets. No database was contacted; no existing file was modified or deleted (new files only, under `powerbi/desktop_build/` and `scripts/`).

## 1. Documented figures vs actual files

| Figure | Documented | Actual | Source checked |
|---|---:|---:|---|
| Listings | 2,252 | **2,252** (2,252 distinct `business_id`) | `cleaned_business_listings.csv` |
| Cities | 12 | **12** (174-206 listings each) | same |
| Categories | 12 | **12** represented (Education & Training has only 2 listings) | same |
| City-category pairs | 144 | **144** | `market_opportunities.csv` |
| Covered pairs | 123 | **123** (85.42%) | same; matches SQL Q30 |
| Avg listings per city | 187.67 | **187.67** | |
| Exact duplicates | 3 | **3** (flagged, retained) | `final_duplicate_records.csv` |
| Missing phone / address | 2,088 / 1,615 | **2,088 / 1,615** | `validation_summary.csv` |
| Complete records | 129 (5.73%) | **129** | |

All documented figures held.

## 2. Available fields

`cleaned_business_listings.csv` (37 columns): ids, name, category, city, address, phone, `latitude`/`longitude`, source fields, `collection_date` (one value: 2026-11-02), `duplicate_flag`, `quality_score`, `is_complete`, `validation_status`, `quality_band`, validity/missing flags. **No** rating, review, revenue, population, area or opening-hours fields exist, so none were used. `market_opportunities.csv` (44 columns) holds the SQL view's opportunity components plus `python_*` recomputed columns (max difference 0.01, 0 mismatches).

## 3. Findings that change how the dashboard must be read

1. **City counts are a collection artifact.** Each city/group query is capped (`out center 35-60`, `analytics/constants.py`); `docs/limitations.md` calls the extract a "capped, non-random sample". The flat 174-206 range follows from this. The dashboard therefore avoids "market size" language and carries a footnote.
2. **"2,252 unique" is distinct IDs, not distinct businesses.** Three exact-duplicate groups are retained, so about 2,249 real-world businesses.
3. **11 of the 12 High-tier opportunity cells have zero listings** (the 12th has 1). Six involve Other Services, which has 8 listings nationally. These are best read as "check collection/tagging first", not as demand.
4. **The score includes a reliability term** (weight 0.15) that rewards cities with better contact completeness, so a data-rich city scores slightly higher for the same gap.
5. **12 Education & Training cells are "Insufficient evidence"** (2 national listings; rule requires >= 5). They are left unscored on Page 4.
6. **Quality dimensions requested in the brief:** invalid coordinates = 0, missing business names = 0, missing categories = 0 (unnamed OSM elements were excluded at collection: 233). The project's own coordinate rule is only the +-90/+-180 range; I additionally tested each point against the city's collection bounding box (0 outside).
7. **No inconsistency** between Python, SQL and CSV outputs was found. Live MySQL could not be checked (the repo's own audit reports error 1045 on the configured login; it was not bypassed).

## 4. Existing Power BI assets and route decision

`powerbi/generated/` is a PBIP/PBIR/TMDL project produced by `scripts/build_powerbi_project.py` (80 KB generator). `reports/powerbi/final_powerbi_audit.md` records that it was never successfully opened: Desktop errors on `SingleColumnRelationship`, duplicate `IsKey`, and a missing `report.json` each needed generator patches, and its status is still "PARTIAL / Desktop pending".

**Decision: do not rely on the generated PBIP.** It matches your own rule (do not keep regenerating TMDL), and I cannot open Power BI Desktop here, so I cannot confirm a new PBIP would load. I left it untouched. Instead this build gives you:

* clean star-schema CSVs reconciled to the existing outputs,
* M, DAX and theme generated from the real columns,
* an exact visual-by-visual Desktop guide.

Existing `powerbi/dax_measures.dax` (72 measures, MySQL-view model) and `powerbi/power_query_m/` (MySQL source) remain valid for a future live-database model; they are not the Desktop-build inputs here.
