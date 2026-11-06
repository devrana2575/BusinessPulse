# Dashboard screenshots — PENDING MANUAL ACTION

No Power BI screenshots are stored here. A PBIP project exists, but it has not
yet been opened, refreshed, or rendered in Power BI Desktop.
**Do not substitute generated images, mockups, or screenshots from another project.**

## What to capture after validating the PBIP and saving the PBIX

Use a 16:9 canvas at 100% zoom, hide the Power BI authoring panes, and capture
the full page (not a cropped visual). Name files exactly:

1. `01_executive_overview.png` — KPI row, city bars, category mix, quality band.
2. `02_geographic_market_analysis.png` — coordinate scatter, city ranking,
   city × category heat map.
3. `03_data_quality.png` — missing-field KPIs, city bars, quality bands,
   review queue.
4. `04_market_opportunity.png` — methodology banner, top gaps, coverage heat
   map, candidate table.
5. `05_filter_interaction.png` — one city selected, showing the geo page and
   opportunity page responding; include the visible slicer state.

Optional:
`06_tooltip_opportunity.png` — the score decomposition tooltip.
`07_mobile_layout.png` — only if a mobile layout is deliberately built.

## Metadata to record next to each screenshot

- PBIP/PBIX commit/version and snapshot date.
- Report page name and active filters.
- `Total Listings`, `Completeness %`, `Opportunity Score` shown on screen.
- Desktop version and screen resolution.
- Whether the manual reconciliation table in `powerbi/README.md` passed.

Do not claim a screenshot verifies data quality, source completeness, or
market demand. A screenshot only shows the rendered report under the stated
filters.

## Existing figures are not dashboard screenshots

`data/reports/figures/*.png` are Matplotlib EDA outputs. They are valid
evidence for the Python EDA, not for the Power BI report. If they are included in
the README, label them as EDA figures.
