"""Exploratory data analysis with interpretation-ready outputs.

Reads the cleaned CSV so the analysis is reproducible without a database,
and exports tables + Matplotlib figures used by docs/eda_report.md.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from analytics.constants import (  # noqa: E402
    CATEGORIES,
    CLEANED_CSV,
    FIGURES_DIR,
    RAW_CSV,
    REPORTS_DIR,
    ensure_directories,
)
from analytics.reporting.theme import PALETTE, SERIES, apply_style, save_figure  # noqa: E402


def markdown_table(frame: pd.DataFrame, max_rows: int = 12) -> str:
    if frame.empty:
        return "_No rows._"
    view = frame.head(max_rows).copy()
    columns = [str(column) for column in view.columns]
    lines = ["| " + " | ".join(columns) + " |", "|" + "|".join(["---"] * len(columns)) + "|"]
    for _, row in view.iterrows():
        values = []
        for value in row:
            if isinstance(value, float):
                values.append(f"{value:,.2f}")
            else:
                values.append(str(value).replace("|", "\\|"))
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def bool_series(series: pd.Series) -> pd.Series:
    return series.astype(str).str.strip().str.lower().isin({"true", "1", "yes"})


def build_tables(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    total = len(df)
    df = df.copy()
    df["is_complete_bool"] = bool_series(df["is_complete"])
    df["duplicate_bool"] = bool_series(df["duplicate_flag"])
    df["missing_phone_bool"] = bool_series(df["missing_phone"])
    df["missing_address_bool"] = bool_series(df["missing_address"])

    city = (
        df.groupby(["city", "state_name"], as_index=False)
        .agg(
            listing_count=("business_id", "count"),
            categories_present=("category", "nunique"),
            missing_phone=("missing_phone_bool", "sum"),
            missing_address=("missing_address_bool", "sum"),
            duplicates=("duplicate_bool", "sum"),
            complete_listings=("is_complete_bool", "sum"),
            avg_quality_score=("quality_score", "mean"),
        )
        .sort_values(["listing_count", "city"], ascending=[False, True])
    )
    city["share_pct"] = (100 * city["listing_count"] / total).round(2)
    city["missing_phone_pct"] = (100 * city["missing_phone"] / city["listing_count"]).round(2)
    city["missing_address_pct"] = (100 * city["missing_address"] / city["listing_count"]).round(2)
    city["completeness_pct"] = (100 * city["complete_listings"] / city["listing_count"]).round(2)
    city["category_coverage_pct"] = (100 * city["categories_present"] / len(CATEGORIES)).round(2)
    city["avg_quality_score"] = city["avg_quality_score"].round(2)
    city["rank"] = city["listing_count"].rank(method="min", ascending=False).astype(int)

    category = (
        df.groupby("category", as_index=False)
        .agg(
            listing_count=("business_id", "count"),
            cities_present=("city", "nunique"),
            missing_phone=("missing_phone_bool", "sum"),
            missing_address=("missing_address_bool", "sum"),
            duplicates=("duplicate_bool", "sum"),
            complete_listings=("is_complete_bool", "sum"),
            avg_quality_score=("quality_score", "mean"),
        )
        .sort_values(["listing_count", "category"], ascending=[False, True])
    )
    category["share_pct"] = (100 * category["listing_count"] / total).round(2)
    category["missing_phone_pct"] = (100 * category["missing_phone"] / category["listing_count"]).round(2)
    category["missing_address_pct"] = (100 * category["missing_address"] / category["listing_count"]).round(2)
    category["completeness_pct"] = (100 * category["complete_listings"] / category["listing_count"]).round(2)
    category["city_coverage_pct"] = (100 * category["cities_present"] / df["city"].nunique()).round(2)
    category["avg_quality_score"] = category["avg_quality_score"].round(2)

    source = (
        df.groupby(["source", "source_type"], as_index=False)
        .agg(
            listing_count=("business_id", "count"),
            cities_present=("city", "nunique"),
            categories_present=("category", "nunique"),
            missing_phone=("missing_phone_bool", "sum"),
            missing_address=("missing_address_bool", "sum"),
            duplicates=("duplicate_bool", "sum"),
            complete_listings=("is_complete_bool", "sum"),
            avg_quality_score=("quality_score", "mean"),
        )
    )
    source["share_pct"] = (100 * source["listing_count"] / total).round(2)
    source["missing_phone_pct"] = (100 * source["missing_phone"] / source["listing_count"]).round(2)
    source["missing_address_pct"] = (100 * source["missing_address"] / source["listing_count"]).round(2)
    source["duplicate_rate_pct"] = (100 * source["duplicates"] / source["listing_count"]).round(2)
    source["completeness_pct"] = (100 * source["complete_listings"] / source["listing_count"]).round(2)
    source["avg_quality_score"] = source["avg_quality_score"].round(2)

    pair = (
        df.groupby(["city", "category"], as_index=False)
        .size()
        .rename(columns={"size": "listing_count"})
    )
    pair["city_total"] = pair.groupby("city")["listing_count"].transform("sum")
    pair["category_share_in_city_pct"] = (
        100 * pair["listing_count"] / pair["city_total"]
    ).round(2)
    pair["is_covered"] = 1

    quality_band = df["quality_band"].value_counts().rename_axis("quality_band").reset_index(name="listing_count")
    quality_band["share_pct"] = (100 * quality_band["listing_count"] / total).round(2)
    status = df["validation_status"].value_counts().rename_axis("validation_status").reset_index(name="listing_count")
    status["share_pct"] = (100 * status["listing_count"] / total).round(2)

    missing = pd.DataFrame(
        {
            "field": [
                "phone missing",
                "address missing",
                "phone present but invalid",
                "address present but invalid",
            ],
            "missing_count": [
                int(df["missing_phone_bool"].sum()),
                int(df["missing_address_bool"].sum()),
                int((~bool_series(df["phone_valid"]) & ~df["missing_phone_bool"]).sum()),
                int((~bool_series(df["address_valid"]) & ~df["missing_address_bool"]).sum()),
            ],
        }
    )
    missing["missing_pct"] = (100 * missing["missing_count"] / total).round(2)

    raw_records = 0
    if RAW_CSV.exists():
        raw_records = len(pd.read_csv(RAW_CSV, usecols=["business_id"], dtype=str))
    summary = pd.DataFrame(
        [
            ("raw_records", raw_records),
            ("cleaned_records", total),
            ("distinct_cities", df["city"].nunique()),
            ("distinct_categories", df["category"].nunique()),
            ("distinct_sources", df["source"].nunique()),
            ("collection_dates", df["collection_date"].nunique()),
            ("missing_phone_count", int(df["missing_phone_bool"].sum())),
            ("missing_phone_pct", round(100 * df["missing_phone_bool"].mean(), 2)),
            ("missing_address_count", int(df["missing_address_bool"].sum())),
            ("missing_address_pct", round(100 * df["missing_address_bool"].mean(), 2)),
            ("duplicate_count", int(df["duplicate_bool"].sum())),
            ("duplicate_rate_pct", round(100 * df["duplicate_bool"].mean(), 2)),
            ("complete_listings", int(df["is_complete_bool"].sum())),
            ("completeness_pct", round(100 * df["is_complete_bool"].mean(), 2)),
            ("avg_quality_score", round(float(df["quality_score"].mean()), 2)),
            ("median_quality_score", round(float(df["quality_score"].median()), 2)),
            ("covered_city_category_pairs", pair.shape[0]),
            ("possible_city_category_pairs", df["city"].nunique() * len(CATEGORIES)),
        ],
        columns=["metric", "value"],
    )
    return {
        "city": city,
        "category": category,
        "source": source,
        "pair": pair,
        "quality_band": quality_band,
        "status": status,
        "missing": missing,
        "summary": summary,
    }


def build_figures(df: pd.DataFrame, tables: dict[str, pd.DataFrame]) -> list[Path]:
    apply_style()
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []

    city = tables["city"].sort_values("listing_count", ascending=True)
    fig, ax = plt.subplots(figsize=(9, 6))
    ax.barh(city["city"], city["listing_count"], color=PALETTE["navy"])
    ax.set_title("Collected listings by city")
    ax.set_xlabel("Listing records")
    ax.grid(axis="y", visible=False)
    for index, value in enumerate(city["listing_count"]):
        ax.text(value, index, f" {value:,}", va="center", fontsize=8, color=PALETTE["navy"])
    path = FIGURES_DIR / "fig_city_distribution.png"
    save_figure(fig, path)
    paths.append(path)

    category = tables["category"].sort_values("listing_count", ascending=True)
    fig, ax = plt.subplots(figsize=(9, 6))
    ax.barh(category["category"], category["listing_count"], color=PALETTE["teal"])
    ax.set_title("Collected listings by category")
    ax.set_xlabel("Listing records")
    ax.grid(axis="y", visible=False)
    for index, value in enumerate(category["listing_count"]):
        ax.text(value, index, f" {value:,}", va="center", fontsize=8, color=PALETTE["navy"])
    path = FIGURES_DIR / "fig_category_distribution.png"
    save_figure(fig, path)
    paths.append(path)

    source = tables["source"]
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.bar(source["source"], source["listing_count"], color=PALETTE["amber"], width=0.5)
    ax.set_title("Collected listings by source")
    ax.set_ylabel("Listing records")
    ax.tick_params(axis="x", rotation=0)
    ax.grid(axis="x", visible=False)
    for index, value in enumerate(source["listing_count"]):
        ax.text(index, value, f"{value:,}", ha="center", va="bottom", fontsize=9)
    path = FIGURES_DIR / "fig_source_distribution.png"
    save_figure(fig, path)
    paths.append(path)

    missing = tables["missing"]
    fig, ax = plt.subplots(figsize=(8, 4.5))
    colors = [PALETTE["red"] if value >= 50 else PALETTE["amber"] for value in missing["missing_pct"]]
    ax.bar(missing["field"], missing["missing_pct"], color=colors, width=0.55)
    ax.set_title("Missing / invalid field share")
    ax.set_ylabel("Percent of cleaned records")
    ax.set_ylim(0, 105)
    for index, value in enumerate(missing["missing_pct"]):
        ax.text(index, value + 2, f"{value:.1f}%", ha="center", fontsize=9)
    path = FIGURES_DIR / "fig_missing_values.png"
    save_figure(fig, path)
    paths.append(path)

    city_complete = tables["city"].sort_values("completeness_pct", ascending=True)
    fig, ax = plt.subplots(figsize=(9, 5.5))
    ax.barh(city_complete["city"], city_complete["completeness_pct"], color=PALETTE["coral"])
    ax.set_title("Completeness by city (phone + address + not duplicate)")
    ax.set_xlabel("Completeness %")
    ax.set_xlim(0, 100)
    for index, value in enumerate(city_complete["completeness_pct"]):
        ax.text(value + 1, index, f"{value:.1f}%", va="center", fontsize=8)
    path = FIGURES_DIR / "fig_completeness_by_city.png"
    save_figure(fig, path)
    paths.append(path)

    category_complete = tables["category"].sort_values("completeness_pct", ascending=True)
    fig, ax = plt.subplots(figsize=(9, 6))
    ax.barh(category_complete["category"], category_complete["completeness_pct"], color=PALETTE["green"])
    ax.set_title("Completeness by category")
    ax.set_xlabel("Completeness %")
    ax.set_xlim(0, 100)
    for index, value in enumerate(category_complete["completeness_pct"]):
        ax.text(value + 1, index, f"{value:.1f}%", va="center", fontsize=8)
    path = FIGURES_DIR / "fig_completeness_by_category.png"
    save_figure(fig, path)
    paths.append(path)

    pivot = (
        tables["pair"]
        .pivot(index="city", columns="category", values="listing_count")
        .reindex(index=sorted(df["city"].unique()), columns=list(CATEGORIES))
        .fillna(0)
    )
    fig, ax = plt.subplots(figsize=(12, 6.5))
    image = ax.imshow(pivot.values, aspect="auto", cmap="YlGnBu")
    ax.set_xticks(range(len(pivot.columns)))
    ax.set_xticklabels(pivot.columns, rotation=35, ha="right", fontsize=8)
    ax.set_yticks(range(len(pivot.index)))
    ax.set_yticklabels(pivot.index, fontsize=8)
    for row in range(pivot.shape[0]):
        for col in range(pivot.shape[1]):
            value = int(pivot.values[row, col])
            ax.text(col, row, value, ha="center", va="center", fontsize=7,
                    color="white" if value >= max(1, pivot.values.max() * 0.55) else "#1F3A5F")
    ax.set_title("City x category listing counts (collected sample)")
    fig.colorbar(image, ax=ax, shrink=0.8, label="Listings")
    ax.grid(False)
    path = FIGURES_DIR / "fig_city_category_heatmap.png"
    save_figure(fig, path)
    paths.append(path)

    scores = df["quality_score"].astype(float)
    fig, ax = plt.subplots(figsize=(8, 4.5))
    bins = [0, 20, 40, 60, 80, 100.01]
    ax.hist(scores, bins=bins, color=PALETTE["navy"], edgecolor="white")
    ax.set_title("Distribution of data-quality scores")
    ax.set_xlabel("Quality score (0-100)")
    ax.set_ylabel("Listing records")
    path = FIGURES_DIR / "fig_quality_score_distribution.png"
    save_figure(fig, path)
    paths.append(path)

    band = tables["quality_band"]
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.bar(band["quality_band"], band["listing_count"], color=SERIES[: len(band)], width=0.55)
    ax.set_title("Quality band distribution")
    ax.set_ylabel("Listing records")
    for index, value in enumerate(band["listing_count"]):
        ax.text(index, value, f"{value:,}", ha="center", va="bottom", fontsize=9)
    path = FIGURES_DIR / "fig_quality_band_distribution.png"
    save_figure(fig, path)
    paths.append(path)

    return paths


def write_report(
    df: pd.DataFrame,
    tables: dict[str, pd.DataFrame],
    figures: list[Path],
    *,
    figure_prefix: str,
) -> str:
    city = tables["city"]
    category = tables["category"]
    source = tables["source"]
    summary = dict(zip(tables["summary"]["metric"], tables["summary"]["value"]))
    top_city = city.iloc[0] if not city.empty else None
    bottom_city = city.iloc[-1] if not city.empty else None
    top_category = category.iloc[0] if not category.empty else None
    low_category = category.iloc[-1] if not category.empty else None
    raw_count = int(summary.get("raw_records", 0))
    cleaned_count = int(summary.get("cleaned_records", 0))
    figure_lines = "\n".join(
        f"![{path.stem}]({figure_prefix}/{path.name})" for path in figures
    )
    report = f"""# BusinessPulse - Exploratory Data Analysis Report

