"""Run the reproducible cleaning pipeline and write audit deliverables."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from analytics.cleaning.cleaning import clean_dataframe, is_blank  # noqa: E402
from analytics.constants import (  # noqa: E402
    CLEANED_CSV,
    CLEANING_LOG_CSV,
    DUPLICATES_CSV,
    MISSING_VALUES_CSV,
    POTENTIAL_DUPLICATES_CSV,
    QUALITY_SUMMARY_CSV,
    RAW_CSV,
    REJECTED_CSV,
    SAMPLE_DIR,
    ensure_directories,
)


def missing_report(raw: pd.DataFrame, cleaned: pd.DataFrame) -> pd.DataFrame:
    fields = [
        "business_id",
        "business_name",
        "category",
        "city",
        "address",
        "phone",
        "source",
        "source_record_id",
        "collection_date",
        "created_at",
        "latitude",
        "longitude",
    ]
    rows: list[dict] = []
    for dataset, frame in (("raw", raw), ("cleaned", cleaned)):
        for field in fields:
            if field not in frame.columns:
                continue
            count = int(frame[field].map(is_blank).sum())
            rows.append(
                {
                    "dataset": dataset,
                    "field": field,
                    "missing_count": count,
                    "total_rows": len(frame),
                    "missing_pct": round(100 * count / len(frame), 2) if len(frame) else 0.0,
                }
            )
    return pd.DataFrame(rows)


def quality_summary(raw: pd.DataFrame, cleaned: pd.DataFrame, rejected: pd.DataFrame, duplicates: pd.DataFrame) -> pd.DataFrame:
    total = len(cleaned)
    missing_phone = int(cleaned["missing_phone"].sum()) if total else 0
    missing_address = int(cleaned["missing_address"].sum()) if total else 0
    invalid_phone = int(((~cleaned["phone_valid"]) & (~cleaned["missing_phone"])).sum()) if total else 0
    invalid_address = int(((~cleaned["address_valid"]) & (~cleaned["missing_address"])).sum()) if total else 0
    complete = int(cleaned["is_complete"].sum()) if total else 0
    duplicate_count = int(cleaned["duplicate_flag"].sum()) if total else 0
    potential_count = int(cleaned["potential_duplicate_flag"].sum()) if total else 0
    valid = int((cleaned["validation_status"] == "valid").sum()) if total else 0
    needs_review = int((cleaned["validation_status"] == "needs_review").sum()) if total else 0
    metrics = [
        ("raw_records", len(raw), "Rows in the preserved raw extract"),
        ("cleaned_records", total, "Rows retained after cleaning and validation"),
        ("rejected_records", len(rejected), "Rows rejected with a documented reason"),
        ("duplicate_records", duplicate_count, "Exact duplicates flagged and retained for audit"),
        ("potential_duplicate_records", potential_count, "Potential duplicates flagged for review only"),
        ("duplicate_rate_pct", round(100 * duplicate_count / total, 2) if total else 0.0, "Exact duplicates / cleaned records"),
        ("missing_phone_count", missing_phone, "Cleaned records with no phone"),
        ("missing_phone_pct", round(100 * missing_phone / total, 2) if total else 0.0, "Missing phone / cleaned records"),
        ("missing_address_count", missing_address, "Cleaned records with no address"),
        ("missing_address_pct", round(100 * missing_address / total, 2) if total else 0.0, "Missing address / cleaned records"),
        ("invalid_phone_count", invalid_phone, "Present phones outside the 7-15 digit rule"),
        ("invalid_address_count", invalid_address, "Present addresses that are too short/unstructured"),
        ("complete_listings", complete, "Rows meeting the documented completeness rule"),
        ("completeness_pct", round(100 * complete / total, 2) if total else 0.0, "Complete / cleaned records"),
        ("valid_listings", valid, "Audit status = valid"),
        ("needs_review_listings", needs_review, "Audit status = needs_review"),
        ("avg_quality_score", round(float(cleaned["quality_score"].mean()), 2) if total else 0.0, "Mean of the documented 0-100 score"),
        ("median_quality_score", round(float(cleaned["quality_score"].median()), 2) if total else 0.0, "Median quality score"),
        ("distinct_cities", int(cleaned["city"].nunique()) if total else 0, "Cities represented"),
        ("distinct_categories", int(cleaned["category"].nunique()) if total else 0, "Categories represented"),
        ("distinct_sources", int(cleaned["source"].nunique()) if total else 0, "Sources represented"),
        ("collection_date", cleaned["collection_date"].mode().iloc[0] if total else "", "Snapshot collection date"),
    ]
    for band in ("High (80-100)", "Medium (60-79)", "Low (<60)"):
        metrics.append(
            (
                f"quality_band_{band}",
                int((cleaned["quality_score"].apply(
                    lambda score: "High (80-100)" if score >= 80 else "Medium (60-79)" if score >= 60 else "Low (<60)"
                ) == band).sum()) if total else 0,
                "Records in this quality band",
            )
        )
    return pd.DataFrame(metrics, columns=["metric", "value", "definition"])


def main() -> None:
    parser = argparse.ArgumentParser(description="Clean and validate BusinessPulse raw listings")
    parser.add_argument("--raw", default=str(RAW_CSV))
    parser.add_argument("--output", default=str(CLEANED_CSV))
    args = parser.parse_args()

    ensure_directories()
    raw_path = Path(args.raw)
    if not raw_path.exists():
        raise SystemExit(f"Raw file not found: {raw_path}. Run data collection first.")

    raw = pd.read_csv(raw_path, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    print(f"Loaded {len(raw)} raw records from {raw_path}")

    result = clean_dataframe(raw, collection_date_fallback=os.getenv("COLLECTION_DATE"))
    cleaned = result.cleaned
    rejected = result.rejected
    duplicates = result.duplicates
    potential = result.potential_duplicates
    if rejected.empty and not len(rejected.columns):
        rejected = pd.DataFrame(
            columns=[
                "business_id", "business_name", "city", "category", "source",
                "source_record_id", "rejection_reason", "raw_record", "rejected_at",
            ]
        )
    if duplicates.empty and not len(duplicates.columns):
        duplicates = pd.DataFrame(
            columns=[
                "business_id", "business_name", "city", "address", "phone", "source",
                "source_record_id", "duplicate_group", "kept_business_id", "duplicate_reason",
            ]
        )
    if potential.empty and not len(potential.columns):
        potential = pd.DataFrame(
            columns=[
                "business_id", "business_name", "city", "address", "other_business_id",
                "other_address", "address_similarity", "phone_a", "phone_b",
            ]
        )

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cleaned.to_csv(output_path, index=False, encoding="utf-8")
    rejected.to_csv(REJECTED_CSV, index=False, encoding="utf-8")
    duplicates.to_csv(DUPLICATES_CSV, index=False, encoding="utf-8")
    potential.to_csv(POTENTIAL_DUPLICATES_CSV, index=False, encoding="utf-8")
    result.log.to_csv(CLEANING_LOG_CSV, index=False, encoding="utf-8")
    missing_report(raw, cleaned).to_csv(MISSING_VALUES_CSV, index=False, encoding="utf-8")
    quality_summary(raw, cleaned, rejected, duplicates).to_csv(
        QUALITY_SUMMARY_CSV, index=False, encoding="utf-8"
    )

    # A small, clearly-labelled subset for quick review. This is not a second
    # dataset; it is sampled from the cleaned data.
    sample = (
        cleaned.sort_values(["city", "category", "business_name"])
        .groupby("city", group_keys=False)
        .head(5)
        .reset_index(drop=True)
    )
    sample.to_csv(SAMPLE_DIR / "business_listings_sample.csv", index=False, encoding="utf-8")

    print(f"Cleaned records: {len(cleaned)}")
    print(f"Rejected records: {len(rejected)}")
    print(f"Exact duplicates flagged: {int(cleaned['duplicate_flag'].sum()) if len(cleaned) else 0}")
    print(f"Potential duplicates flagged: {int(cleaned['potential_duplicate_flag'].sum()) if len(cleaned) else 0}")
    print(f"Missing phone: {int(cleaned['missing_phone'].sum()) if len(cleaned) else 0}")
    print(f"Missing address: {int(cleaned['missing_address'].sum()) if len(cleaned) else 0}")
    print(f"Complete listings: {int(cleaned['is_complete'].sum()) if len(cleaned) else 0}")
    print(f"Written: {output_path}")
    print(f"Quality summary: {QUALITY_SUMMARY_CSV}")


if __name__ == "__main__":
    main()
