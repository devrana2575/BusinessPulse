"""Shared constants for the BusinessPulse pipeline.

The dataset is a real OpenStreetMap extract collected through the public
Overpass API. Every collected record keeps its OSM provenance. See
docs/data_sources.md and data/raw/collection_manifest.json.
"""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
SAMPLE_DIR = DATA_DIR / "sample"
REPORTS_DIR = DATA_DIR / "reports"
FIGURES_DIR = REPORTS_DIR / "figures"
SQL_RESULTS_DIR = REPORTS_DIR / "sql"
DATABASE_DIR = PROJECT_ROOT / "database"
DOCS_DIR = PROJECT_ROOT / "docs"
POWERBI_DIR = PROJECT_ROOT / "powerbi"

RAW_CSV = RAW_DIR / "business_listings_raw.csv"
CLEANED_CSV = PROCESSED_DIR / "cleaned_business_listings.csv"
REJECTED_CSV = PROCESSED_DIR / "rejected_records.csv"
DUPLICATES_CSV = PROCESSED_DIR / "duplicate_records.csv"
POTENTIAL_DUPLICATES_CSV = PROCESSED_DIR / "potential_duplicate_records.csv"
CLEANING_LOG_CSV = PROCESSED_DIR / "cleaning_log.csv"
QUALITY_SUMMARY_CSV = REPORTS_DIR / "data_quality_summary.csv"
MISSING_VALUES_CSV = REPORTS_DIR / "missing_values_report.csv"

# Canonical 12-city collection frame. Bounding boxes are [south, west, north, east]
# as returned by OpenStreetMap Nominatim for each city on 2026-11-02.
CITY_METADATA: dict[str, dict] = {
    "Pune": {
        "state_name": "Maharashtra",
        "country": "India",
        "bbox": [18.3613738, 73.6945071, 18.6813738, 74.0145071],
        "latitude": 18.5213738,
        "longitude": 73.8545071,
    },
    "Mumbai": {
        "state_name": "Maharashtra",
        "country": "India",
        "bbox": [18.8949990, 72.7092035, 19.2149990, 73.0292035],
        "latitude": 19.0549990,
        "longitude": 72.8692035,
    },
    "Bengaluru": {
        "state_name": "Karnataka",
        "country": "India",
        "bbox": [12.8334905, 77.4598797, 13.1426196, 77.7840639],
        "latitude": 12.9880551,
        "longitude": 77.6219718,
    },
    "Delhi": {
        "state_name": "Delhi",
        "country": "India",
        "bbox": [28.4046285, 76.8388351, 28.8834464, 77.3453379],
        "latitude": 28.6440375,
        "longitude": 77.0920865,
    },
    "Hyderabad": {
        "state_name": "Telangana",
        "country": "India",
        "bbox": [17.2916377, 78.2387067, 17.5608321, 78.6223912],
        "latitude": 17.4262349,
        "longitude": 78.4305490,
    },
    "Chennai": {
        "state_name": "Tamil Nadu",
        "country": "India",
        "bbox": [12.8519771, 80.1339233, 13.2351580, 80.3328982],
        "latitude": 13.0435676,
        "longitude": 80.2334108,
    },
    "Kolkata": {
        "state_name": "West Bengal",
        "country": "India",
        "bbox": [22.4335321, 88.2421429, 22.6325679, 88.4589549],
        "latitude": 22.5330500,
        "longitude": 88.3505489,
    },
    "Ahmedabad": {
        "state_name": "Gujarat",
        "country": "India",
        "bbox": [22.8615374, 72.4200568, 23.1815374, 72.7400568],
        "latitude": 23.0215374,
        "longitude": 72.5800568,
    },
    "Jaipur": {
        "state_name": "Rajasthan",
        "country": "India",
        "bbox": [26.7554576, 75.6589817, 27.0754576, 75.9789817],
        "latitude": 26.9154576,
        "longitude": 75.8189817,
    },
    "Surat": {
        "state_name": "Gujarat",
        "country": "India",
        "bbox": [21.0494892, 72.6717058, 21.3694892, 72.9917058],
        "latitude": 21.2094892,
        "longitude": 72.8317058,
    },
    "Lucknow": {
        "state_name": "Uttar Pradesh",
        "country": "India",
        "bbox": [26.6781000, 80.7746001, 26.9981000, 81.0946001],
        "latitude": 26.8381000,
        "longitude": 80.9346001,
    },
    "Chandigarh": {
        "state_name": "Chandigarh",
        "country": "India",
        "bbox": [30.5734421, 76.6197143, 30.8934421, 76.9397143],
        "latitude": 30.7334421,
        "longitude": 76.7797143,
    },
}

