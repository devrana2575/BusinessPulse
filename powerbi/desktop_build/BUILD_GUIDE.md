# BusinessPulse - Power BI Desktop build guide

The six CSV snapshots, Power Query definitions, DAX measures, theme and report specification are under this directory. The automated generator is `scripts/build_powerbi_desktop_project.py`; it emits `generated/BusinessPulse.pbip`, a six-table semantic model, 50 measures, and four PBIR page definitions containing 59 visuals.

Generate and run the offline checks from the repository root:

```powershell
python scripts/build_powerbi_desktop_project.py
python scripts/build_powerbi_desktop_project.py --validate-only
python -m pytest tests/test_powerbi_desktop_project.py tests/test_powerbi_project.py -q
```

The project is also opened in the installed Power BI Desktop. Its local semantic-model engine loaded the CSV tables and evaluated representative measures. However, Desktop displayed a blank report canvas instead of the generated PBIR pages. The install's Preview features list did not expose a PBIR toggle. Therefore the report visuals, interactions, PBIX export, and screenshots remain unverified; see `VALIDATION_REPORT.md`. Do not treat generated JSON or passing offline checks as proof that Desktop rendered the report.

Use the automated PBIP as the starting point. The manual steps below remain as a fallback if Desktop continues not to render its report definition.

## Generated semantic model

The generated model uses the six CSV snapshots in `data/`. The source columns and Power Query types are defined in `powerquery/BusinessPulse.m`; measures are defined in `measures.dax` and documented in `MEASURES.md`.

| Table | Role and business key |
|---|---|
| `DimCity` | City dimension; `city_id` |
| `DimCategory` | Category dimension; `category_id` |
| `DimSource` | Listing-source dimension; `source_id` |
| `FactListings` | Listing fact; `business_id` |
| `FactQualityIssues` | Quality-issue fact; `issue_id`, with `business_id` linking to its listing |
| `FactCityCategoryCoverage` | Complete city-category coverage grid; one row per `city_id` + `category_id` pair |
| `_Measures` | DAX measure host table; not related to the other tables |

There are six active, single-direction relationships: each of `FactListings.city_id`, `FactListings.category_id`, and `FactListings.source_id` is many-to-one to its matching dimension key; `FactQualityIssues.business_id` is many-to-one to `FactListings.business_id`; and `FactCityCategoryCoverage.city_id` and `.category_id` are many-to-one to their matching dimensions. This preserves the source business keys and avoids duplicate dimension keys or bidirectional filter paths.

The generator defines 50 measures from the build kit and a calculated `Pair Label` column for the city-category grain. Opportunity and quality calculations retain the definitions in `measures.dax`; see `MEASURES.md` for the individual formulas and intended meaning.

---

## Part A - Model setup

**1. Refresh the data files (optional).** From the project root: `python scripts/export_powerbi_star_schema.py`. It reads only existing repo files, prints 12 reconciliation checks, and rewrites `powerbi/desktop_build/data/*.csv`.