## 1. Objective

Describe the collected business-listing sample, quantify its geographic and
category composition, expose data-quality limitations, and generate evidence
for the four Power BI pages.

## 2. Dataset description

- Source: **OpenStreetMap via the Overpass API** (ODbL 1.0).
- Snapshot: **{df['collection_date'].mode().iloc[0]}**.
- Raw records: **{raw_count:,}**; cleaned records: **{cleaned_count:,}**.
- Cities: **{df['city'].nunique()}**; categories: **{df['category'].nunique()}**;
  sources: **{df['source'].nunique()}**.
- Grain: one collected business POI per row. This is a sample of public map
  listings, not a complete business census.

## 3. Cleaning and validation steps

The raw extract is preserved in `data/raw/business_listings_raw.csv`. Cleaning
normalises business names, cities, categories, addresses and phone formats;
it does not invent missing contact data. Exact duplicates are flagged and
retained for audit. Suspicious records are rejected with reasons in
`data/processed/rejected_records.csv`.

Validation checks required fields, city/category membership, source validity,
phone format, address structure, duplicate keys, dates, coordinates and audit
consistency. Blocking errors: **{int(pd.read_csv(REPORTS_DIR / 'validation_summary.csv').query("metric == 'error_count'")['value'].iloc[0]) if (REPORTS_DIR / 'validation_summary.csv').exists() else 'pending'}**.

