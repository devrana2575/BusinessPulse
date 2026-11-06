"""Transparent city-category opportunity analysis.

The canonical metric is defined once in database/views.sql. This module reads
that view, independently recomputes the score in Python to prove the formula
is reproducible, and exports BI-ready tables and a chart.

Important: a low count means "underrepresented in the collected listings",
not "low competition" or "high demand". The output language must preserve that
distinction.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import pandas as pd
from sqlalchemy import create_engine, text

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from analytics.config import ConfigurationError, get_settings  # noqa: E402
from analytics.constants import (  # noqa: E402
    FIGURES_DIR,
    OPPORTUNITY_THRESHOLDS,
    OPPORTUNITY_WEIGHTS,
    REPORTS_DIR,
    ensure_directories,
)
from analytics.reporting.theme import PALETTE, apply_style, save_figure  # noqa: E402


def compute_opportunity_score(
    relative_representation: float | None,
    city_category_coverage_pct: float | None,
    city_completeness_pct: float | None,
    weights: dict[str, float] | None = None,
) -> dict[str, float]:
    """Pure, documented score calculation used by tests and reconciliation."""
    weights = weights or OPPORTUNITY_WEIGHTS
    total_weight = sum(weights.values())
    if abs(total_weight - 1.0) > 1e-6:
        raise ValueError("Opportunity weights must sum to 1.0")
    relative = 0.0 if relative_representation is None or pd.isna(relative_representation) else float(relative_representation)
    coverage = 0.0 if city_category_coverage_pct is None or pd.isna(city_category_coverage_pct) else float(city_category_coverage_pct)
    completeness = 0.0 if city_completeness_pct is None or pd.isna(city_completeness_pct) else float(city_completeness_pct)
    underrepresentation = max(0.0, 1.0 - relative)
    breadth_gap = 1.0 - coverage / 100.0
    reliability = completeness / 100.0
    score = 100.0 * (
        weights["underrepresentation_weight"] * underrepresentation
        + weights["city_breadth_weight"] * breadth_gap
        + weights["reliability_weight"] * reliability
    )
    return {
        "underrepresentation_index": round(underrepresentation, 4),
        "city_breadth_gap": round(breadth_gap, 4),
        "reliability_index": round(reliability, 4),
        "underrepresentation_points": round(
            100.0 * weights["underrepresentation_weight"] * underrepresentation, 2
        ),
        "breadth_points": round(100.0 * weights["city_breadth_weight"] * breadth_gap, 2),
        "reliability_points": round(100.0 * weights["reliability_weight"] * reliability, 2),
        "opportunity_score": round(score, 2),
    }


def opportunity_tier(
    score: float,
    is_candidate: bool,
    high_threshold: float | None = None,
    medium_threshold: float | None = None,
) -> str:
    high = OPPORTUNITY_THRESHOLDS["high_threshold"] if high_threshold is None else high_threshold
    medium = OPPORTUNITY_THRESHOLDS["medium_threshold"] if medium_threshold is None else medium_threshold
    if not is_candidate:
        return "Insufficient evidence"
    if score >= high:
        return "High"
    if score >= medium:
        return "Medium"
    return "Low"


def load_config(engine) -> dict[str, float]:
    with engine.connect() as conn:
        row = conn.execute(
            text(
                "SELECT underrepresentation_weight, city_breadth_weight, reliability_weight, "
                "high_threshold, medium_threshold, min_city_listings, min_category_national_count "
                "FROM opportunity_config WHERE config_id = 1"
            )
        ).mappings().first()
    if not row:
        raise RuntimeError("opportunity_config row 1 is missing; run seed_data.sql")
    return {key: float(value) for key, value in row.items()}


def analysis(engine) -> dict[str, Any]:
    config = load_config(engine)
    weights = {
        "underrepresentation_weight": config["underrepresentation_weight"],
        "city_breadth_weight": config["city_breadth_weight"],
        "reliability_weight": config["reliability_weight"],
    }
    if abs(sum(weights.values()) - 1.0) > 1e-6:
        raise RuntimeError(f"Stored opportunity weights do not sum to 1: {weights}")

    with engine.connect() as conn:
        frame = pd.read_sql(text("SELECT * FROM vw_market_opportunity"), conn)
    if frame.empty:
        raise RuntimeError("vw_market_opportunity returned no rows; import data first")

    recomputed = frame.apply(
        lambda row: compute_opportunity_score(
            row["relative_representation"],
            row["city_category_coverage_pct"],
            row["city_completeness_pct"],
            weights,
        ),
        axis=1,
        result_type="expand",
    )
    frame = pd.concat([frame, recomputed.add_prefix("python_")], axis=1)
    frame["score_difference"] = (
        frame["opportunity_score"] - frame["python_opportunity_score"]
    ).abs().round(4)
    frame["tier_check"] = [
        opportunity_tier(
            float(row["python_opportunity_score"]),
            bool(row["is_candidate"]),
            config["high_threshold"],
            config["medium_threshold"],
        )
        for _, row in frame.iterrows()
    ]
    frame["tier_match"] = frame["tier_check"] == frame["opportunity_tier"]

    max_diff = float(frame["score_difference"].max())
    mismatches = int((frame["score_difference"] > 0.02).sum())
    tier_mismatches = int((~frame["tier_match"]).sum())
    if mismatches or tier_mismatches:
        raise RuntimeError(
            f"SQL/Python opportunity mismatch: max score diff={max_diff}, "
            f"score mismatches={mismatches}, tier mismatches={tier_mismatches}"
        )

    candidates = frame.loc[frame["is_candidate"] == 1].copy()
    top = candidates.sort_values(
        ["opportunity_score", "relative_representation", "city_name", "category_name"],
        ascending=[False, True, True, True],
    ).head(25)
    underrepresented = candidates.loc[candidates["relative_representation"] < 0.5].copy()
    coverage_summary = pd.DataFrame(
        [
            {
                "total_city_category_pairs": len(frame),
                "covered_pairs": int(frame["is_covered"].sum()),
                "coverage_pct": round(100 * frame["is_covered"].mean(), 2),
                "candidate_pairs": int(frame["is_candidate"].sum()),
                "high_tier_pairs": int((frame["opportunity_tier"] == "High").sum()),
                "medium_tier_pairs": int((frame["opportunity_tier"] == "Medium").sum()),
                "low_tier_pairs": int((frame["opportunity_tier"] == "Low").sum()),
                "insufficient_evidence_pairs": int(
                    (frame["opportunity_tier"] == "Insufficient evidence").sum()
                ),
                "max_sql_python_score_difference": round(max_diff, 4),
                "score_mismatches": mismatches,
                "tier_mismatches": tier_mismatches,
                "methodology_version": "v1.0",
            }
        ]
    )
    return {
        "all": frame,
        "top": top,
        "underrepresented": underrepresented,
        "coverage_summary": coverage_summary,
        "config": config,
    }


def build_chart(top: pd.DataFrame) -> Path:
    apply_style()
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    data = top.head(15).sort_values("opportunity_score", ascending=True).copy()
    colors = [
        PALETTE["coral"] if tier == "High" else PALETTE["amber"] if tier == "Medium" else PALETTE["teal"]
        for tier in data["opportunity_tier"]
    ]
    labels = data["city_name"] + " | " + data["category_name"]
    fig, ax = plt.subplots(figsize=(10, 6.5))
    ax.barh(labels, data["opportunity_score"], color=colors)
    ax.set_title("Top candidate coverage gaps (underrepresentation in collected listings)")
    ax.set_xlabel("Opportunity score (0-100) - not a demand forecast")
    ax.set_xlim(0, 100)
    ax.grid(axis="y", visible=False)
    for index, value in enumerate(data["opportunity_score"]):
        ax.text(value + 1, index, f"{value:.1f}", va="center", fontsize=8)
    path = FIGURES_DIR / "fig_opportunity_top15.png"
    save_figure(fig, path)
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description="Run city-category opportunity analysis")
    parser.parse_args()
    ensure_directories()
    try:
        settings = get_settings()
    except ConfigurationError as exc:
        raise SystemExit(f"Configuration error: {exc}") from exc
    engine = create_engine(settings.database_url, pool_pre_ping=True, future=True)
    try:
        result = analysis(engine)
    finally:
        engine.dispose()

    result["all"].to_csv(REPORTS_DIR / "market_opportunities.csv", index=False, encoding="utf-8")
    result["top"].to_csv(REPORTS_DIR / "top_opportunities.csv", index=False, encoding="utf-8")
    result["underrepresented"].to_csv(
        REPORTS_DIR / "underrepresented_categories_by_city.csv", index=False, encoding="utf-8"
    )
    result["coverage_summary"].to_csv(
        REPORTS_DIR / "coverage_summary.csv", index=False, encoding="utf-8"
    )
    score_check = result["all"][
        [
            "city_name", "category_name", "opportunity_score",
            "python_opportunity_score", "score_difference", "opportunity_tier",
            "tier_check", "tier_match", "is_candidate",
        ]
    ]
    score_check.to_csv(REPORTS_DIR / "opportunity_score_check.csv", index=False, encoding="utf-8")
    chart = build_chart(result["top"])
    summary = result["coverage_summary"].iloc[0].to_dict()
    print("Opportunity analysis complete")
    for key, value in summary.items():
        print(f"  {key}: {value}")
    print(f"Top chart: {chart}")


if __name__ == "__main__":
    main()
