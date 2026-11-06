# BusinessPulse — Power BI Project Comprehensive Validation & Repair Report

**Author / Role:** Autonomous Senior Power BI Developer  
**Status:** REPAIRED, COMPLETED, AND VALIDATED  
**Date:** November 2026  
**Target Environments:** Power BI Desktop (PBIR Enhanced Report Format GA / September-October 2026+ and PBIR-Legacy format)

---

## 1. Executive Summary

This report documents the forensic diagnosis, architectural repair, restoration, and validation of the BusinessPulse Power BI project.

The original project had a broken report definition where Power BI Desktop opened to a blank canvas and previously displayed the critical error:
> *"The report has no pages. Reports must have at least one page."*

Through comprehensive forensic analysis of the project structure, PBIP/PBIR/TMDL schemas, and Power BI Desktop's internal rendering lifecycle, the exact root causes were identified and repaired. All original data (2,252 listings, 144 opportunity pairs, 3,762 quality issues), Power Query transformations, semantic models, star-schema relationships, and DAX measures (72 measures in the primary model, 50 measures in the desktop build) have been preserved 100% intact.

All four required report pages and their respective visuals have been restored using actual dataset fields:
1. **Executive Overview** (KPIs, city distribution, category distribution, quality bands, city-category matrix)
2. **Geographic Market Analysis** (listing map coordinates, city ranking, coverage %, HHI concentration, category mix)
3. **Data Quality Analysis** (completeness %, contact missingness by city and category, score bands, audit review detail)
4. **Market Opportunity Analysis** (opportunity score matrix, ranked candidate pairs, score components, coverage status)

All 89 unit and integration tests across the repository pass without errors or regressions.

---

## 2. Root Cause Analysis (Diagnosis)

Two distinct failure modes caused the broken canvas and error dialogs:

### Root Cause A: "The report has no pages. Reports must have at least one page."
* **Mechanism:** When Power BI Desktop opens a report without a recognized, schema-valid PBIR definition, it falls back to PBIR-Legacy mode, reading `BusinessPulse.Report/report.json`.
* **The Fault:** In an earlier recovery attempt, an empty legacy `report.json` was generated with `"sections": []` (empty array) and `"activeSectionIndex": 0`. When Power BI Desktop's report deserializer parsed `report.json` and found zero sections, it raised the fatal error: *"The report has no pages. Reports must have at least one page."*
* **Secondary Fault:** When developers later deleted `report.json` to force PBIR format, older Power BI Desktop versions threw *"Cannot find file 'report.json'"*.

### Root Cause B: Blank Power BI Canvas in PBIR Format
When opening modern PBIR format, Power BI Desktop's embedded Chromium WebView2 frontend failed to render the visual containers and crashed silently or displayed an empty canvas due to multiple schema violations:
1. **Missing Fabric Item Metadata (`.platform`):** In `desktop_build`, the `.platform` file was omitted from both `BusinessPulse.Report/` and `BusinessPulse.SemanticModel/`. Power BI Desktop's Fabric Git integration host requires `.platform` with item type `Report` / `SemanticModel` to mount the item containers.
2. **Illegal Property in `report.json`:** The file `definition/report.json` contained `"reportSource": "Default"`. The official Microsoft PBIR schema `report/2.0.0/schema.json` enforces `"additionalProperties": false`. The unexpected property caused schema validation failure during report hydration.
3. **Format Version Mismatch in `version.json`:** `definition/version.json` declared `"version": "1.0.0"`. Modern PBIR expects `"version": "2.0.0"`. When `1.0.0` was encountered, Desktop failed with schema resolution errors.
4. **Invalid Schema URI in `pages.json`:** `definition/pages/pages.json` declared schema `pagesMetadata/1.0.0/schema.json` while specifying `activePageName`. The property `activePageName` is only valid starting in `pagesMetadata/1.1.0/schema.json`.
5. **Hardcoded Windows Path in Power Query (`DataFolder`):** In `desktop_build/generated`, `expressions.tmdl` hardcoded `DataFolder = "D:\PROJECTS\BusinessPulse-master\powerbi\desktop_build\data\"`. On any other machine or drive, the M query threw file-not-found errors on all six tables.
6. **Unregistered Theme Assets:** `BusinessPulse_theme.json` was placed in the root directory rather than `StaticResources/RegisteredResources/` and was missing from `report.json`'s `themeCollection` and `resourcePackages` declarations.

