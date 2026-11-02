# Data sources and collection

## Source

| Item | Value |
|---|---|
| Source | OpenStreetMap (OSM) points of interest |
| Access | Public Overpass API (main endpoint + public mirror; per-query endpoint in manifest) |
| Licence | Open Database License (ODbL) 1.0 |
| Attribution | © OpenStreetMap contributors |
| Source type | Open data — volunteered geographic information |
| Snapshot date | **2026-11-02** |
| Collection method | Bounded Overpass QL queries, one request at a time |
| Geography | 12 Indian cities, each with a Nominatim-derived bounding box |
| Analytical grain | One unique OSM element (node/way/relation) with a business-like tag |

The exact query text, endpoint, HTTP status, attempt count, element count and
cache path are recorded in `data/raw/collection_manifest.json`. Every raw row
keeps `source_record_id` (`node/123`, `way/456`, …), `source_record_url`, the
raw phone and the original OSM tag JSON.

## Licence and attribution requirements

OSM data is © OpenStreetMap contributors and available under ODbL 1.0. Any
public use of this dataset or derivative database must attribute OSM and comply
with ODbL share-alike/attribution requirements. The project displays the
attribution in the README, documentation, database `dim_source` row and Power BI
footer. This repository is an educational portfolio project, not legal advice;
review ODbL obligations before republishing a derivative database.

## City frame

Bounding boxes are approximate city extents supplied by Nominatim on the
collection date. They can include neighbouring urban areas; they are not
administrative boundaries. This is a deliberate, reproducible collection frame,
not a claim about municipal market size.

| City | State/UT | South | West | North | East |
|---|---|---:|---:|---:|---:|
| Pune | Maharashtra | 18.3613738 | 73.6945071 | 18.6813738 | 74.0145071 |
| Mumbai | Maharashtra | 18.8949990 | 72.7092035 | 19.2149990 | 73.0292035 |
| Bengaluru | Karnataka | 12.8334905 | 77.4598797 | 13.1426196 | 77.7840639 |
| Delhi | Delhi | 28.4046285 | 76.8388351 | 28.8834464 | 77.3453379 |
| Hyderabad | Telangana | 17.2916377 | 78.2387067 | 17.5608321 | 78.6223912 |
| Chennai | Tamil Nadu | 12.8519771 | 80.1339233 | 13.2351580 | 80.3328982 |
| Kolkata | West Bengal | 22.4335321 | 88.2421429 | 22.6325679 | 88.4589549 |
| Ahmedabad | Gujarat | 22.8615374 | 72.4200568 | 23.1815374 | 72.7400568 |
| Jaipur | Rajasthan | 26.7554576 | 75.6589817 | 27.0754576 | 75.9789817 |
| Surat | Gujarat | 21.0494892 | 72.6717058 | 21.3694892 | 72.9917058 |
| Lucknow | Uttar Pradesh | 26.6781000 | 80.7746001 | 26.9981000 | 81.0946001 |
| Chandigarh | Chandigarh | 30.5734421 | 76.6197143 | 30.8934421 | 76.9397143 |

## Query design and caps

Five tag groups are queried for each city. Each group is a union of bounded
tag filters followed by `out center N`, where `N` is the documented cap:

| Group | Main tags | Cap per city |
|---|---|---:|
| `food` | Food/drink amenities and food shops | 35 |
| `retail` | Any `shop=*` POI | 60 |
| `health_finance` | Pharmacies, clinics, healthcare, banks, finance/professional offices | 45 |
| `hospitality_leisure` | Hotels/guest houses, fitness/sport, cinemas/theatres | 35 |
| `services_trades` | Vehicle services, beauty/laundry/tailoring, trades/crafts, training | 45 |

The cap keeps the public endpoint polite and the portfolio dataset bounded. It
also means **the dataset is a capped sample, not an exhaustive extract**. Within a
group, OSM returns matching elements in the endpoint's order; the cap can
systematically omit some POIs, especially in dense cities. This is a known
limitation, not a random sample.

## Politeness, retries and caching

`analytics/data_collection/collect_osm_data.py`:

- sends one request at a time with a default 2-second delay;
- retries HTTP 429/5xx/timeouts with exponential backoff and jitter (up to six
  attempts by default);
- caches every successful JSON response under `data/raw/osm_responses/`;
- reuses cache on rerun unless `--refresh` is passed;
- writes the manifest only after all requested cities/groups finish.

A failed query is recorded with status `failed` and a reason. The final dataset
must be checked for failed entries before it is treated as complete. The raw CSV
is built from **all valid cached responses**, and the manifest gives the query
provenance.

### Endpoint note for this snapshot

The first **31** cached groups were collected from
`https://overpass-api.de/api/interpreter`. The main endpoint then returned HTTP
502 (“at capacity”) for an extended period. The remaining **29** groups were
collected from the public mirror
`https://overpass.openstreetmap.fr/api/interpreter`; a different mirror returned
HTTP 200 with zero elements and was rejected (empty broad queries are treated
as failures, not data). Every query entry in `collection_manifest.json` records
the endpoint that produced its cache, and the manifest lists both observed
endpoints. This is an availability workaround, not data enrichment: all values
remain OpenStreetMap/ODbL data.

Cache files have a small `.meta.json` sidecar recording their origin. The HTTP
cache itself is gitignored because it is large; the final raw CSV and manifest
are committed.

## Business inclusion rules

A raw OSM element becomes a business listing only when:

1. it has a usable name (`name`, `name:en`, or `brand`);
2. it maps to one of the 12 analytical categories through documented OSM tags;
3. it is not in the explicit non-business exclusion list (government, school,
   park, place of worship, vacant shop, etc.);
4. it has a usable coordinate (or a way/relation center);
5. it is unique by OSM type + id.

OSM elements can be unnamed. Those are skipped during raw building and counted
in the build summary; they are not invented or labelled from a generic category.
Similarly, a POI with a missing phone or address stays missing. The project does
not enrich from Google, Justdial, or any other source.

## What this source cannot tell you

- It is not a business census; OSM coverage varies by city, contributor
  activity, mapping conventions and tagging completeness.
- A missing phone/address does not mean the real business lacks one.
- A low count does not measure demand, revenue, footfall, competition or market
  size.
- One source means no cross-source verification. The source page is descriptive,
  not comparative.
- Open map data has positional and duplicate risk. Exact duplicates are flagged
  with transparent rules; potential duplicates are retained for review.

## Re-collection

```powershell
# Re-use cached responses; only missing groups are queried.
python -m analytics.data_collection.collect_osm_data

# Force fresh collection (polite defaults; expect throttling/backoff).
python -m analytics.data_collection.collect_osm_data --refresh

# Subset for a quick check
python -m analytics.data_collection.collect_osm_data --cities Pune,Mumbai
```

Overpass is shared infrastructure. Do not raise concurrency, remove delays, or
run repeated full refreshes while developing. Respect the endpoint's usage
policy and retry/backoff signals.
