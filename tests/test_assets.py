"""Static contract tests for the SQL, Power BI and repository assets.

These tests do not execute Power BI. They verify that the deliverable files
exist and that the repository does not silently claim a web stack or fabricate a
rendered report.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from analytics.sql_analysis.run_queries import parse_queries, slug

ROOT = Path(__file__).resolve().parents[1]


def test_schema_has_eight_base_tables():
    schema = (ROOT / "database" / "schema.sql").read_text(encoding="utf-8")
    assert schema.count("CREATE TABLE IF NOT EXISTS") == 8
    for table in (
        "dim_city",
        "dim_category",
        "dim_source",
        "import_batches",
        "listing_master",
        "data_quality_audit",
        "listing_rejects",
        "opportunity_config",
    ):
        assert f"CREATE TABLE IF NOT EXISTS {table}" in schema


def test_views_have_seven_reporting_views():
    views = (ROOT / "database" / "views.sql").read_text(encoding="utf-8")
    assert views.count("CREATE OR REPLACE VIEW") == 7
    for view in (
        "vw_listing_detail",
        "vw_city_summary",
        "vw_category_summary",
        "vw_source_summary",
        "vw_data_quality_summary",
        "vw_city_category_coverage",
        "vw_market_opportunity",
    ):
        assert f"CREATE OR REPLACE VIEW {view}" in views


def test_exactly_35_analytical_queries_are_parseable():
    text = (ROOT / "database" / "analytical_queries.sql").read_text(encoding="utf-8")
    queries = parse_queries(text)
    assert len(queries) == 35
    assert [query["query_id"] for query in queries] == [f"Q{i:02d}" for i in range(1, 36)]
    assert all(query["sql"] for query in queries)
    assert all(query["title"] for query in queries)
    assert len({query["query_id"] for query in queries}) == 35


def test_query_slug_is_stable():
    assert slug("Dataset health snapshot") == "dataset_health_snapshot"
    assert slug("City-wise category distribution and category rank") == (
        "city_wise_category_distribution_and_category_rank"
    )


def test_opportunity_formula_is_documented_in_sql():
    views = (ROOT / "database" / "views.sql").read_text(encoding="utf-8")
    assert "0.60 * underrepresentation" in views
    assert "0.25 * city breadth gap" in views
    assert "0.15 * reliability" in views
    assert "not proof of low competition" in views.lower()


def test_powerbi_files_exist():
    required = [
        "README.md",
        "dax_measures.dax",
        "data_model.md",
        "power_query_guide.md",
        "dashboard_design.md",
        "implementation_checklist.json",
        "screenshots/README.md",
        "power_query_m/stg_Listings.pq",
        "power_query_m/FactListings.pq",
        "power_query_m/FactDataQuality.pq",
        "power_query_m/FactCityCategoryCoverage.pq",
        "power_query_m/DimCity.pq",
        "power_query_m/DimCategory.pq",
        "power_query_m/DimSource.pq",
    ]
    for relative in required:
        assert (ROOT / "powerbi" / relative).exists(), relative


def test_data_quality_query_has_no_city_or_category_ids():
    # Prevents the documented ambiguous relationship path.
    text = (ROOT / "powerbi" / "power_query_m" / "FactDataQuality.pq").read_text(
        encoding="utf-8"
    )
    assert '"city_id"' not in text
    assert '"category_id"' not in text


def test_dax_contains_core_and_quality_measures():
    text = (ROOT / "powerbi" / "dax_measures.dax").read_text(encoding="utf-8")
    for measure in (
        "Total Listings =",
        "Unique Businesses =",
        "Total Cities =",
        "Total Categories =",
        "Total Sources =",
        "Average Listings per City =",
        "Listings with Phone Numbers =",
        "Listings without Phone Numbers =",
        "Listings with Complete Addresses =",
        "Phone Availability Percentage =",
        "Address Availability Percentage =",
        "Complete Records Percentage =",
        "City Contribution % =",
        "City Coverage % =",
        "Geographic Coverage % =",
        "City Concentration HHI (Collected Listings) =",
        "Missing Phone % =",
        "Completeness % =",
        "Opportunity Score =",
        "High Opportunity Gaps =",
        "Methodology Note =",
        "Candidate Opportunity Score =",
        "Report Context =",
    ):
        assert measure in text


def test_dashboard_specification_has_four_pages():
    text = (ROOT / "powerbi" / "dashboard_design.md").read_text(encoding="utf-8")
    for page in (
        "Page 1 — Executive Overview",
        "Page 2 — Geographic Coverage",
        "Page 3 — Data Quality & Completeness",
        "Page 4 — Market Opportunity",
    ):
        assert page in text


def test_powerbi_implementation_checklist_tracks_generated_project_honestly():
    checklist = json.loads(
        (ROOT / "powerbi" / "implementation_checklist.json").read_text(
            encoding="utf-8"
        )
    )
    assert checklist["desktop"]["validation_performed"] is False
    assert checklist["status"] == "PBIP GENERATED — DESKTOP VALIDATION PENDING"
    assert checklist["generated_project"]["pbip_generated"] is True
    assert checklist["generated_project"]["pbix_generated"] is False
    assert [page["title"] for page in checklist["pages"]] == [
        "Executive Overview",
        "Geographic Market Analysis",
        "Data Quality Analysis",
        "Market Opportunity Analysis",
    ]
    assert all(
        page["status"] == "generated_not_desktop_validated"
        for page in checklist["pages"]
    )
    for asset in checklist["source_assets"]:
        for relative in asset.get("files", []):
            assert (ROOT / relative).is_file()
        assert asset["can_be_automated"]
        assert asset["requires_desktop"]


def test_no_fake_pbix_or_screenshot_files():
    assert not list(ROOT.glob("**/*.pbix"))
    assert (ROOT / "powerbi" / "generated" / "BusinessPulse.pbip").is_file()
    assert (
        ROOT
        / "powerbi"
        / "generated"
        / "BusinessPulse.SemanticModel"
        / "definition"
        / "tables"
        / "FactListings.tmdl"
    ).is_file()
    image_files = []
    for suffix in ("*.png", "*.jpg", "*.jpeg"):
        image_files.extend((ROOT / "powerbi").rglob(suffix))
    assert image_files == []


def test_no_web_framework_in_requirements():
    requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8").lower()
    for forbidden in ("fastapi", "flask", "django", "react", "streamlit"):
        assert forbidden not in requirements


def test_screenshots_readme_is_honest():
    text = (ROOT / "powerbi" / "screenshots" / "README.md").read_text(encoding="utf-8")
    assert "No Power BI screenshots are stored here." in text
    assert "has not" in text
    assert "rendered in Power BI Desktop" in text
    assert "Do not substitute generated images" in text


def test_powerbi_phase_evidence_and_model_documentation_exist():
    required = (
        ROOT / "powerbi" / "documentation" / "data_model.md",
        ROOT / "reports" / "powerbi" / "repository_baseline.md",
        ROOT / "reports" / "powerbi" / "mysql_verification_report.md",
        ROOT / "reports" / "powerbi" / "metric_reconciliation.csv",
        ROOT / "reports" / "powerbi" / "final_powerbi_audit.md",
    )
    assert all(path.exists() for path in required)


def test_powerbi_metric_reconciliation_keeps_desktop_values_unclaimed():
    path = ROOT / "reports" / "powerbi" / "metric_reconciliation.csv"
    with path.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) >= 10
    assert all(row["powerbi_value"] == "" for row in rows)
    assert all(row["validation_status"] == "PARTIAL" for row in rows)