## 4. Key observations

- Largest city representation: **{top_city['city'] if top_city is not None else 'n/a'}**
  with **{int(top_city['listing_count']) if top_city is not None else 0:,}** records
  ({top_city['share_pct'] if top_city is not None else 0:.1f}% of the sample).
- Smallest city representation: **{bottom_city['city'] if bottom_city is not None else 'n/a'}**
  with **{int(bottom_city['listing_count']) if bottom_city is not None else 0:,}** records.
- Most common category: **{top_category['category'] if top_category is not None else 'n/a'}**
  with **{int(top_category['listing_count']) if top_category is not None else 0:,}** records
  ({top_category['share_pct'] if top_category is not None else 0:.1f}%).
- Least represented category: **{low_category['category'] if low_category is not None else 'n/a'}**
  with **{int(low_category['listing_count']) if low_category is not None else 0:,}** records.
- Missing phone: **{int(summary.get('missing_phone_count', 0)):,}**
  ({summary.get('missing_phone_pct', 0):.2f}%).
- Missing address: **{int(summary.get('missing_address_count', 0)):,}**
  ({summary.get('missing_address_pct', 0):.2f}%).
- Duplicate rate: **{summary.get('duplicate_rate_pct', 0):.2f}%**.
- Completeness (phone + address + not duplicate): **{summary.get('completeness_pct', 0):.2f}%**.
- Covered city-category pairs: **{int(summary.get('covered_city_category_pairs', 0))}** of
  **{int(summary.get('possible_city_category_pairs', 0))}** possible
  ({100 * int(summary.get('covered_city_category_pairs', 0)) / max(1, int(summary.get('possible_city_category_pairs', 1))):.1f}%).

