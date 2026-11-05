# Business insights

> **Scope:** a snapshot of **collected public OSM listings** on **2026-11-02**.
> These findings describe the sample, not the population of businesses, demand,
> revenue, or competition. Missing contact data is a source limitation, not a
> reason to infer a contact. See [`limitations.md`](limitations.md).

The numbers below are generated from the final cleaned CSV and MySQL views:
`data/processed/cleaned_business_listings.csv`, `data/reports/*.csv`,
`data/reports/sql/Q01–Q35_*.csv`, and `data/reports/reconciliation_report.md`.

## 1. Dataset at a glance

| Metric | Value |
|---|---:|
| Raw / cleaned listings | 2,252 / 2,252 |
| Cities | 12 |
| Categories | 12 |
| Missing phone | 2,088 (92.72%) |
| Missing address | 1,615 (71.71%) |
| Exact duplicates flagged (retained) | 3 (0.13%) |
| Strict complete listings | 129 (5.73%) |
| Mean audit score / median | 63.36 / 55.00 |
| Covered city × category pairs | 123 / 144 (85.42%) |
| Candidate opportunity cells | 132 |
| High-tier opportunity cells | 12 |

The raw and cleaned counts are equal because no row failed blocking validation
and no row was rejected during cleaning. That does **not** mean the rows are
complete; completeness is a separate, strict audit flag. The low completeness
rate is the main data-quality story.

## 2. City distribution is broad, not concentrated

| City | Listings | Share | Categories present | Complete |
|---|---:|---:|---:|---:|
| Surat | 206 | 9.15% | 10 | 14.56% |
| Chennai | 201 | 8.93% | 10 | 4.98% |
| Ahmedabad | 192 | 8.53% | 11 | 6.25% |
| Pune | 192 | 8.53% | 11 | 5.21% |
| Bengaluru | 190 | 8.44% | 11 | 4.74% |
| Jaipur | 189 | 8.39% | 10 | 11.11% |
| Hyderabad | 186 | 8.26% | 9 | 0.54% |
| Mumbai | 185 | 8.21% | 10 | 4.32% |
| Kolkata | 182 | 8.08% | 11 | 3.85% |
| Chandigarh | 179 | 7.95% | 9 | 4.47% |
| Lucknow | 176 | 7.82% | 11 | 5.11% |
| Delhi | 174 | 7.73% | 10 | 2.30% |

The largest city sample (Surat, 206) is only 32 listings larger than the
smallest (Delhi, 174). Because the collection frame and caps are consistent
across cities, **city volume is fairly even in this extract**. That is a
collection-design result, not evidence that the real cities have equal business
counts. Do not read Surat as the “best market” or Delhi as the “worst”; these
are sample sizes.

The useful comparison is not raw volume but **what is present within each
city**. Hyderabad and Chandigarh have only 9 of 12 categories; Surat, Chennai,
Jaipur, Mumbai and Delhi have 10; the remaining cities have 11. This is where
the coverage analysis becomes more informative than the city ranking.

## 3. Retail and food dominate; specialist categories are thin

| Category | Listings | Share | Cities present | Complete |
|---|---:|---:|---:|---:|
| Retail | 452 | 20.07% | 12 | 7.30% |
| Food & Beverage | 447 | 19.85% | 12 | 6.26% |
| Automotive | 351 | 15.59% | 12 | 1.71% |
| Hospitality | 275 | 12.21% | 12 | 9.45% |
| Health & Pharmacy | 244 | 10.83% | 12 | 5.74% |
| Finance & Banking | 224 | 9.95% | 12 | 0.89% |
| Fitness & Recreation | 124 | 5.51% | 11 | 2.42% |
| Professional Services | 62 | 2.75% | 11 | 19.35% |
| Beauty & Personal Care | 42 | 1.87% | 11 | 4.76% |
| Home & Repair Services | 21 | 0.93% | 10 | 9.52% |
| Other Services | 8 | 0.36% | 6 | 12.50% |
| Education & Training | 2 | 0.09% | 2 | 0.00% |

Retail and Food & Beverage together account for **about 40%** of the sample.
Automotive, Hospitality, Health and Finance add another ~48%. The long tail is
thin: Education & Training has 2 records and Other Services has 8. This is
consistent with OSM mapping visibility for consumer-facing POIs, but it is also
a **category coverage limitation**. A category with two records cannot support
a reliable city-level comparison.

Professional Services has the highest strict completeness (19.35%) despite its
small count; Automotive (1.71%) and Finance & Banking (0.89%) are the weakest.
Completeness varies by category, not just by city.

## 4. Contact data is the binding constraint

Only **129 of 2,252** listings (5.73%) have a usable phone **and** a usable
address **and** are not flagged as an exact duplicate. The two missing-field
facts dominate:

- **2,088 listings (92.72%) have no phone.** This is the largest quality gap.
- **1,615 listings (71.71%) have no structured address.**
- A further 5 present phones fail the documented 7–15 digit rule; 54 present
  addresses are too short/unstructured for the audit. These are *not* missing
  values, but they are not usable for contact analysis.
- 2,123 records are `needs_review`; 129 are `valid`.

