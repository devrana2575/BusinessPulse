"""Shared pytest fixtures and import path setup.

All fixtures are synthetic and deliberately tiny. They test rules, not the
real dataset. MySQL integration tests are marked and read the actual imported
CSV/database; they skip when no database is configured.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def make_raw_row(**overrides) -> dict:
    row = {
        "business_id": "BP-OSM-N-1",
        "business_name": "Alpha Cafe",
        "category": "Food & Beverage",
        "city": "Pune",
        "state_name": "Maharashtra",
        "country": "India",
        "address": "12 MG Road, Pune",
        "phone": "+91 98765 43210",
        "phone_raw": "+91 98765 43210",
        "latitude": 18.52,
        "longitude": 73.85,
        "source": "OpenStreetMap (Overpass API)",
        "source_type": "Open Data - Crowdsourced Map",
        "source_record_id": "node/1",
        "source_record_url": "https://www.openstreetmap.org/node/1",
        "collection_date": "2026-11-02",
        "created_at": "2026-11-02T00:00:00+00:00",
        "category_raw": "amenity=restaurant",
        "osm_tags_json": '{"amenity": "restaurant", "name": "Alpha Cafe"}',
    }
    row.update(overrides)
    return row


@pytest.fixture
def raw_rows() -> list[dict]:
    return [
        make_raw_row(),
        make_raw_row(
            business_id="BP-OSM-N-2",
            business_name="Beta Bakery",
            category="Food & Beverage",
            city="Mumbai",
            address="45 Linking Road, Mumbai",
            phone="",
            phone_raw="",
            source_record_id="node/2",
            latitude=19.05,
            longitude=72.87,
        ),
        make_raw_row(
            business_id="BP-OSM-N-3",
            business_name="Gamma Hardware",
            category="Home & Repair Services",
            city="Pune",
            address="8 Station Road, Pune",
            phone="020 1234 5678",
            phone_raw="020 1234 5678",
            source_record_id="node/3",
            latitude=18.53,
            longitude=73.86,
        ),
    ]


@pytest.fixture
def valid_raw_df(raw_rows) -> pd.DataFrame:
    return pd.DataFrame(raw_rows)


@pytest.fixture
def cleaned_df(valid_raw_df):
    from analytics.cleaning.cleaning import clean_dataframe

    return clean_dataframe(valid_raw_df).cleaned
