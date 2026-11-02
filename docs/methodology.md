# Methodology

## 1. Scope and unit of analysis

The unit is a **collected business listing**: one unique OSM element that maps to
a business-like category and has a name and coordinate. The snapshot is
**2026-11-02** across 12 Indian cities. The project describes that collected
sample. It does not estimate the population of all businesses, demand, revenue,
or causal effects.

## 2. Raw → cleaned pipeline

1. **Raw preservation.** `business_listings_raw.csv` is written once from cached
   Overpass responses. Raw phone/address/tag values are preserved.
2. **Normalisation.** Names are Unicode NFKC-normalised, whitespace-collapsed,
   and stripped of surrounding quotes/punctuation. City and category aliases are
   mapped to canonical values. Phones are normalised without inventing digits.
3. **Address assembly.** Only published `addr:*` components are combined:
   `addr:full` first; otherwise house number + street/place, suburb/neighbourhood,
   and postcode. No geocoding or external lookup fills a blank address.
4. **Validation.** Required fields, canonical membership, source, dates,
   coordinates and audit consistency are checked. Blocking errors stop import;
   warnings document quality issues.
5. **Duplicate detection.** Exact and potential duplicate rules below.
6. **Audit flags and scores.** Every row receives `missing_phone`,
   `missing_address`, `phone_valid`, `address_valid`, `duplicate_flag`,
   `potential_duplicate_flag`, `is_complete`, `validation_status`,
   `quality_score` and `quality_band`.
7. **Import.** Listing and audit rows are inserted in one transaction. Rejected
   rows are recorded with reasons. A file hash prevents accidental duplicate
   imports.

## 3. Canonical cities and categories

Cities: Pune, Mumbai, Bengaluru, Delhi, Hyderabad, Chennai, Kolkata, Ahmedabad,
Jaipur, Surat, Lucknow, Chandigarh. Aliases such as Bombay → Mumbai are
documented in `analytics/cleaning/cleaning.py`.

Categories (12): Food & Beverage; Retail; Health & Pharmacy; Finance & Banking;
Professional Services; Hospitality; Beauty & Personal Care; Automotive;
Education & Training; Fitness & Recreation; Home & Repair Services; Other
Services. OSM tag rules are deterministic; the exact rule is stored in
`category_raw`, for example `amenity=restaurant` or `shop=car_repair`. When an
element matches several groups, the documented priority order is applied. This
is a simplification: one POI can sell food and retail goods.

## 4. Phone and address rules

### Phone

- Take the first number when several are separated by `;` or `/`.
- Strip an extension and punctuation; keep a leading `+`; convert `00` to `+`.
- Placeholders (`n/a`, `-`, `0`, etc.) become blank.
- Keep a value only if it has 7–15 digits after normalisation.
- A present phone is **valid** when the raw value has no letters outside an
  extension, 7–15 digits, and is not a repeated single digit.
- A missing phone is not imputed.

### Address

- Build from published address tags only.
- Normalise commas and whitespace.
- A present address is **valid** for the audit when it has at least two tokens
  and six characters. This is a minimum usability rule, not proof of a real-world
  address.
- A missing address is not geocoded or filled from the map pin.

### Completeness

`is_complete = phone present and valid AND address present and valid AND not an
exact duplicate`. This is a deliberately strict contactability definition. It
is why the completeness rate is low; that is a finding, not a bug.

## 5. Duplicate rules

Rows are grouped by `(city, normalised name)`. An **exact duplicate** is a
non-canonical member of a connected component where records share the same
non-empty normalised address **or** the same non-empty normalised phone. One
canonical record remains unflagged; other members are flagged and retained (not
silently deleted). A shared brand with different branches/phones is not an exact
duplicate.

A **potential duplicate** is a same-name/city pair with similar but non-identical
addresses (SequenceMatcher ratio ≥ 0.90) and no shared phone. These are flagged
for review only and are not counted in the duplicate KPI.

