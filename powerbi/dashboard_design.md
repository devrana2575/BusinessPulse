# BusinessPulse — four-page dashboard design

## Status

**IMPLEMENTED AS A DESIGN SPECIFICATION — NOT RENDERED OR TESTED IN POWER BI
DESKTOP.** Build the pages in Desktop, then capture real screenshots. Do not
fabricate screenshots or claim visual QA that was not performed.

## Global design system

| Token | Value | Use |
|---|---|---|
| Canvas | `#F7F9FC` | Page background |
| Ink | `#14213D` | Titles and primary text |
| Muted ink | `#5B6577` | Secondary labels |
| Navy | `#1D3557` | Primary bars, header accent |
| Teal | `#2A9D8F` | Positive/coverage marks |
| Amber | `#E9A23B` | Warning/missing data |
| Coral | `#E76F51` | High opportunity/urgent |
| Green | `#2F855A` | Complete/valid |
| Border | `#DDE3EC` | Card and table borders |

- Font: **Segoe UI** (Windows default). Title 20–24 pt semibold; card values
  26–32 pt; body 10–11 pt.
- Page size: 16:9 (1280 × 720 px design canvas or the Desktop default 16:9).
- Outer margins: 24 px. Visual gutters: 12–16 px.
- Every page has a header band with the page title, a one-line question, a
  `Collection Snapshot Label` card, and the source attribution footer:
  `Source: OpenStreetMap contributors (ODbL 1.0) · Snapshot only · Not a census`.
- Use a left-hand navigation rail or four page tabs with short labels. Keep the
  same filter pane position on every page.
- Global slicers: `DimCity[city_name]`, `DimCategory[category_name]`, and
  `DimSource[source_name]` where listing-level visuals appear. A quality-band
  slicer is optional. Set city/category slicers to multi-select with a “Select
  all” state and keep the standard clear-selection control visible.
- Do not add a date-range slicer. One snapshot date makes a range control
  misleading. Use the snapshot card.

## Page 1 — Executive Overview

**Question:** What does the collected sample contain, and where is it complete
enough to act on?

**Top KPI row (five cards):**

| Card | Field / measure | Format |
|---|---|---|
| Listings collected | `[Total Listings]` | whole number |
| Cities represented | `[Total Cities]` | whole number |
| Categories represented | `[Total Categories]` | whole number |
| Data sources | `[Total Sources]` | whole number |
| Average listings per city | `[Average Listings per City]` | 1 decimal |

Add a smaller secondary row:
`[Completeness %]`, `[Average Quality Score]`, `[Phone Availability Percentage]`,
`[Address Availability Percentage]`, `[Duplicate Rate %]`. Label the quality
card “Mean audit score (0–100)” and do not imply it is a business-quality score.

**Visual 1 — City contribution (horizontal bar, sorted descending):**
- Axis: `DimCity[city_name]`
- Value: `[Total Listings]`
- Tooltip: `[City Contribution % (Selected)]`, `[Completeness %]`
- Data labels on. Keep 12 cities visible or use a scrollable bar; do not
  truncate without a “Top N + Other” note.

**Visual 2 — Category mix (donut or 100% stacked bar):**
- Legend: `DimCategory[category_name]`
- Value: `[Total Listings]`
- Tooltip: `[Category Contribution %]`, `[Completeness %]`
- Use a sorted legend by `display_order`, not alphabetical. A donut with 12
  slices is dense; a horizontal 100% stacked bar is preferred for readability.

**Visual 3 — Quality band split (stacked bar):**
- Axis: `FactDataQuality[quality_band]`
- Value: `[Total Listings]`
- Colors: High = green, Medium = amber, Low = coral.
- Add a text note: “Bands are derived from the documented 0–100 audit score.”

**Visual 4 — Collection coverage snapshot (matrix or table):**
- Rows: `DimCity[city_name]`
- Columns: `DimCategory[category_name]`
- Values: `[Total Listings]`
- Conditional formatting: blank/0 = light grey, low = amber, high = navy.
- Turn off totals that would imply a complete census. Add a subtitle:
  “Counts are collected POIs, not total businesses.”

**Footer:** `Snapshot 2026-11-02 · Source: OSM (ODbL 1.0) · Missing data is not imputed`.

## Page 2 — Geographic Coverage

**Question:** How does the sample distribute across the 12 cities, and where
are category gaps concentrated?

**Map visual (filled or bubble map):**
- Location: `FactListings[latitude]`, `FactListings[longitude]`
- Size: `[Total Listings]` (bubble map) or use city points from `DimCity`.
- Legend: `DimCategory[category_name]` optional; too many points may overload.
- Tooltip: business name, city, category, phone availability flag (not the
  actual phone by default), quality band.
- Add a visible note: “Map points are public OSM POIs; clustering can hide
  overlapping businesses.”

**City ranking table:**
- `DimCity[city_name]`, `DimCity[state_name]`, `[Total Listings]`,
  `[City Contribution % (Selected)]`, `[City Rank]`, `[Completeness %]`,
  `[Average Quality Score]`.
- Sort by `[Total Listings]` descending. Add data bars.

**City × category heat map:**
- Rows: city; columns: category; values: `[Total Listings]`.
- Conditional formatting by value. Add a tooltip with
  `[Category Share in City %]`.
- This is the visual that makes “low count” visible without claiming demand.

**Top/bottom city cards:**
- `Top city by listings` using a card with a measure or a filtered table.
- `Lowest city by listings` (only cities with at least one listing).
- Do not call the lowest city “worst market”; call it “smallest collected
  sample”.

**Interaction:** Selecting a city on the map filters the table and heat map.
Add city, category and source slicers; include the standard slicer clear
control. The current source dimension has one member, so its slicer is
descriptive and cannot distinguish sources. Test the interactions manually
and capture one screenshot.