**2. Create the parameter.** Home > Transform data > Manage Parameters > New. Name `DataFolder`, Type Text, Required, value = full path to `...\powerbi\desktop_build\data\` **ending with a backslash**.

**3. Load the 6 tables.** For each block in `powerquery/BusinessPulse.m`: New Source > Blank Query > Advanced Editor > paste > Done > rename the query to the name in the comment (`DimCity`, `DimCategory`, `DimSource`, `FactListings`, `FactQualityIssues`, `FactCityCategoryCoverage`). Close & Apply.
Check in Power Query: no `Error` cells; `FactListings` = 2,252 rows; `FactQualityIssues` = 3,762; `FactCityCategoryCoverage` = 144.

**4. Relationships (Model view).** Create exactly these six; all Many-to-one (or One-to-many), **Single** direction, active:

| One side | Many side |
|---|---|
| `DimCity[city_id]` | `FactListings[city_id]` |
| `DimCategory[category_id]` | `FactListings[category_id]` |
| `DimSource[source_id]` | `FactListings[source_id]` |
| `DimCity[city_id]` | `FactCityCategoryCoverage[city_id]` |
| `DimCategory[category_id]` | `FactCityCategoryCoverage[category_id]` |
| `FactListings[business_id]` | `FactQualityIssues[business_id]` |

Turn off *Auto-detect* if Desktop adds extras; delete any relationship not in this table. `FactListings` and `FactCityCategoryCoverage` share `DimCity` and `DimCategory`; `FactQualityIssues` relates to `FactListings` by `business_id`. Keep all six relationships active and single-direction to avoid ambiguous filter paths. `DimSource` filters listings only (the opportunity facts have no source key), so a Source slicer never affects Page 4.

**5. Hide technical columns** (right-click > Hide in report view): every `*_id` key column (including `business_id` and `issue_id`), `quality_band_sort`, `opportunity_tier_sort` and `display_order`. Also hide `bbox_*`, `city_total` and `category_total` (they are not additive). Leave `source_record_url` visible for the duplicates table.

**6. Sorting.** `DimCategory[category_name]` sort by `display_order`. `FactListings[quality_band]` sort by `quality_band_sort`. `FactCityCategoryCoverage[opportunity_tier]` sort by `opportunity_tier_sort`.

**7. Data categories (Column tools).** `FactListings[latitude]` = Latitude, `[longitude]` = Longitude; `DimCity[centroid_latitude]/[centroid_longitude]` likewise; `FactListings[source_record_url]` = Web URL.

**8. Measures table.** Home > Enter data > one blank column > name table `_Measures` > Load; delete the blank column. Paste each measure from `measures.dax` (New measure). Set the format listed in `MEASURES.md`. Display folders: use the four folder names in the file.
Add the calculated column on `FactCityCategoryCoverage`:
```dax
Pair Label = RELATED ( DimCity[city_name] ) & " | " & RELATED ( DimCategory[category_name] )
```

**9. Theme.** View > Themes > Browse for themes > `BusinessPulse_theme.json`. Palette: navy `#1F3A5F` (primary), teal `#2A9D8F`, amber `#E9A23B`, coral `#D1495B` (emphasis only), grey `#6B7280`.

**10. Canvas.** Format page > Canvas settings: 16:9 (1280 x 720). Fonts: Segoe UI throughout. Card callout 28 pt, titles 12 pt semi-bold, labels 10 pt.

**11. Common grid (all pages).** Margin 20 px.
- Title band: y 0-52 (page title left, subtitle right: "Source: (c) OpenStreetMap contributors (ODbL) - snapshot [Snapshot Date]").
- Slicer strip: y 60-96, three dropdown slicers 220 px wide at x 20 / 250 / 480.
- KPI cards: y 108-178, 6 cards, 196 px wide, 8 px gap.
- Content: y 190-700.
- Footer note: 10 pt grey text, y 696-716.

Slicers: **dropdown** style, single-select off, "Select all" on. Sync City and Category slicers across pages (View > Sync slicers; tick all four pages in both columns).

---

## Part B - Pages

Interaction rule for every page: select the bar visuals, then Format > Edit interactions so **cards and slicers are unaffected by cross-highlighting where it would mislead** (noted per page). Default cross-filtering is fine otherwise.

### Page 1 - Executive Overview

Question: *What does the collected business landscape look like at a glance?*

| # | Visual | Fields | Notes |
|---|---|---|---|
| S1-S3 | Slicers | `DimCity[city_name]`, `DimCategory[category_name]`, `DimSource[source_name]` | Source has one value; it exists to show attribution and filter correctly if sources are added. There is no date slicer: the data has a single collection date. |
| K1 | Card | `[Total Listings]` | Title "Listings collected" |
| K2 | Card | `[Total Cities]` | |
| K3 | Card | `[Total Categories]` | |
| K4 | Card | `[Avg Listings per City]` | Subtitle (card "Category label" off; add small text box): "Capped collection - not market size" |
| K5 | Card | `[Pair Coverage %]` | Title "City-category coverage" (123 of 144) |
| K6 | Card | `[Avg Quality Score]` | Title "Avg data quality score (0-100)" |
| V1 | Clustered bar | Y `DimCategory[category_name]`; X `[Total Listings]`; Tooltips `[Listing Share %]`, `[City Coverage %]`, `[Avg Quality Score]` | Sort by X descending. Data labels on. Title "Listings by category". Doubles as the category-distribution view (labels show share via tooltip), so no second redundant chart. |
| V2 | Clustered bar | Y `DimCity[city_name]`; X `[Total Listings]`; Tooltips `[Listing Share %]`, `[City Rank]`, `[Avg Quality Score]` | Sort descending. Title "Listings by city (ranked)". This is the top-cities view; true density per km2 or per capita cannot be computed because no area/population exists in the data. |
| T1 | Text box | static text from README "Executive interpretation" | y 190-700 right column, 300 px wide |

