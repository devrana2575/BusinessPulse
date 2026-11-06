# BusinessPulse — Business Intelligence & Analytics Project

A portfolio-ready **Data Analyst / Business Intelligence** project built from a real OpenStreetMap business-POI extract across 12 Indian cities. It covers the complete analytical lifecycle: polite Overpass API collection, Python cleaning and validation, MySQL schema design, 35 analytical SQL queries, EDA, transparent opportunity scoring, automated testing, and a fully restored, four-page Power BI dashboard delivered in both modern PBIR and universal legacy PBIP formats.

> **Scope:** This is an auditable **snapshot of collected public map listings**, not a business census or speculative financial projection. Contact missingness in OSM is transparently measured and audited rather than invented or artificially enriched. See [`docs/limitations.md`](docs/limitations.md).

---

## At a Glance

| Item | Result | Verification |
|---|---|---|
| Snapshot Date | **2026-11-02** | OpenStreetMap Overpass API (ODbL 1.0) |
| Geography | **12 Indian Cities** (Ahmedabad, Bengaluru, Chandigarh, Chennai, Delhi, Hyderabad, Indore, Jaipur, Kolkata, Mumbai, Pune, Surat) | Bounded latitude/longitude coordinates |
| Raw / Cleaned Records | **2,252 / 2,252** listings | 100% verified key uniqueness on `business_id` |
| Categories | **12 Sectors** | Retail, Food & Beverage, Healthcare, etc. |
| Missing Contact Audit | Phone: **92.72%** (2,088 missing); Address: **71.71%** (1,615 missing) | Documented and auditable quality gap |
| Strict Completeness | **5.73%** (129 complete listings) | Phone + address valid + non-duplicate |
| Exact Duplicates | **3 flagged & retained** | Retained for audit fidelity, not deleted |
| Market Opportunity | **123/144** covered pairs (**85.42%**) | 12 High-tier and 5 Medium-tier market gaps |
| Analytical SQL | **35 / 35** queries documented & tested | `database/analytical_queries.sql` |
| Automated Test Suite | **90 / 90 tests PASSED** | Unit, cleaning, validation, opportunity, and Power BI tests (`python run_tests.py`) |
| Power BI Desktop | **REPAIRED & FULLY RESTORED** | 4 pages, 55–59 visuals, PBIR & legacy PBIP formats |

---

## Power BI Dashboard Restoration & Architecture

The report definitions and PBIP schemas have been repaired from the ground up, resolving previous canvas blankness and `"The report has no pages"` error dialogs.

### Restored Report Pages
1. **Executive Overview** (`Executive_Overview`):
   - **Slicers:** City, Category, Source.
   - **Headline Metrics:** Total Listings (2,252), Unique Businesses (2,252), Total Cities (12), Total Categories (12), Avg Listings per City (187.67).
   - **Quality Benchmarks:** Completeness % (5.73%), Average Quality Score (63.4/100), Phone Availability % (7.28%), Address Availability % (28.29%), Duplicate Rate % (0.13%).
   - **Visuals:** Listings by City (ranked bar chart), Listings by Category (bar chart), Record Quality Bands (stacked bar chart), City-Category Listing Count Matrix.
2. **Geographic Market Analysis** (`Geographic_Market_Analysis`):
   - **Geographic Metrics:** City Coverage %, Geographic Bounding Box Validity, City Concentration HHI (0.0835), Top City Share, Largest/Smallest City.
   - **Visuals:** City Distribution bar chart, City Ranking & Listing Share table, City-Category Coverage Heatmap matrix, Geographic Coordinates scatter plot (latitude/longitude coordinates with zero out-of-bounds records).
3. **Data Quality Analysis** (`Data_Quality_Analysis`):
   - **Audit Metrics:** Missing Phone (2,088), Missing Address (1,615), Complete Records (129), Retained Duplicates (3), Mean Quality Score (63.4/100).
   - **Visuals:** Missing Contact Fields by City, Completeness by Category, Quality Score Band Distribution, Detailed Record Audit Review table.
4. **Market Opportunity Analysis** (`Market_Opportunity_Analysis`):
   - **Opportunity Metrics:** Total Pairs (144), Covered Pairs (123), Qualified Candidates, High-Tier Opportunities (12), Top Opportunity Score (85.0/100).
   - **Visuals:** Opportunity Score Heatmap matrix, Ranked Candidate Pairs bar chart, Score Component Breakdown (Underrepresentation 60%, Breadth Gap 25%, Reliability 15%), Detailed Opportunity Pair table.