Limitations: this is not a full entity-resolution system. It does not use
coordinates, opening hours, websites, or fuzzy branch names. It can miss
duplicates with different names and can over-flag branches with the same phone
and address pattern.

## 6. Quality score

The 0–100 score starts at 100 and subtracts documented penalties:

| Condition | Penalty |
|---|---:|
| Missing phone | −20 |
| Missing address | −25 |
| Exact duplicate flag | −20 |
| Phone present but malformed | −10 |
| Address present but too short/unstructured | −5 |

Score is floored at 0. Bands: High 80–100; Medium 60–79; Low <60. The score is a
data-quality prioritisation tool, not a business quality rating. A business with
no public phone can be excellent; the score only says the record is less usable
for contact analysis.

## 7. Validation severities

**Blocking errors:** missing required fields/columns, invalid city/category,
unexpected source, duplicate `business_id`, duplicate source record, invalid
date/coordinate, out-of-range quality score, audit inconsistency.

**Warnings:** missing phone/address, malformed contact fields, missing
coordinates, future collection date, status/completeness mismatch. Warnings do
not prevent import. Rejected rows are stored in `rejected_records.csv` and, on
import, in `listing_rejects`.

## 8. Opportunity score (v1.0)

The canonical formula is in `database/views.sql` and stored in
`opportunity_config`:

```
relative_representation =
    (listings in city-category / listings in city)
    / (national category listings / national listings)

underrepresentation = max(0, 1 - relative_representation)
city_breadth_gap   = 1 - (categories present in city / 12)
reliability        = city completeness % / 100

opportunity_score = 100 × (
    0.60 × underrepresentation
  + 0.25 × city_breadth_gap
  + 0.15 × reliability
)
```

Candidate rule: a pair is scored only when the city has ≥20 collected listings
and the category has ≥5 national listings. Non-candidates get tier
`Insufficient evidence`. Tiers: High ≥60, Medium ≥40, Low <40 after rounding to
2 decimals.

Why these components:

- **Underrepresentation (60%)** makes the score sensitive to a city-category
  share below the national category baseline.
- **City breadth gap (25%)** gives some weight to a city having a narrow
  category mix overall.
- **Reliability (15%)** rewards cells in cities with more complete contact data,
  but is deliberately a minority of the score.

Important interpretation: a high score means “this cell is underrepresented in
the collected sample and has enough evidence to review”. It does **not** mean
“open a business here”, “low competition”, or “high demand”. The data has no
revenue, footfall, competitor quality, or customer-demand measure.

The score is recomputed independently in
`analytics/business_insights/opportunity_analysis.py` and
`scripts/verify_reconciliation.py`; SQL/Python differences above 0.02 fail the
reconciliation.

## 9. SQL analytical approach

The 35 queries cover:

- dataset health and snapshot;
- city and category distributions/ranks;
- concentration and cumulative share;
- city × category coverage and within-city shares;
- missing contact fields and duplicate rates;
- source concentration (descriptive only);
- opportunity ranking, decomposition, candidate gaps and KPI summary.

They use joins, `GROUP BY`, CTEs, window functions (`RANK`, `DENSE_RANK`,
`ROW_NUMBER`, running sums), `CASE`, `NULLIF`, `HAVING` and `LIMIT`. The runner
exports every result to CSV and records row counts/status.

## 10. Reproducibility and reconciliation

- Cleaning is deterministic given the raw CSV and quality rules.
- The database import is transactional and rejects a repeated file hash.
- `scripts/verify_reconciliation.py` compares Pandas metrics with MySQL views,
  including counts, percentages, averages and the opportunity formula.
- Power BI is not installed in the build environment; DAX/model validation is
  explicitly pending manual action, not claimed as verified.

## 11. What would change with more data

More sources, repeated snapshots, and a business registry could support
cross-source validation, trends and population estimates. Those are outside the
current scope. Adding them would require new source-level quality analysis and a
new methodology version; the current results should not be extrapolated.