Layout: V1 x 20-470, V2 x 480-930, T1 x 940-1260, all y 190-690.
Conditional formatting: on V2, Data colors > fx > Format by *Rules* using `[City Rank]`: rank <= 3 = navy `#1F3A5F`, otherwise light blue `#8FB8DE`.
Edit interactions: K1-K6 respond to slicers only (V1/V2 selection may filter them - leave on; it is correct behaviour here).

### Page 2 - Geographic Market Analysis

Question: *Where are listings, and how evenly are categories spread across cities?*

| # | Visual | Fields | Notes |
|---|---|---|---|
| S1-S2 | Slicers | City, Category | |
| K1 | Card | `[Largest City Listings]` | Title "Largest city (listings)" |
| K2 | Card | `[Smallest City Listings]` | |
| K3 | Card | `[Top City Share %]` | |
| K4 | Card | `[City HHI]` | Subtitle "0.0833 = perfectly even" |
| K5 | Card | `[Uncovered Pairs]` | "City-category cells with no listing" |
| M1 | **Map** (bubble) | Latitude `FactListings[latitude]`, Longitude `FactListings[longitude]`; Legend `DimCategory[category_name]` *or* none; Tooltips `FactListings[business_name]`, `DimCity[city_name]` | 2,252 points. Needs Map visuals enabled (File > Options > Security > Map and filled map visuals). **Fallback if disabled/blank:** Scatter chart, X `longitude` (Don't summarise), Y `latitude` (Don't summarise), Details `business_id`. Verified at build time: all coordinates fall inside India and inside each city's collection box (0 outside). |
| V1 | Clustered bar | Y city; X `[Total Listings]`; Visual filter Top N = 5 by `[Total Listings]` | "Top 5 cities by listings" |
| V2 | Clustered bar | Y city; X `[Total Listings]`; Visual filter Top N = **Bottom** 5 by `[Total Listings]` | "Bottom 5 cities by listings" |
| V3 | 100% stacked bar | Y city; X `[Total Listings]`; Legend category | "Category mix by city". Use 12 legend colours sparingly: this is the only multi-colour chart; leave default theme cycle. |
| V4 | Clustered bar | Y city; X `[Total Categories]`; Tooltips `[Category Coverage %]`, `[Missing Categories]` | "Categories present per city (of 12)". Axis max fixed at 12. |