## 5. City distribution

{markdown_table(city[['city', 'state_name', 'listing_count', 'share_pct', 'categories_present', 'completeness_pct', 'avg_quality_score']])}

## 6. Category distribution

{markdown_table(category[['category', 'listing_count', 'share_pct', 'cities_present', 'completeness_pct', 'avg_quality_score']])}

## 7. Source distribution

{markdown_table(source[['source', 'source_type', 'listing_count', 'share_pct', 'missing_phone_pct', 'missing_address_pct', 'completeness_pct']])}

The dataset contains one source. Source comparisons are therefore descriptive,
not comparative; see `docs/limitations.md`.

## 8. Findings and interpretation

1. **City coverage is broad in this extract.** The largest city contributes
   {top_city['share_pct'] if top_city is not None else 0:.1f}% of records;
   the smallest contributes
   {bottom_city['share_pct'] if bottom_city is not None else 0:.1f}%. The
   even spread reflects the consistent collection frame and caps, not relative
   market size.
2. **Contact data is the binding constraint.** Phone is missing for
   {summary.get('missing_phone_pct', 0):.1f}% and address for
   {summary.get('missing_address_pct', 0):.1f}% of records. This limits the
   reliability of any contactability conclusion and explains the low
   completeness rate.
3. **Category mix is uneven.** The largest category is
   **{top_category['category'] if top_category is not None else 'n/a'}** with
   **{int(top_category['listing_count']) if top_category is not None else 0:,}**
   records ({top_category['share_pct'] if top_category is not None else 0:.1f}%).
   A few consumer-facing categories dominate the visible sample; specialist
   categories are thinner. This reflects public mapping visibility, not market
   size.