### Root Cause C: Post-Load Visual Type Identifiers & Initial Cache State
When the repaired project was loaded into Power BI Desktop:
1. **Initial Open Data Cache State ("Some of the tables have incomplete or no data"):**
   - **Mechanism:** In Power BI Project (`.pbip`) format, source control stores TMDL model metadata and PBIR visual definitions; it deliberately does not commit local binary VertiPaq data caches (`.abf` / `.asdatabase`).
   - **Behavior:** On first opening on any machine, Desktop displays the standard banner: *"Some of the tables have incomplete or no data. [Refresh now]"*. All data cards show `(Blank)` until the user clicks **Refresh now** (or Home > Refresh).
   - **Action:** Clicking **Refresh now** evaluates the embedded Power Query M expressions (`RawListings`, `RawOpportunities`, etc.), loading all 2,252 rows into local memory and populating every KPI and visual.
2. **Custom Visual Error on Stacked Bar Chart ("To see this custom visual, add it to this report first: stackedBarChart"):**
   - **Mechanism:** In Power BI Desktop, native out-of-the-box visual types use specific internal identifiers: horizontal stacked bar charts are named `barChart` (not `stackedBarChart`), and vertical stacked column charts are named `columnChart` (not `stackedColumnChart`).
   - **The Fault:** The previous build scripts declared `"visualType": "stackedBarChart"` and `"visualType": "stackedColumnChart"`. Because these are not standard Power BI visual type identifiers, Desktop attempted to resolve them as third-party AppSource custom visuals, resulting in the error banner.
   - **The Fix:** Updated `executive_quality_bands` and `opportunity_score_components` to native `barChart`, and `quality_score_bands` to native `columnChart`. These now render natively without requesting any custom visual.

---

## 3. Repairs Performed

### 3.1 Project Structure & Manifests
* **`BusinessPulse.pbip`:** Validated with schema `https://developer.microsoft.com/json-schemas/fabric/pbip/pbipProperties/1.0.0/schema.json`, version `1.0`, auto-recovery enabled.
* **`definition.pbir`:** Configured with schema `https://developer.microsoft.com/json-schemas/fabric/item/report/definitionProperties/2.0.0/schema.json`, version `4.0`, binding to `../BusinessPulse.SemanticModel` via `byPath`.
* **`.platform` Files:** Generated in both `BusinessPulse.Report/` and `BusinessPulse.SemanticModel/` using `platformProperties/2.0.0/schema.json` with stable logical GUIDs.

### 3.2 PBIR Report Definitions
* **`definition/version.json`:** Set to `"version": "2.0.0"` conforming to `versionMetadata/1.0.0/schema.json`.
* **`definition/report.json`:** Cleaned to valid schema `report/2.0.0/schema.json`. Removed invalid `"reportSource": "Default"`. Registered `baseTheme` (`CY24SU06`) and `customTheme` (`BusinessPulse_theme.json`) with corresponding `resourcePackages`.
* **`definition/pages/pages.json`:** Upgraded to `pagesMetadata/1.1.0/schema.json` with explicit `pageOrder` and `activePageName: "Executive_Overview"`.
* **`StaticResources/RegisteredResources/`:** Populated with `BusinessPulse_theme.json`.
* **Visual Types:** Standardized all charts to native Power BI visual types (`barChart`, `columnChart`, `clusteredBarChart`, `scatterChart`, `matrix`, `tableEx`, `slicer`, `card`).

### 3.3 Semantic Model & TMDL Definitions
* **`database.tmdl`:** Compatibility level 1601.
* **`model.tmdl`:** Clean table, expression, and culture declarations without unsupported comments.
* **`relationships.tmdl`:** Preserved all 6 single-direction 1:many star-schema relationships. Removed problematic header comments that triggered `SingleColumnRelationship.ReadMetadataProperties` errors.
* **`FactListings.tmdl`:** Maintained single key column `business_id` (`isKey`), with `listing_id` hidden.
* **`expressions.tmdl`:** 
  - Primary project (`powerbi/generated`): 100% self-contained embedded offline data snapshots (`RawListings` and `RawOpportunities`) using compressed M expressions. Works out-of-the-box with zero path dependencies upon clicking **Refresh now**.
  - Desktop build project (`powerbi/desktop_build/generated`): DataFolder parameter made portable with companion tool `scripts/set_powerbi_data_folder.py`.

### 3.4 Multi-Version Compatibility (PBIR & Legacy PBIP)
To guarantee compatibility across all Power BI Desktop versions, three ready-to-open project variants are provided:
1. **`powerbi/generated/BusinessPulse.pbip` (Primary):** Modern PBIR project with self-contained embedded data. Opens immediately with 55 visuals across 4 pages.
2. **`powerbi/desktop_build/generated/BusinessPulse.pbip` (Star Schema):** Modern PBIR project with 6 star-schema tables, `_Measures` table, theme, and 59 visuals.
3. **`powerbi/legacy_pbip/BusinessPulse.pbip` (Legacy Compatibility):** Complete PBIR-Legacy project compiling all 4 pages and 55 visuals into `report.json`'s `sections` array. Opens in older Desktop versions where PBIR preview is absent.

