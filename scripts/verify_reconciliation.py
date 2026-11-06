"""Reconcile Python/Pandas metrics with the MySQL reporting views.

Critical analytical values must agree across the CSV layer, the database views
and the opportunity formula. Power BI is not available in this environment, so
its reconciliation remains a documented manual checklist.
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from analytics.business_insights.opportunity_analysis import (  # noqa: E402
    compute_opportunity_score,
)
from analytics.config import ConfigurationError, get_settings  # noqa: E402
from analytics.constants import CLEANED_CSV, REPORTS_DIR, ensure_directories  # noqa: E402


def bool_series(series: pd.Series) -> pd.Series:
    return series.astype(str).str.strip().str.lower().isin({"true", "1", "yes"})


def add_check(
    rows: list[dict],
    metric: str,
    python_value,
    sql_value,
    tolerance: float,
    note: str = "",
) -> None:
    try:
        py_num = float(python_value)
        sql_num = float(sql_value)
        difference = abs(py_num - sql_num)
        passed = difference <= tolerance + 1e-9
    except (TypeError, ValueError):
        py_num = python_value
        sql_num = sql_value
        difference = None
        passed = str(python_value) == str(sql_value)
    rows.append(
        {
            "metric": metric,
            "python_value": python_value,
            "sql_value": sql_value,
            "absolute_difference": round(difference, 6) if isinstance(difference, float) else difference,
            "tolerance": tolerance,
            "status": "PASS" if passed else "FAIL",
            "note": note,
        }
    )


def main() -> None:
    ensure_directories()
    try:
        settings = get_settings()
    except ConfigurationError as exc:
        raise SystemExit(f"Configuration error: {exc}") from exc
    df = pd.read_csv(CLEANED_CSV, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    df["quality_score"] = pd.to_numeric(df["quality_score"], errors="coerce").fillna(0)
    for field in ("missing_phone", "missing_address", "duplicate_flag", "is_complete"):
        df[field] = bool_series(df[field])

    engine = create_engine(settings.database_url, pool_pre_ping=True, future=True)
    rows: list[dict] = []
    with engine.connect() as conn:
        overall = pd.read_sql(text("SELECT * FROM vw_data_quality_summary"), conn).iloc[0]
        city_sql = pd.read_sql(text("SELECT * FROM vw_city_summary"), conn)
        category_sql = pd.read_sql(text("SELECT * FROM vw_category_summary"), conn)
        coverage_sql = pd.read_sql(text("SELECT * FROM vw_city_category_coverage"), conn)
        opportunity_sql = pd.read_sql(text("SELECT * FROM vw_market_opportunity"), conn)
        config = pd.read_sql(text("SELECT * FROM opportunity_config WHERE config_id = 1"), conn).iloc[0]

    total = len(df)
    add_check(rows, "total_listings", total, overall["total_listings"], 0)
    add_check(rows, "missing_phone_count", int(df["missing_phone"].sum()), overall["missing_phone_count"], 0)
    add_check(rows, "missing_phone_pct", round(100 * df["missing_phone"].mean(), 2), overall["missing_phone_pct"], 0.05)
    add_check(rows, "missing_address_count", int(df["missing_address"].sum()), overall["missing_address_count"], 0)
    add_check(rows, "missing_address_pct", round(100 * df["missing_address"].mean(), 2), overall["missing_address_pct"], 0.05)
    add_check(rows, "duplicate_count", int(df["duplicate_flag"].sum()), overall["duplicate_count"], 0)
    add_check(rows, "duplicate_rate_pct", round(100 * df["duplicate_flag"].mean(), 2), overall["duplicate_rate_pct"], 0.05)
    add_check(rows, "complete_listings", int(df["is_complete"].sum()), overall["complete_listings"], 0)
    add_check(rows, "completeness_pct", round(100 * df["is_complete"].mean(), 2), overall["completeness_pct"], 0.05)
    add_check(rows, "avg_quality_score", round(float(df["quality_score"].mean()), 2), overall["avg_quality_score"], 0.02)

    city_py = df.groupby("city").size().to_dict()
    city_db = dict(zip(city_sql["city_name"], city_sql["listing_count"]))
    for city in sorted(set(city_py) | set(city_db)):
        add_check(
            rows, f"city_listing_count::{city}",
            int(city_py.get(city, 0)), int(city_db.get(city, 0)), 0,
        )
    category_py = df.groupby("category").size().to_dict()
    category_db = dict(zip(category_sql["category_name"], category_sql["listing_count"]))
    for category in sorted(set(category_py) | set(category_db)):
        add_check(
            rows, f"category_listing_count::{category}",
            int(category_py.get(category, 0)), int(category_db.get(category, 0)), 0,
        )

    covered_py = df.groupby(["city", "category"]).size().shape[0]
    covered_sql = int(coverage_sql["is_covered"].sum())
    add_check(rows, "covered_city_category_pairs", covered_py, covered_sql, 0)
    add_check(rows, "city_category_universe", 12 * 12, len(coverage_sql), 0)

    weights = {
        "underrepresentation_weight": float(config["underrepresentation_weight"]),
        "city_breadth_weight": float(config["city_breadth_weight"]),
        "reliability_weight": float(config["reliability_weight"]),
    }
    diffs: list[float] = []
    for _, row in opportunity_sql.iterrows():
        result = compute_opportunity_score(
            row["relative_representation"],
            row["city_category_coverage_pct"],
            row["city_completeness_pct"],
            weights,
        )
        diffs.append(abs(float(row["opportunity_score"]) - result["opportunity_score"]))
    add_check(rows, "max_opportunity_score_difference", round(max(diffs), 4), 0.0, 0.02,
              "Python recomputation vs vw_market_opportunity")

    report = pd.DataFrame(rows)
    report.to_csv(REPORTS_DIR / "reconciliation_report.csv", index=False, encoding="utf-8")
    failures = int((report["status"] == "FAIL").sum())
    md_lines = [
        "# BusinessPulse - SQL / Python Reconciliation Report",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat(timespec='seconds')}",
        "",
        f"- Checks: {len(report)}",
        f"- Passed: {len(report) - failures}",
        f"- Failed: {failures}",
        "",
        "The comparison is between Pandas over the cleaned CSV and the MySQL",
        "reporting views. Power BI is not installed in this environment; its",
        "critical values are listed in the manual verification checklist.",
        "",
        "| Metric | Python | SQL | Difference | Tolerance | Status |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for _, row in report.iterrows():
        md_lines.append(
            f"| {row['metric']} | {row['python_value']} | {row['sql_value']} | "
            f"{row['absolute_difference']} | {row['tolerance']} | {row['status']} |"
        )
    (REPORTS_DIR / "reconciliation_report.md").write_text("\n".join(md_lines), encoding="utf-8")
    print(f"Checks: {len(report)}; passed: {len(report) - failures}; failed: {failures}")
    print(f"Report: {REPORTS_DIR / 'reconciliation_report.csv'}")
    if failures:
        print(report.loc[report["status"] == "FAIL"].to_string(index=False))
        raise SystemExit(1)


if __name__ == "__main__":
    main()