CATEGORIES: tuple[str, ...] = (
    "Food & Beverage",
    "Retail",
    "Health & Pharmacy",
    "Finance & Banking",
    "Professional Services",
    "Hospitality",
    "Beauty & Personal Care",
    "Automotive",
    "Education & Training",
    "Fitness & Recreation",
    "Home & Repair Services",
    "Other Services",
)

SOURCE_METADATA: dict[str, str] = {
    "source_name": "OpenStreetMap (Overpass API)",
    "source_type": "Open Data - Crowdsourced Map",
    "source_url": "https://overpass-api.de/",
    "license_name": "Open Database License (ODbL) 1.0",
    "license_url": "https://opendatacommons.org/licenses/odbl/1-0/",
    "attribution": "© OpenStreetMap contributors",
}

SOURCE_NAME = SOURCE_METADATA["source_name"]

# Overpass QL groups. Each query is deliberately bounded and rate-limited.
# A group is a union of tag filters followed by a single "out center" cap.
OSM_QUERY_GROUPS: tuple[dict, ...] = (
    {
        "key": "food",
        "filters": [
            ("amenity", "restaurant|cafe|fast_food|bar|pub|food_court|ice_cream|biergarten"),
            (
                "shop",
                "bakery|butcher|greengrocer|confectionery|cheese|meat|fish|seafood|"
                "delicatessen|beverages|alcohol|wine|coffee|tea|spices|health_food|farm",
            ),
        ],
        "limit": 35,
    },
    {
        "key": "retail",
        "filters": [("shop", None)],
        "limit": 60,
    },
    {
        "key": "health_finance",
        "filters": [
            ("amenity", "pharmacy|hospital|clinic|doctors|dentist|veterinary|bank|bureau_de_change"),
            ("healthcare", None),
            (
                "office",
                "lawyer|accountant|insurance|financial|estate_agent|architect|engineer|"
                "company|it|consulting|employment_agency|surveyor|tax_advisor|travel_agent|yes",
            ),
        ],
        "limit": 45,
    },
    {
        "key": "hospitality_leisure",
        "filters": [
            ("tourism", "hotel|guest_house|hostel|motel|apartment"),
            ("leisure", "fitness_centre|sports_centre|swimming_pool|stadium"),
            ("amenity", "cinema|theatre|nightclub|casino"),
        ],
        "limit": 35,
    },
    {
        "key": "services_trades",
        "filters": [
            (
                "shop",
                "car|car_repair|car_parts|motorcycle|motorcycle_repair|tyres|"
                "beauty|hairdresser|massage|laundry|dry_cleaning|tailor|travel_agency|"
                "pet|pet_grooming|mobile_phone|electronics|hardware|doityourself|"
                "building_materials|paint|electrical|plumbing|garden_centre",
            ),
            (
                "amenity",
                "fuel|car_wash|car_rental|driving_school|language_school|music_school|training",
            ),
            ("craft", None),
        ],
        "limit": 45,
    },
)

# Fields required in the raw and cleaned datasets.
REQUIRED_FIELDS: tuple[str, ...] = (
    "business_id",
    "business_name",
    "category",
    "city",
    "source",
    "source_record_id",
    "collection_date",
    "created_at",
)

# Opportunity scoring defaults. These values are also stored in the
# opportunity_config table so SQL, Python, and Power BI use one definition.
OPPORTUNITY_WEIGHTS: dict[str, float] = {
    "underrepresentation_weight": 0.60,
    "city_breadth_weight": 0.25,
    "reliability_weight": 0.15,
}
OPPORTUNITY_THRESHOLDS: dict[str, float] = {
    "high_threshold": 60.0,
    "medium_threshold": 40.0,
    "min_city_listings": 20,
    "min_category_national_count": 5,
}


def ensure_directories() -> None:
    """Create every output directory used by the pipeline."""
    for path in (
        RAW_DIR,
        PROCESSED_DIR,
        SAMPLE_DIR,
        REPORTS_DIR,
        FIGURES_DIR,
        SQL_RESULTS_DIR,
        DATABASE_DIR,
        DOCS_DIR,
        POWERBI_DIR,
    ):
        path.mkdir(parents=True, exist_ok=True)
