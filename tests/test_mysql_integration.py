"""Live MySQL integration tests.

Marked ``mysql``. They skip when the configured database is unavailable or has
not been imported. Run after:

    python scripts/import_data.py
    pytest -q -m mysql

Use ``--replace-data`` only on an explicitly approved disposable database; it
deletes existing listing, audit, reject and batch rows.
The tests compare the cleaned CSV with the committed database state. They never
write to the database.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
from sqlalchemy import create_engine, text

from analytics.business_insights.opportunity_analysis import (
    compute_opportunity_score,
    opportunity_tier,
)
from analytics.config import ConfigurationError, get_settings
from analytics.constants import CLEANED_CSV
from analytics.sql_analysis.run_queries import parse_queries

pytestmark = pytest.mark.mysql

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def engine():
    if not CLEANED_CSV.exists():
        pytest.skip("cleaned CSV not available")
    try:
        settings = get_settings()
        eng = create_engine(settings.database_url, pool_pre_ping=True, future=True)
        with eng.connect() as conn:
            total = conn.execute(text("SELECT COUNT(*) FROM listing_master")).scalar_one()
            if int(total) == 0:
                pytest.skip("database has no imported listings")
        yield eng
        eng.dispose()
    except (ConfigurationError, Exception) as exc:  # noqa: BLE001 - report skip reason
        pytest.skip(f"MySQL integration unavailable: {exc}")


@pytest.fixture(scope="module")
def cleaned() -> pd.DataFrame:
    df = pd.read_csv(CLEANED_CSV, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    df["quality_score"] = pd.to_numeric(df["quality_score"], errors="coerce").fillna(0)
    for field in ("missing_phone", "missing_address", "duplicate_flag", "is_complete"):
        df[field] = df[field].astype(str).str.lower().isin({"true", "1"})
    return df


def test_imported_rows_match_cleaned_csv(engine, cleaned):
    with engine.connect() as conn:
        listings = conn.execute(text("SELECT COUNT(*) FROM listing_master")).scalar_one()
        audits = conn.execute(text("SELECT COUNT(*) FROM data_quality_audit")).scalar_one()
        batches = conn.execute(text("SELECT COUNT(*) FROM import_batches")).scalar_one()
    assert int(listings) == len(cleaned)
    assert int(audits) == len(cleaned)
    assert int(batches) >= 1


def test_import_batch_is_completed(engine):
    with engine.connect() as conn:
        row = conn.execute(
            text(
                "SELECT rows_received, rows_inserted, rows_rejected, status "
                "FROM import_batches ORDER BY batch_id DESC LIMIT 1"
            )
        ).mappings().one()
    assert row["status"] == "completed"
    assert int(row["rows_inserted"]) > 0
    assert int(row["rows_inserted"]) <= int(row["rows_received"])


def test_seven_views_exist(engine):
    with engine.connect() as conn:
        count = conn.execute(
            text(
                "SELECT COUNT(*) FROM information_schema.tables "
                "WHERE table_schema = DATABASE() AND table_type = 'VIEW'"
            )
        ).scalar_one()
    assert int(count) == 7


def test_source_attribution_is_correct(engine):
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT attribution, license_name FROM dim_source ORDER BY source_id LIMIT 1")
        ).mappings().one()
        listings = conn.execute(text("SELECT COUNT(*) FROM listing_master")).scalar_one()
    assert int(listings) > 0
    assert "OpenStreetMap contributors" in row["attribution"]
    assert "ODbL" in row["license_name"]


def test_quality_summary_matches_pandas(engine, cleaned):
    with engine.connect() as conn:
        overall = pd.read_sql(text("SELECT * FROM vw_data_quality_summary"), conn).iloc[0]
    assert int(overall["total_listings"]) == len(cleaned)
    assert int(overall["missing_phone_count"]) == int(cleaned["missing_phone"].sum())
    assert int(overall["missing_address_count"]) == int(cleaned["missing_address"].sum())
    assert int(overall["duplicate_count"]) == int(cleaned["duplicate_flag"].sum())
    assert int(overall["complete_listings"]) == int(cleaned["is_complete"].sum())
    assert abs(float(overall["completeness_pct"]) - round(100 * cleaned["is_complete"].mean(), 2)) <= 0.01
    assert abs(float(overall["avg_quality_score"]) - round(float(cleaned["quality_score"].mean()), 2)) <= 0.01


def test_city_and_category_counts_match(engine, cleaned):
    with engine.connect() as conn:
        city = pd.read_sql(text("SELECT * FROM vw_city_summary"), conn)
        category = pd.read_sql(text("SELECT * FROM vw_category_summary"), conn)
    city_py = cleaned.groupby("city").size().to_dict()
    assert dict(zip(city["city_name"], city["listing_count"].astype(int))) == city_py
    category_py = cleaned.groupby("category").size().to_dict()
    category_db = {
        row["category_name"]: int(row["listing_count"])
        for _, row in category.iterrows()
        if int(row["listing_count"]) > 0
    }
    assert category_db == category_py


def test_city_category_universe_is_twelve_cities_by_twelve_categories(engine):
    with engine.connect() as conn:
        city_count = conn.execute(text("SELECT COUNT(*) FROM vw_city_summary")).scalar_one()
        pairs = conn.execute(text("SELECT COUNT(*) FROM vw_city_category_coverage")).scalar_one()
    assert int(city_count) == 12
    assert int(pairs) == 144


def test_opportunity_score_recomputes_in_python(engine):
    with engine.connect() as conn:
        config = pd.read_sql(
            text("SELECT * FROM opportunity_config WHERE config_id = 1"), conn
        ).iloc[0]
        frame = pd.read_sql(text("SELECT * FROM vw_market_opportunity"), conn)
        pairs = conn.execute(text("SELECT COUNT(*) FROM vw_market_opportunity")).scalar_one()
    weights = {
        "underrepresentation_weight": float(config["underrepresentation_weight"]),
        "city_breadth_weight": float(config["city_breadth_weight"]),
        "reliability_weight": float(config["reliability_weight"]),
    }
    assert abs(sum(weights.values()) - 1.0) < 1e-6
    assert len(frame) == int(pairs) == 144
    max_diff = 0.0
    for _, row in frame.iterrows():
        result = compute_opportunity_score(
            row["relative_representation"],
            row["city_category_coverage_pct"],
            row["city_completeness_pct"],
            weights,
        )
        max_diff = max(max_diff, abs(float(row["opportunity_score"]) - result["opportunity_score"]))
        expected_tier = opportunity_tier(
            result["opportunity_score"],
            bool(row["is_candidate"]),
            float(config["high_threshold"]),
            float(config["medium_threshold"]),
        )
        assert expected_tier == row["opportunity_tier"]
    assert max_diff <= 0.02


def test_all_35_analytical_queries_execute(engine):
    text_content = (ROOT / "database" / "analytical_queries.sql").read_text(encoding="utf-8")
    queries = parse_queries(text_content)
    assert len(queries) == 35
    with engine.connect() as conn:
        for query in queries:
            frame = pd.read_sql(text(query["sql"].rstrip(";")), conn)
            assert isinstance(frame, pd.DataFrame), query["query_id"]