This is not a cleaning failure. The source simply does not publish contact data
for most POIs. The project deliberately does **not** enrich from Google, Justdial
or another provider. Any contactability statement applies only to the 129
complete records, not to the full sample.

The quality bands reflect the same rules: 588 records are High (80–100), 72 are
Medium (60–79), and 1,592 are Low (<60). A Low band can be caused entirely by
missing public contact data; it is not a judgment about the business.

## 5. Coverage is high but category mix is uneven

The city × category universe is **144 pairs** (12 cities × 12 categories).
**123 pairs (85.42%)** have at least one listing; 21 are empty. Coverage is
therefore high at the “does this cell have any record?” level, while the
category-count distribution remains uneven.

This distinction matters:

- **Coverage** says whether a cell is represented at all.
- **Volume** says how many records it has.
- **Opportunity score** combines underrepresentation, city breadth and
  completeness. It does not measure demand.

The city breadth gap is largest for Hyderabad and Chandigarh (9/12 categories,
gap 0.25) and smallest for the five cities with 11/12 (gap 0.0833). That directly
influences the opportunity ranking.

## 6. Opportunity ranking: useful as a review queue, not a forecast

The canonical formula is:

```text
100 × (0.60 × underrepresentation
     + 0.25 × city breadth gap
     + 0.15 × completeness)
```

There are **132 candidate pairs** (city has ≥20 listings and category has ≥5
national listings). **12 are High tier, 5 Medium, 115 Low**, and 12 have
insufficient evidence. The top of the ranking is:

| Rank | City | Category | Listings | Score | Tier |
|---:|---|---|---:|---:|---|
| 1 | Chandigarh | Home & Repair Services | 0 | 66.92 | High |
| 2 | Chandigarh | Other Services | 0 | 66.92 | High |
| 3 | Surat | Other Services | 0 | 66.35 | High |
| 4 | Hyderabad | Beauty & Personal Care | 0 | 66.33 | High |
| 5 | Hyderabad | Professional Services | 0 | 66.33 | High |
| 6 | Jaipur | Other Services | 0 | 65.83 | High |
| 7 | Chennai | Other Services | 0 | 64.91 | High |
| 8 | Mumbai | Fitness & Recreation | 0 | 64.82 | High |
| 9 | Delhi | Home & Repair Services | 0 | 64.51 | High |
| 10 | Ahmedabad | Other Services | 0 | 63.02 | High |
| 11 | Pune | Other Services | 0 | 62.86 | High |
| 12 | Jaipur | Fitness & Recreation | 1 | 60.07 | High |

**Eleven of the 12 High-tier cells have zero collected listings.** The twelfth
has one. A zero count is a strong signal of **mapping/sampling absence**, not
proof of an untapped market. For example, “Other Services” is a residual
category with only 8 records nationally; its zero-city cells are especially
likely to be an artifact of category visibility. The ranking is best used to
decide **where to investigate the source and the local market**, not where to
invest.

This is why the README and dashboard label the score as
“underrepresentation in collected listings”. The score is transparent and
reproducible, but it is not a demand, revenue or competition model.

## 7. What to do next (research actions, not business advice)

1. **Improve the source before expanding the ranking.** A second independent
   source or a targeted local validation would test whether zero/low cells are
   real gaps or mapping absence.
2. **Prioritize data collection for the thinnest categories:** Education &
   Training, Other Services, Home & Repair Services, Beauty & Personal Care.
   These categories have too few records for reliable city comparisons.
3. **Treat missing phone/address as a measurement problem.** A contactability
   analysis should be limited to the 129 complete records or use a new source
   with better contact coverage. Do not impute.
4. **Keep the city comparison contextual.** The even city volumes are caused
   partly by equal caps; they are not population estimates.
5. **Re-run the score only after versioning the methodology.** The weights and
   thresholds are a documented heuristic, not a universal standard.

## 8. What cannot be concluded

- That Surat has more real businesses than Delhi, or that any city is a better
  market.
- That a zero-listing category has no competitors or high demand.
- That the 2,123 `needs_review` records are invalid businesses. They are usable
  listings with missing or malformed contact fields.
- That the 3 exact duplicates are the only duplicate entities; rule-based
  matching is limited.
- That OSM coverage equals real-world business density.
- That the Power BI report was rendered. The report is specified, not built or
  screenshotted in this environment.

## 9. Reproduce the numbers

```powershell
python scripts/businesspulse.py clean --confirm-regenerate
python scripts/businesspulse.py validate
python scripts/businesspulse.py import --database businesspulse --confirm-target-empty
python scripts/businesspulse.py analyze --database businesspulse
python scripts/businesspulse.py eda
python scripts/businesspulse.py insights --database businesspulse
python scripts/businesspulse.py reconcile --database businesspulse
```

The database must be independently approved and verified. Import refuses an
existing/populated target and is not a replacement workflow.

For the full automated check:

```powershell
python -m pytest -q
```

The historical 2026-11-02 run reported **99 tests passed**, **35/35 SQL queries executed**, and
**37/37 reconciliation checks passed**. See [`testing.md`](testing.md) and
`data/reports/reconciliation_report.md` for the exact outputs.