4. **City-category gaps are candidates for research only.** Zero or low counts
   in a city-category cell indicate underrepresentation in this collected
   sample. They do not establish low competition or unmet demand.

## 9. Figures

{figure_lines}

## 10. Limitations

- OpenStreetMap is crowd-sourced and unevenly maintained; a missing field is
  not evidence that a business lacks a phone or address.
- The snapshot contains one collection date, so time-trend analysis is not
  meaningful.
- One source prevents source-adjusted comparisons.
- Bounding boxes may include neighbouring urban areas.
- Category mapping is rule-based and may merge distinct business models.
"""
    REPORT_DIR = REPORTS_DIR
    report_path = REPORT_DIR / "eda_report.md"
    report_path.write_text(report, encoding="utf-8")
    docs_path = ROOT / "docs" / "eda_report.md"
    docs_report = report.replace(
        f"]({figure_prefix}/", "](../data/reports/figures/"
    ) if figure_prefix == "figures" else report
    docs_path.write_text(docs_report, encoding="utf-8")
    return str(report_path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run BusinessPulse EDA")
    parser.add_argument("--input", default=str(CLEANED_CSV))
    args = parser.parse_args()
    ensure_directories()
    df = pd.read_csv(args.input, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    df["quality_score"] = pd.to_numeric(df["quality_score"], errors="coerce").fillna(0)
    tables = build_tables(df)
    tables["summary"].to_csv(REPORTS_DIR / "eda_summary.csv", index=False, encoding="utf-8")
    tables["city"].to_csv(REPORTS_DIR / "city_distribution.csv", index=False, encoding="utf-8")
    tables["category"].to_csv(REPORTS_DIR / "category_distribution.csv", index=False, encoding="utf-8")
    tables["source"].to_csv(REPORTS_DIR / "source_distribution.csv", index=False, encoding="utf-8")
    tables["pair"].to_csv(REPORTS_DIR / "city_category_counts.csv", index=False, encoding="utf-8")
    tables["quality_band"].to_csv(REPORTS_DIR / "quality_band_distribution.csv", index=False, encoding="utf-8")
    tables["status"].to_csv(REPORTS_DIR / "validation_status_distribution.csv", index=False, encoding="utf-8")
    tables["missing"].to_csv(REPORTS_DIR / "missing_values_summary.csv", index=False, encoding="utf-8")
    tables["city"].to_csv(REPORTS_DIR / "completeness_by_city.csv", index=False, encoding="utf-8")
    tables["category"].to_csv(REPORTS_DIR / "completeness_by_category.csv", index=False, encoding="utf-8")
    figures = build_figures(df, tables)
    report_path = write_report(df, tables, figures, figure_prefix="figures")
    print(f"EDA tables written to {REPORTS_DIR}")
    print(f"Figures: {len(figures)}")
    print(f"Report: {report_path}")


if __name__ == "__main__":
    main()