## Page 3 — Data Quality & Completeness

**Question:** Which fields are missing, where, and how much does that limit
the analysis?

**KPI row:**
`[Total Listings]`, `[Phone Availability Percentage]`,
`[Address Availability Percentage]`, `[Duplicate Rate %]`,
`[Complete Records Percentage]`, `[Average Quality Score]`.

**Visual 1 — Missing fields by city (clustered bar):**
- Axis: `DimCity[city_name]`
- Values: `[Missing Phone %]`, `[Missing Address %]`
- Use a common 0–100% axis, data labels, and a legend.
- Add a reference line at the overall `[Missing Phone %]` only if it does not
  clutter; label it clearly.

**Visual 2 — Quality band distribution (stacked column):**
- Axis: `FactDataQuality[quality_band]`
- Value: `[Total Listings]`
- Add `[Complete Listings]` as a tooltip and the documented scoring note.

**Visual 3 — Missingness by category (matrix):**
- Rows: `DimCategory[category_name]`
- Values: `[Missing Phone %]`, `[Missing Address %]`, `[Completeness %]`
- Conditional formatting: high missing = coral, low = green.
- Add a subtitle: “Missing means absent in the public source, not necessarily
  absent in reality.”

**Visual 4 — Review queue table:**
- Columns: `business_name`, `city_name`, `category_name`, `validation_status`,
  `quality_score`, `missing_phone`, `missing_address`, `duplicate_flag`.
- Filter: `validation_status = "needs_review"` by default; give the viewer a
  way to clear it.
- Hide phone/address by default in the table; if shown, they are public business
  contact fields, not customer data.
- Add a note: “Exact duplicates are flagged and retained for audit; they are not
  deleted.”

**Visual 5 — Source completeness (single card/table):**
- `DimSource[source_name]`, `[Total Listings]`, `[Source Completeness %]`.
- With one source this is descriptive only; do not imply a source comparison.
- Add the source slicer where listing-level visuals are shown. The aggregated
  city × category opportunity view has no source key, so source selections do
  not filter its scores; state this limitation in the report.

## Page 4 — Market Opportunity

**Question:** Which city × category combinations are most underrepresented in
the collected sample, given data reliability?

**Methodology banner (text box):**
> Opportunity score v1.0 = 100 × (0.60 × underrepresentation + 0.25 × city
> breadth gap + 0.15 × completeness). It ranks **underrepresentation in
> collected listings**, not demand, revenue, or competition. High scores are
> research candidates, not investment advice.

**KPI row:**
- `[Category Coverage %]` — covered city × category pairs / universe.
- `[High Opportunity Gaps]` — candidate pairs in the High tier.
- `[Candidate City-Category Pairs]`.
- `[Top Opportunity Score]`.
- Add a card for `[City-Category Combinations]` labelled “Universe pairs”.

**Visual 1 — Opportunity ranking (horizontal bar, top 15):**
- Axis: `DimCity[city_name] & " | " & DimCategory[category_name]` (create a
  concatenated column in Power Query or a visual-level field; do not use a
  calculated table).
- Value: `[Opportunity Score]`.
- Color by `FactCityCategoryCoverage[opportunity_tier]` (High = coral, Medium =
  amber, Low = teal, Insufficient = grey).
- Filter `is_candidate = 1` and top 15 by score.
- Tooltip: `listing_count`, `relative_representation`,
  `underrepresentation_points`, `breadth_points`, `reliability_points`.

**Visual 2 — Coverage heat map:**
- Rows: city; columns: category; values: `[Opportunity Score]` (not count).
- Conditional formatting: coral for high, teal for low.
- Tooltip: `listing_count`, `coverage_status`, `is_candidate`.
- Include a second matrix with `[Total Listings]` for context; do not let the
  score matrix replace the raw counts.

**Visual 3 — Score decomposition (stacked bar):**
- Axis: top candidate pairs.
- Values: `[Underrepresentation Points]`, `[Breadth Points]`,
  `[Reliability Points]`.
- Use a 100-point axis. Explain that points are additive by construction.

**Visual 4 — Candidate detail table:**
- `city_name`, `category_name`, `listing_count`, `relative_representation`,
  `opportunity_score`, `opportunity_tier`, `coverage_status`,
  `methodology_note`.
- Sort by score descending. Add conditional formatting on tier.
- Do not include a “recommended action” that claims market demand; the only
  valid action is “investigate further”.

**Interactions and validation:**
- Selecting a city on Page 2 should filter the opportunity page if the reader
  uses the shared city slicer. Verify that the coverage universe and the
  fact-table counts remain consistent under the selection.
- `Opportunity Score` must not be summed. If a table shows a total, hide it or
  use an explicit “average” label.
- Record the page’s actual counts in the manual checklist after refresh.

## Accessibility and UX checks (manual)

- Every visual has a title and, where needed, a subtitle with units/definitions.
- Do not rely on color alone; use labels or icons for High/Medium/Low.
- Alt text for the map, charts and tables describes the message, not just the
  visual type.
- Tab order follows the header → KPIs → main chart → detail.
- Contrast of muted text on the canvas meets WCAG AA for normal text; verify in
  Desktop’s accessibility checker.
- The report is readable at 100% zoom and on a 1366 × 768 display.
- No page claims a complete census, demand, revenue or causal effect.

## What remains pending

- Creating the `.pbix`.
- Applying theme JSON, fonts, and page layout in Desktop.
- Testing measures and relationships.
- Capturing screenshots and recording actual reconciliation values.
- Exporting a PDF or publishing to Power BI Service (optional, not required).