---

## Opening the Project in Power BI Desktop

Three fully functional project options are provided to support every Power BI Desktop environment:

### Option 1: Primary Modern PBIR Project (Recommended)
* **File:** `powerbi/generated/BusinessPulse.pbip`
* **Format:** Modern Power BI Enhanced Report Format (PBIR) with TMDL semantic model.
* **Data Mode:** Embedded offline snapshot (100% self-contained via compressed M queries).
* **Launch:** Double-click `powerbi/generated/BusinessPulse.pbip`. Opens immediately in Power BI Desktop (September 2026 or newer) with all 4 pages, visuals, measures, and relationships loaded without external dependencies.

### Option 2: Star-Schema Desktop Build
* **File:** `powerbi/desktop_build/generated/BusinessPulse.pbip`
* **Format:** Star-schema architecture with six source tables, `_Measures` table, and custom theme.
* **Setup:** If running from a custom location, configure your data folder once:
  ```bash
  python scripts/set_powerbi_data_folder.py "C:\path\to\BusinessPulse-master\powerbi\desktop_build\data\"
  ```
* **Launch:** Double-click `powerbi/desktop_build/generated/BusinessPulse.pbip`.

### Option 3: Universal Legacy PBIP
* **File:** `powerbi/legacy_pbip/BusinessPulse.pbip`
* **Format:** Classic PBIR-Legacy format with all 4 pages pre-populated in `report.json`'s `sections` array.
* **Compatibility:** Guaranteed to open in older Power BI Desktop versions where PBIR preview features are not enabled.

---

## Running the Automated Test Suite

Run all unit tests, data pipeline tests, and Power BI project validation checks offline with the unified runner:

```bash
python run_tests.py
```

To validate the Power BI project definitions directly:

```bash
python scripts/build_powerbi_project.py --validate-only
python scripts/build_powerbi_desktop_project.py --validate-only
```

---

## Project Structure

```
BusinessPulse-master/
├── README.md                                  # Project overview and instructions
├── VALIDATION_REPORT.md                       # Comprehensive repair and validation audit
├── run_tests.py                               # Unified test runner
├── pytest.ini                                 # Pytest configuration
├── requirements.txt                           # Python dependencies
├── analytics/                                 # Data collection, cleaning, EDA, validation
│   ├── business_insights/opportunity_analysis.py
│   ├── cleaning/cleaning.py
│   └── validation/validation.py
├── data/
│   ├── processed/cleaned_business_listings.csv
│   ├── raw/business_listings_raw.csv
│   └── reports/market_opportunities.csv
├── database/                                  # MySQL schemas, views, analytical queries
│   ├── schema.sql
│   ├── views.sql
│   └── analytical_queries.sql
├── powerbi/
│   ├── dax_measures.dax                       # 72 documented DAX measures
│   ├── dashboard_design.md                    # Visual layout and specification
│   ├── generated/                             # Primary repaired modern PBIR project
│   │   ├── BusinessPulse.pbip
│   │   ├── BusinessPulse.Report/
│   │   └── BusinessPulse.SemanticModel/
│   ├── desktop_build/                         # Star-schema project kit & CSVs
│   │   ├── generated/BusinessPulse.pbip
│   │   ├── data/*.csv                         # Star-schema tables
│   │   └── BusinessPulse_theme.json
│   └── legacy_pbip/                           # Backwards-compatible legacy PBIP project
│       ├── BusinessPulse.pbip
│       └── BusinessPulse.Report/report.json
├── scripts/
│   ├── build_powerbi_project.py               # Modern PBIR generator
│   ├── build_powerbi_desktop_project.py       # Desktop star-schema generator
│   ├── build_legacy_pbip.py                   # Legacy PBIP generator
│   └── set_powerbi_data_folder.py             # DataFolder configuration helper
└── tests/
    ├── test_powerbi_project.py                # PBIP/PBIR/TMDL validation tests
    ├── test_powerbi_desktop_project.py        # Desktop star-schema tests
    ├── test_cleaning.py                       # Data cleaning tests
    └── test_validation.py                     # Validation rules tests
```

---

## License & Attribution

* **Data Source:** OpenStreetMap contributors via Overpass API, collected November 2, 2026.
* **License:** Open Database License (ODbL) 1.0 — [opendatacommons.org/licenses/odbl/1-0/](https://opendatacommons.org/licenses/odbl/1-0/).
