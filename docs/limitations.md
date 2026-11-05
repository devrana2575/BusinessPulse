# Limitations and honest interpretation

These are not footnotes added after the analysis; they constrain what the
results can support.

## 1. Source bias

OpenStreetMap is volunteered geographic information. Coverage varies by city,
neighbourhood, contributor activity and tagging conventions. The extract is
**not a business census**, and the 12-city bounding boxes are approximate urban
frames, not administrative market definitions. A low count can reflect mapping
neglect rather than a real market gap.

## 2. Capped, non-random sample

Each city/group query is capped (`out center N`) to keep the public endpoint
polite. Within a group, returned elements are not a random sample. Dense cities
may be systematically under-sampled. Do not treat shares as population shares or
compute confidence intervals as if this were a random survey.

## 3. Contact completeness is genuinely low

Most OSM business POIs in this snapshot do not publish a phone, and many lack a
structured address. The project reports this rather than enriching from another
source. A missing phone/address means **missing in the public source**, not
missing in reality. Any contactability conclusion is limited to the subset with
published data.

The strict completeness rule requires both a valid phone and a valid address and
no exact duplicate. It is intentionally demanding. A low completeness percentage
is a finding about usable records, not a claim that most businesses are
uncontactable.

## 4. One source

There is one real source. Source-level analysis is descriptive only. The project
does not claim cross-source agreement, source ranking, or “best source”. The
source summary pages exist to make the concentration and license visible, not to
imply comparison.

## 5. One snapshot

All rows share one collection date (`2026-11-02`). Month-over-month growth,
seasonality, trend and time-intelligence claims are not supported. There is no
`DimDate` in the Power BI model by design. `Snapshot Date` is a card, not a time
series.

## 6. Rule-based cleaning and entity resolution

- Phone normalisation keeps the first number and applies a digit/length rule.
  It can mis-handle unusual formats.
- Address validity is a minimum usability check, not proof of a real address.
- Exact duplicate rules use name + city + (address or phone). Potential
  duplicates use address similarity ≥0.90. Both can miss duplicates or flag
  branches incorrectly. Coordinates, opening hours and websites are not used.
- OSM tags are simplified into 12 categories. A mixed business may fit more than
  one category. The mapping priority is documented, but it is not ground truth.
- Names are normalised; brands, abbreviations and transliterations can remain
  inconsistent.

## 7. Quality score is a heuristic

The 0–100 score is documented and reproducible, but the penalties (20/25/20/10/5)
are project choices, not an industry standard. It measures record usability for
this analysis, not business quality, trustworthiness, or customer experience.
Quality bands are derived from that score.

## 8. Opportunity score is not a demand model

`opportunity_score` is a transparent prioritisation heuristic:

```
100 × (0.60 × underrepresentation
     + 0.25 × city breadth gap
     + 0.15 × completeness)
```

It uses only collected listing counts, category breadth and data reliability. It
does not observe revenue, footfall, customers, competitor quality, rent, supply
constraints, or willingness to pay. A high score means “underrepresented in this
sample and worth further research”, not “a profitable opportunity” or “low
competition”. Candidate thresholds (city ≥20 listings, category ≥5 national
listings) are evidence filters, not statistical significance tests.

## 9. SQL and Python are not independent data sources

The SQL views and Python code implement the same documented rules. The
reconciliation proves consistency, not external validity. A shared conceptual
mistake would not be detected by agreement between layers.

## 10. Power BI status

Power BI Desktop is installed from the Microsoft Store (version 2.159.883.0),
but the DAX, Power Query and design files have not yet been executed in Desktop.
There is no generated `.pbip`, `.pbix` or dashboard screenshot. These remain
pending deliverables, not verified outputs. Saved SQL/Python artifacts are
available, but current live database and BI rendering are not verified.

## 11. Not implemented

- Web app, API service, React/frontend, FastAPI/Flask/Streamlit.
- Automated Power BI publishing, gateway, scheduled refresh.
- Real-time or streaming data.
- Customer, transaction, revenue or demand data.
- Machine learning, forecasting or causal inference.
- Full business registry matching.
- Production security hardening or a publicly exposed database.

## 12. Responsible use

Do not use the opportunity ranking to make investment decisions without primary
research and better data. Do not present the listing counts as a complete market
map. Preserve OSM attribution and ODbL terms in any reuse. If the analysis is
extended with new sources or snapshots, version the methodology and re-run the
reconciliation rather than mixing definitions.
