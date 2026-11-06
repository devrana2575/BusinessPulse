# Demo script (5–7 minutes)

This is a truthful walkthrough of what exists. The numbers below come from the
final generated reports. Do not claim Power BI was rendered; the PBIX/screenshots
are pending manual action.

## 0. Opening (30 seconds)

> BusinessPulse is a local data-analyst portfolio project built on a real
> OpenStreetMap extract of business POIs across 12 Indian cities, collected
> through the Overpass API on 2026-11-02. The stack is Python, Pandas, MySQL,
> SQL and a specified Power BI model. The goal is not to claim a business
> census; it is to show a full, auditable pipeline from raw public data to
> decision-ready analysis, including honest data-quality limits.

Show the repository tree and the status table in the README.

## 1. Source and provenance (45 seconds)

- Open `docs/data_sources.md`: OSM/Overpass, ODbL, 12 bounding boxes, five
  capped query groups, retry/cache design.
- Open `data/raw/collection_manifest.json`: query text, endpoint, statuses,
  element counts, cache paths.
- Point out one raw row in `data/raw/business_listings_raw.csv`: `source_record_id`,
  `source_record_url`, raw phone, OSM tags. Missing phone is blank, not invented.

## 2. Cleaning and quality (90 seconds)

Run or show:

```powershell
python scripts/businesspulse.py clean --confirm-regenerate
python scripts/businesspulse.py validate
```

Show `data/reports/data_quality_summary.csv`:

- 2,252 raw and cleaned listings;
- 92.7% missing phone, 71.7% missing address;
- 5.7% complete under the strict rule;
- exact duplicates flagged and retained, not silently deleted.

Explain the quality score penalties and why a missing public phone is not a
reason to fabricate a number. Show one rejected row and its documented reason.

## 3. Database and SQL (90 seconds)

Show the MySQL schema and views:

```powershell
# Only for an explicitly approved new database/account.
python scripts/businesspulse.py setup --database businesspulse --confirm-database-create --confirm-account-provisioning
python scripts/businesspulse.py import --database businesspulse --confirm-target-empty
```

Do not use `--reset` or `--replace-data` against an existing database during
the demo. Those options are destructive.

Open `database/views.sql` and `database/analytical_queries.sql`. Highlight:

- 8 tables, 7 views, 35 queries;
- a window-function query (Q05/Q06/Q29);
- a CTE/coverage query (Q25/Q28);
- the opportunity view with weights stored in `opportunity_config`.

Show `data/reports/sql_query_results_index.csv`: 35/35 successful, row counts.

## 4. EDA and findings (90 seconds)

Open `docs/eda_report.md` and `data/reports/figures/`:

- city distribution and concentration;
- category mix;
- missingness by city/category;
- city × category heat map.

State the main findings with actual values: the largest city sample, the most
common category, the contact-data gap, and the covered city-category pairs. Do
not call the largest city the “best market”; it is the largest **collected
sample**.

## 5. Opportunity analysis (90 seconds)

Open `data/reports/top_opportunities.csv` and
`data/reports/fig_opportunity_top15.png`.

> The score is 100 × (0.60 × underrepresentation + 0.25 × city breadth gap +
> 0.15 × completeness). It ranks underrepresentation in the collected listings,
> not demand. A high score is a research candidate.

Show `opportunity_score_check.csv` and the reconciliation report: SQL and Python
agree within 0.02. Show candidate tiers and the methodology note. Explicitly say
that the score cannot support an investment decision.

## 6. Power BI story (60 seconds)

Open `powerbi/dashboard_design.md`:

1. Executive Overview — volume, mix, quality bands.
2. Geographic Coverage — map, ranking, coverage heat map.
3. Data Quality & Completeness — missing contact, review queue.
4. Market Opportunity — methodology banner, score decomposition, candidate table.

Be explicit:

> Power BI Desktop 2.159.883.0 is installed, but the report has not yet been
> generated or validated there. The model, Power Query and DAX are source
> controlled; PBIP/PBIX generation, refresh, validation and screenshots remain
> pending.

## 7. Close (30 seconds)

- One command/test story: `pytest -q`.
- Reconciliation: Python ↔ SQL.
- Limitations: one source, one snapshot, capped non-random sample, low contact
  completeness, heuristic opportunity score.
- What I would add next: a second independent source, repeated snapshots, and a
  business registry match to validate coverage.

## Backup questions

**Why is completeness so low?** Because the public OSM source often lacks phone
and structured address tags. The project does not enrich or invent them.

**Why not call the gaps opportunities?** Because listing underrepresentation is
not demand. The score is an explicit, reversible prioritisation heuristic.

**Why only one source?** The project prioritises verifiable real data over a
fabricated multi-source comparison. Adding a second source would require a new
quality/comparison methodology.

**What is verified?** Data collection, cleaning, validation, MySQL import, 35 SQL
queries, EDA, opportunity scoring, reconciliation and automated tests. **What is
not?** Power BI rendering, screenshots, scheduled refresh and cloud deployment.