Layout: M1 x 20-620 y 190-690; V1 x 630-940 y 190-330; V2 x 950-1260 y 190-330; V3 x 630-1260 y 340-520; V4 x 630-1260 y 530-690. Cards on y 108-178 (5 cards x 240 px).
**Important footnote (text box, y 696):** "Counts are capped per city/query group during collection, so city ranking reflects collection design, not market size."
Edit interactions: M1 should be *filtered* by V1/V2/V4 clicks (shows that city's points) and should not filter the cards.

### Page 3 - Data Quality Analysis

Question: *How reliable and complete is the dataset, and where are the weak spots?*

| # | Visual | Fields | Notes |
|---|---|---|---|
| S1-S3 | Slicers | City, Category, `FactListings[validation_status]` | |
| K1 | Card | `[Total Listings]` | Title "Records audited" |
| K2 | Card | `[Duplicate Count]` | |
| K3 | Card | `[Missing Phone %]` | |
| K4 | Card | `[Missing Address %]` | |
| K5 | Card | `[Invalid Coordinate Count]` | Shows 0 - a genuine result |
| K6 | Card | `[Missing Business Name Count]` | Shows 0 |
| K7 | Card | `[Avg Quality Score]` | |
| V1 | Clustered bar | Y `FactQualityIssues[issue_type]`; X `[Quality Issue Rows]` | "Audit warnings by type" (missing_phone, missing_address, invalid_address, invalid_phone_format) |
| V2 | Column | X `FactListings[quality_band]`; Y `[Total Listings]` | "Quality-score bands" (sorted High, Medium, Low) |
| V3 | Clustered bar | Y city; X `[Missing Phone %]`, `[Missing Address %]` | "Missing contact data by city". Axis 0-100% fixed. |
| V4 | Clustered bar | Y category; X `[Missing Phone %]`, `[Missing Address %]` | "Missing contact data by category". Axis 0-100% fixed. |
| V5 | Bar | Y city; X `[Avg Quality Score]` | "Avg quality score by city". Conditional colour: rules <60 coral, 60-<80 amber, >=80 teal (project bands). Axis 0-100. |
| T1 | Table | `FactListings[business_name]`, `DimCity[city_name]`, `DimCategory[category_name]`, `FactListings[source_record_url]`; visual-level filter `FactListings[duplicate_flag]` is 1 | "Exact duplicates flagged (retained)". 3 rows. |
| X1 | Text box | Analytical-impact text (README) | |

Not shown, deliberately: "missing categories" and "invalid coordinates" have zero occurrences, so no chart; the cards show 0. No quality metric is invented.
Edit interactions: turn V3/V4/V5 selections to *filter* K cards; fine.

### Page 4 - Market Opportunity Analysis

Question: *Which city-category cells are thinly represented in the collected data and merit review?*

| # | Visual | Fields | Notes |
|---|---|---|---|
| S1-S3 | Slicers | City, Category, `FactCityCategoryCoverage[opportunity_tier]` | |
| K1 | Card | `[Covered Pairs]` | "Cells with listings (of 144)" |
| K2 | Card | `[High Opportunity Pairs]` | |
| K3 | Card | `[Medium Opportunity Pairs]` | |
| K4 | Card | `[Highest Opportunity Score]` | |
| K5 | Card | `[Avg Opportunity Score]` | Subtitle "descriptive, candidate pairs only" |
| MX1 | **Matrix** | Rows `DimCity[city_name]`; Columns `DimCategory[category_name]`; Values `[Pair Listings]` | "City x category coverage (listing count)". Conditional background (fx > Rules): value = 0 coral `#D1495B` with white text; 1-4 amber `#E9A23B`; >=5 none. Row/column totals on. Column headers wrapped. |
| T1 | Table | `[Pair Label]`, `[Pair Listings]`, `[Relative Representation (Pair)]`, `[Opportunity Score (Pair)]`, `FactCityCategoryCoverage[opportunity_tier]`; visual filter Top N = 15 by `[Opportunity Score (Pair)]` | "Opportunity ranking (candidate pairs)". Sort by score desc. Data bar on score. |
| V1 | Stacked bar | Y `[Pair Label]` (Top N 10 by `[Opportunity Score (Pair)]`); X `[Avg Underrepresentation Points]`, `[Avg Breadth Points]`, `[Avg Reliability Points]` | "Score breakdown (top 10)". Legend = the three components. Components sum to the score. |
| V2 | Bar | Y city; X `[Opportunity Count]` | "High + Medium pairs by city" |
| V3 | Bar | Y category; X `[Opportunity Count]` | "High + Medium pairs by category" |
| X1 | Text box | Method + caveat (below) | |

Required caveat (visible on the page): *"Opportunity score = 100 x (0.60 x underrepresentation + 0.25 x city category-breadth gap + 0.15 x city completeness), methodology v1.0 from the repository. It flags cells that are thin in this capped OpenStreetMap sample. It is a review signal, not evidence of demand, revenue or competition. 12 Education & Training cells are 'Insufficient evidence' (only 2 national listings) and are left unscored."*

Layout: MX1 x 20-700 y 190-520; T1 x 710-1260 y 190-410; V1 x 710-1260 y 420-690; V2 x 20-360 y 530-690; V3 x 370-700 y 530-690.

---

## Part C - Interaction & quality checks (do before saving)

1. Select **Hyderabad** on the City slicer: Page 1 K2 = 1, K3 = 9; Page 2 K5 = 3; Page 4 K1 = 9.
2. Clear it; select **Retail**: Page 1 K1 = 452.
3. Click a bar on any chart: other visuals cross-filter without blanks or errors.
4. No visual shows "Can't display" or a yellow triangle; no unexpected `(Blank)` row on any axis.
5. `[Pair Listings]` equals `[Total Listings]` under every slicer combination you try.
6. Page order: Executive Overview, Geographic Market Analysis, Data Quality Analysis, Market Opportunity Analysis. Rename tabs.
7. View > Page view: Fit to page; Selection pane: give every visual a meaningful name; Alt text on charts.

## Part D - Deliver

1. After confirming all four pages render and their visuals work, save as `BusinessPulse.pbix` in `powerbi/`.
2. Capture screenshots of each page at 100% zoom, with **no slicer selection** applied. Save as `powerbi/screenshots/01_executive_overview.png` ... `04_market_opportunity.png`, plus `05_model_view.png`.
3. Record only observed Desktop results in `VALIDATION_REPORT.md`.
4. Do not present the current PBIP as a verified visual report or create a PBIX/screenshots from its blank canvas. Do not commit `.env`.