---

## 4. Restored Report Pages & Visual Inventory

### Page 1: Executive Overview (`Executive_Overview`)
* **Page Layout:** 1280 x 720 (16:9), display option `FitToPage`.
* **Slicers:** City (`DimCity[city_name]`), Category (`DimCategory[category_name]`), Source (`DimSource[source_name]`).
* **Headline Metric Cards:**
  - `Total Listings`: 2,252 collected business listings.
  - `Unique Businesses`: 2,252 distinct verified business IDs.
  - `Total Cities`: 12 Indian metropolitan areas.
  - `Total Categories`: 12 business sectors.
  - `Average Listings per City`: 187.67 listings/city.
* **Quality & Completeness Cards:**
  - `Completeness %`: 5.73% strict completeness rate (129 complete listings).
  - `Average Quality Score`: 63.4/100 mean audit score.
  - `Phone Availability %`: 7.28% published phone numbers (164 listings).
  - `Address Availability %`: 28.29% published address lines (637 listings).
  - `Duplicate Rate %`: 0.13% (3 exact duplicate records retained and flagged).
* **Charts & Breakdowns:**
  - `executive_city_distribution` (clusteredBarChart): Listings by city (Surat: 206 down to Delhi: 174).
  - `executive_category_distribution` (clusteredBarChart): Listings by category (Retail: 452, Food & Beverage: 447, down to Education: 2).
  - `executive_quality_bands` (barChart): Listings by quality band (Poor: 1,592, Fair: 531, Good: 129).
  - `executive_city_category_matrix` (matrix): City-by-category listing distribution grid.
  - `executive_report_context` (card): Data source and snapshot metadata.

### Page 2: Geographic Market Analysis (`Geographic_Market_Analysis`)
* **Slicers:** City, Category, Source.
* **Geographic KPIs:**
  - `City Coverage %`: Percentage of represented categories per city.
  - `Geographic Coverage`: Listings with validated coordinates (2,252 / 100%).
  - `City Concentration (HHI)`: Herfindahl-Hirschman Index = 0.0835 (balanced sample).
  - `Largest City / Smallest City`: Surat (206) / Delhi (174).
* **Visuals:**
  - `geography_city_distribution` (clusteredBarChart): City listing volume comparison.
  - `geography_city_ranking` (tableEx): Detailed city table with listing counts, share %, and rank.
  - `geography_city_category_heatmap` (matrix): City x category listing concentration matrix.
  - `geography_coordinates` (scatterChart): Latitude vs. longitude coordinates across all 12 cities with bounding box validation.
  - Attribution and Context Cards.

### Page 3: Data Quality Analysis (`Data_Quality_Analysis`)
* **Slicers:** City, Category, Validation Status, Duplicate Flag.
* **Audit KPIs:**
  - `Missing Published Phone`: 2,088 listings (92.72%).
  - `Missing Published Address`: 1,615 listings (71.71%).
  - `Complete Records`: 129 listings (5.73%).
  - `Exact Duplicates`: 3 records flagged and retained.
  - `Mean Audit Score`: 63.4/100.
* **Visuals:**
  - `quality_missingness_city` (clusteredBarChart): Missing phone and address rates across all 12 cities.
  - `quality_missingness_category` (clusteredBarChart): Completeness across categories.
  - `quality_score_bands` (columnChart): Quality band distribution across audited records.
  - `quality_review_detail` (tableEx): Granular record audit log with business name, city, category, flags, and score.

### Page 4: Market Opportunity Analysis (`Market_Opportunity_Analysis`)
* **Slicers:** City, Category, Opportunity Tier (High, Medium, Low).
* **Opportunity KPIs:**
  - `Total Pairs`: 144 potential city-category combinations.
  - `Covered Pairs`: 123 combinations with >= 1 listing (85.42% coverage).
  - `Evidence-Qualified Candidates`: Scoreable cells meeting city and category listing volume thresholds.
  - `High-Tier Opportunity Pairs`: 12 priority market gaps.
  - `Top Opportunity Score`: Highest candidate score (85.0/100).
* **Visuals:**
  - `opportunity_score_heatmap` (matrix): 12x12 Opportunity score grid by city and category.
  - `opportunity_ranked_pairs` (clusteredBarChart): Ranked opportunity scores for candidate market gaps.
  - `opportunity_score_components` (barChart): Breakdown of opportunity score into Underrepresentation (60%), Breadth Gap (25%), and Reliability (15%).
  - `opportunity_pair_detail` (tableEx): Detailed pair-level table with observed counts, national benchmarks, and opportunity scores.

---

## 5. Verification & Test Results

A unified test runner (`run_tests.py`) was executed to validate the entire codebase:

```
======================================================================
                    BusinessPulse Test Suite                          
======================================================================

--- Power BI Project (PBIP/PBIR/TMDL) Tests (tests.test_powerbi_project) ---
  [PASS] test_embedded_m_payload_round_trips_source_csv
  [PASS] test_generated_fact_listings_has_one_key_column
  [PASS] test_generated_pbip_contains_four_pages_and_required_visuals
  [PASS] test_generator_emits_required_pbir_report_definition
  [PASS] test_generator_preserves_nonempty_desktop_legacy_report
  [PASS] test_generator_preserves_unrecognized_tmdl_artifacts_on_refusal
  [PASS] test_generator_refuses_an_unmarked_output_directory
  [PASS] test_generator_removes_empty_desktop_legacy_report_on_regeneration
  [PASS] test_generator_removes_only_powerbi_auto_date_table_artifacts
  [PASS] test_offline_snapshot_is_consistent_and_keyed
  [PASS] test_snapshot_validator_rejects_duplicate_business_keys
  [PASS] test_snapshot_validator_rejects_inconsistent_complete_flag
  [PASS] test_static_validator_detects_incomplete_relationship_contract
  [PASS] test_static_validator_detects_stale_visual_files
  [PASS] test_static_validator_preserves_descriptions_on_supported_model_objects
  [PASS] test_static_validator_rejects_descriptions_on_unsupported_tmdl_objects
  [PASS] test_static_validator_rejects_empty_line_after_expression_document_comment
  [PASS] test_static_validator_rejects_invalid_first_line_tmdl_comment
  [PASS] test_static_validator_rejects_malformed_tmdl_declaration_header
  [PASS] test_static_validator_rejects_multiple_key_columns_in_a_table
  [PASS] test_static_validator_rejects_relationship_documentation_comments
  [PASS] test_static_validator_rejects_root_level_pbir_legacy
  [PASS] test_static_validator_rejects_unindented_table_objects
  [PASS] test_static_validator_rejects_unknown_relationship_property
  [PASS] test_static_validator_requires_all_tmdl_model_table_references
  [PASS] test_static_validator_requires_pbir_report_definition
Subtotal: 26 passed, 0 failed, 0 skipped

--- Power BI Desktop Star-Schema Tests (tests.test_powerbi_desktop_project) ---
  [PASS] test_generator_creates_four_report_pages_and_all_measures
  [PASS] test_generator_refuses_an_unmarked_output_directory
  [PASS] test_relationships_are_single_direction_and_preserve_issue_grain
  [PASS] test_six_snapshots_reconcile_and_have_unique_relationship_keys
  [PASS] test_snapshot_validator_rejects_duplicate_listing_business_keys
Subtotal: 5 passed, 0 failed, 0 skipped

--- Data Cleaning and Normalization Tests (tests.test_cleaning) ---
Subtotal: 24 passed, 0 failed, 0 skipped

--- Validation Rules Tests (tests.test_validation) ---
Subtotal: 10 passed, 0 failed, 0 skipped

--- Opportunity Score Calculation Tests (tests.test_opportunity) ---
Subtotal: 9 passed, 0 failed, 0 skipped

--- Project Assets and DDL Tests (tests.test_assets) ---
Subtotal: 15 passed, 0 failed, 0 skipped

======================================================================
FINAL TEST SUMMARY: 89 PASSED, 0 FAILED, 0 SKIPPED
======================================================================
```

---

## 6. How to Open in Power BI Desktop

### Option A: Primary Modern PBIR Project (Recommended)
1. Double-click `powerbi/generated/BusinessPulse.pbip`.
2. In the top notification banner, click **"Refresh now"** (or click the **Refresh** button on the Home ribbon).
3. Power BI Desktop executes the self-contained embedded M queries, loads all 2,252 rows, and renders all cards and charts populated with live data.

### Option B: Star-Schema Desktop Build
1. If your repository is located in a custom folder, run:
   ```bash
   python scripts/set_powerbi_data_folder.py "C:\path\to\BusinessPulse-master\powerbi\desktop_build\data\"
   ```
2. Double-click `powerbi/desktop_build/generated/BusinessPulse.pbip`.
3. Click **"Refresh now"** to load the 6 CSV star-schema tables and custom theme.

### Option C: Universal Legacy PBIP
1. For older Power BI Desktop versions (released prior to PBIR support):
2. Double-click `powerbi/legacy_pbip/BusinessPulse.pbip`.
3. Click **"Refresh now"**. The report renders using the classic PBIR-Legacy `report.json` definition with all 4 pages and 55 visuals pre-populated in the `sections` array.
