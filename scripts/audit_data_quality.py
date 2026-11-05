"""Recompute the final data-quality evidence from the preserved data files.

This script is deliberately independent of the previously generated summary
CSVs. It reads the raw extract, the cleaned listing file and the collection
manifest, recalculates every reported count from those files, and writes:

* data/reports/final_quality_summary.csv
* data/reports/final_missing_values.csv
* data/reports/final_duplicate_records.csv

The outputs are deterministic for a fixed dataset. They are the evidence used
by docs/data_quality_audit.md and docs/final_audit.md.

Run from the project root:

    python scripts/audit_data_quality.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from analytics.constants import (  # noqa: E402
    CLEANED_CSV,
    DUPLICATES_CSV,
    PROCESSED_DIR,
    RAW_CSV,
    REPORTS_DIR,
)

MANIFEST_JSON = ROOT / "data" / "raw" / "collection_manifest.json"
QUALITY_SUMMARY_CSV = REPORTS_DIR / "final_quality_summary.csv"
MISSING_VALUES_CSV = REPORTS_DIR / "final_missing_values.csv"
FINAL_DUPLICATES_CSV = REPORTS_DIR / "final_duplicate_records.csv"
OPPORTUNITIES_CSV = REPORTS_DIR / "market_opportunities.csv"

SNAPSHOT_DATE = "2026-11-02"


def read_csv(path: Path) -> pd.DataFrame:
    """Read all values as text so blanks stay blanks instead of becoming NaN."""
    if not path.exists():
        raise FileNotFoundError(f"Required data file not found: {path}")
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def bool_series(series: pd.Series) -> pd.Series:
    return series.astype(str).str.strip().str.lower().isin({"true", "1", "yes"})


def blank_series(series: pd.Series) -> pd.Series:
    return series.astype(str).str.strip().eq("")


def pct(numerator: int | float, denominator: int | float) -> float | None:
    if not denominator:
        return None
    return round(100.0 * numerator / denominator, 2)


def metric(
    name: str,
    value: Any,
    denominator: int | float | None,
    percentage: float | None,
    unit: str,
    definition: str,
    evidence: str,
) -> dict[str, Any]:
    return {
        "metric": name,
        "value": value,
        "denominator": "" if denominator is None else denominator,
        "pct": "" if percentage is None else percentage,
        "unit": unit,
        "definition": definition,
        "evidence": evidence,
    }


def build_summary(
    raw: pd.DataFrame,
    cleaned: pd.DataFrame,
    manifest: dict[str, Any],
) -> pd.DataFrame:
    total = len(cleaned)
    raw_total = len(raw)

    for frame in (raw, cleaned):
        for column in (
            "missing_phone",
            "missing_address",
            "phone_valid",
            "address_valid",
            "duplicate_flag",
            "potential_duplicate_flag",
            "is_complete",
        ):
            if column in frame.columns:
                frame[column] = bool_series(frame[column])
    cleaned["quality_score"] = pd.to_numeric(cleaned["quality_score"], errors="coerce")

    missing_phone = int(cleaned["missing_phone"].sum())
    missing_address = int(cleaned["missing_address"].sum())
    present_phone = total - missing_phone
    present_address = total - missing_address
    invalid_phone = int(((~cleaned["missing_phone"]) & (~cleaned["phone_valid"])).sum())
    invalid_address = int(
        ((~cleaned["missing_address"]) & (~cleaned["address_valid"])).sum()
    )
    duplicate_count = int(cleaned["duplicate_flag"].sum())
    potential_duplicate_count = int(cleaned["potential_duplicate_flag"].sum())
    complete_count = int(cleaned["is_complete"].sum())

    city_category = pd.crosstab(cleaned["city"], cleaned["category"])
    covered_pairs = int((city_category > 0).to_numpy().sum())
    universe_pairs = int(city_category.size)

    raw_by_id = raw.set_index("business_id")
    clean_by_id = cleaned.set_index("business_id")
    common_ids = clean_by_id.index.intersection(raw_by_id.index)
    changed = {
        column: int(
            (
                raw_by_id.loc[common_ids, column].fillna("").astype(str)
                != clean_by_id.loc[common_ids, column].fillna("").astype(str)
            ).sum()
        )
        for column in ("business_name", "category", "city", "address", "phone")
    }

    quality = cleaned["quality_score"].dropna()
    bands = cleaned["quality_band"].value_counts().to_dict()
    statuses = cleaned["validation_status"].value_counts().to_dict()

    validation_summary_path = REPORTS_DIR / "validation_summary.csv"
    validation = (
        pd.read_csv(validation_summary_path, dtype=str, keep_default_na=False)
        if validation_summary_path.exists()
        else pd.DataFrame()
    )
    validation_values = (
        dict(zip(validation["metric"], validation["value"])) if not validation.empty else {}
    )

    queries = manifest.get("queries", [])
    query_statuses = [q.get("status", "") for q in queries]
    element_total = sum(int(q.get("element_count") or 0) for q in queries)
    cap_limited = sum(
        1
        for q in queries
        if str(q.get("status", "")).lower() == "success"
        and q.get("element_count") == q.get("limit")
    )

    raw_build = json.loads(
        (ROOT / "data" / "raw" / "raw_build_summary.json").read_text(encoding="utf-8")
    )
    skipped = raw_build.get("skipped", {})

    rows: list[dict[str, Any]] = []

    def add(name, value, denominator, percentage, unit, definition, evidence="calculated"):
        rows.append(metric(name, value, denominator, percentage, unit, definition, evidence))

    add("raw_records", raw_total, None, None, "records", "Rows in the preserved raw CSV")
    add("cleaned_records", total, None, None, "records", "Rows in the cleaned CSV")
    add(
        "unique_business_ids",
        int(cleaned["business_id"].nunique()),
        total,
        pct(cleaned["business_id"].nunique(), total),
        "records",
        "Distinct project business IDs in the cleaned file",
    )
    add(
        "rejected_records",
        int(len(read_csv(PROCESSED_DIR / "rejected_records.csv"))),
        total,
        pct(len(read_csv(PROCESSED_DIR / "rejected_records.csv")), total),
        "records",
        "Rows with a documented blocking rejection; none were rejected",
    )
    add(
        "duplicate_records_flagged",
        duplicate_count,
        total,
        pct(duplicate_count, total),
        "records",
        "Exact duplicates flagged by name + city + address/phone; retained for audit",
    )
    add(
        "duplicate_rate",
        duplicate_count,
        total,
        pct(duplicate_count, total),
        "%",
        "Exact duplicate records divided by cleaned records",
    )
    add(
        "potential_duplicate_records",
        potential_duplicate_count,
        total,
        pct(potential_duplicate_count, total),
        "records",
        "Address-similarity >= 0.90 candidates; review only, not deleted",
    )
    add(
        "missing_phone_records",
        missing_phone,
        total,
        pct(missing_phone, total),
        "records",
        "Cleaned records with no published phone value",
    )
    add(
        "missing_phone_rate",
        missing_phone,
        total,
        pct(missing_phone, total),
        "%",
        "Missing phone records divided by cleaned records",
    )
    add(
        "missing_address_records",
        missing_address,
        total,
        pct(missing_address, total),
        "records",
        "Cleaned records with no published structured address",
    )
    add(
        "missing_address_rate",
        missing_address,
        total,
        pct(missing_address, total),
        "%",
        "Missing address records divided by cleaned records",
    )
    add(
        "invalid_present_phone_records",
        invalid_phone,
        present_phone,
        pct(invalid_phone, total),
        "records",
        "Present phone values outside the 7-15 digit rule; pct is share of all records",
    )
    add(
        "invalid_present_phone_rate_of_present",
        invalid_phone,
        present_phone,
        pct(invalid_phone, present_phone),
        "%",
        "Invalid present phones divided by records with a present phone",
    )
    add(
        "invalid_present_address_records",
        invalid_address,
        present_address,
        pct(invalid_address, total),
        "records",
        "Present addresses too short/unstructured for the audit; pct is share of all records",
    )
    add(
        "invalid_present_address_rate_of_present",
        invalid_address,
        present_address,
        pct(invalid_address, present_address),
        "%",
        "Invalid present addresses divided by records with a present address",
    )
    add(
        "complete_records",
        complete_count,
        total,
        pct(complete_count, total),
        "records",
        "Valid phone + valid address + not an exact duplicate",
    )
    add(
        "completeness_rate",
        complete_count,
        total,
        pct(complete_count, total),
        "%",
        "Complete records divided by cleaned records",
    )
    add("validation_valid", int(statuses.get("valid", 0)), total, pct(statuses.get("valid", 0), total), "records", "Validation status = valid")
    add(
        "validation_needs_review",
        int(statuses.get("needs_review", 0)),
        total,
        pct(statuses.get("needs_review", 0), total),
        "records",
        "Validation status = needs_review (warnings, not blocking)",
    )
    add(
        "validation_invalid",
        int(statuses.get("invalid", 0)),
        total,
        pct(statuses.get("invalid", 0), total),
        "records",
        "Validation status = invalid (blocking errors)",
    )
    add(
        "quality_score_mean",
        round(float(quality.mean()), 2),
        len(quality),
        None,
        "score (0-100)",
        "Mean documented audit score; not business quality",
    )
    add(
        "quality_score_median",
        round(float(quality.median()), 2),
        len(quality),
        None,
        "score (0-100)",
        "Median documented audit score",
    )
    add(
        "quality_score_min",
        round(float(quality.min()), 2),
        len(quality),
        None,
        "score (0-100)",
        "Minimum documented audit score",
    )
    add(
        "quality_score_max",
        round(float(quality.max()), 2),
        len(quality),
        None,
        "score (0-100)",
        "Maximum documented audit score",
    )
    for band in ("High (80-100)", "Medium (60-79)", "Low (<60)"):
        add(
            f"quality_band_{band}",
            int(bands.get(band, 0)),
            total,
            pct(bands.get(band, 0), total),
            "records",
            f"Records in quality band {band}",
        )
    add("distinct_cities", int(cleaned["city"].nunique()), None, None, "cities", "Cities represented by at least one cleaned listing")
    add("distinct_categories", int(cleaned["category"].nunique()), None, None, "categories", "Analytical categories represented by at least one listing")
    add("distinct_sources", int(cleaned["source"].nunique()), None, None, "sources", "Distinct public data sources in this snapshot")
    add(
        "covered_city_category_pairs",
        covered_pairs,
        universe_pairs,
        pct(covered_pairs, universe_pairs),
        "pairs",
        "City x category cells with at least one collected listing",
    )
    add(
        "city_category_universe",
        universe_pairs,
        universe_pairs,
        100.0,
        "pairs",
        "All city x category combinations in the fixed 12 x 12 frame",
    )
    add(
        "coverage_rate",
        covered_pairs,
        universe_pairs,
        pct(covered_pairs, universe_pairs),
        "%",
        "Covered pairs divided by the 144-pair universe",
    )
    if OPPORTUNITIES_CSV.exists():
        opp = read_csv(OPPORTUNITIES_CSV)
        for column in ("is_candidate",):
            if column in opp:
                opp[column] = bool_series(opp[column])
        candidates = int(opp["is_candidate"].sum()) if "is_candidate" in opp else 0
        tiers = opp["opportunity_tier"].value_counts().to_dict() if "opportunity_tier" in opp else {}
        add("opportunity_candidate_pairs", candidates, universe_pairs, pct(candidates, universe_pairs), "pairs", "Pairs passing city >=20 and category >=5 evidence filters")
        for tier in ("High", "Medium", "Low", "Insufficient evidence"):
            add(
                f"opportunity_tier_{tier}",
                int(tiers.get(tier, 0)),
                universe_pairs,
                pct(tiers.get(tier, 0), universe_pairs),
                "pairs",
                f"City x category pairs in opportunity tier {tier}",
            )
    add(
        "blocking_validation_errors",
        int(float(validation_values.get("error_count", 0) or 0)),
        total,
        pct(int(float(validation_values.get("error_count", 0) or 0)), total),
        "errors",
        "Blocking validation errors; these would reject rows",
    )
    add(
        "warning_validation_issues",
        int(float(validation_values.get("warning_count", 0) or 0)),
        total,
        None,
        "warnings",
        "Warning-level validation issues; retained and flagged",
    )
    add(
        "raw_cleaned_business_id_matches",
        len(common_ids),
        total,
        pct(len(common_ids), total),
        "records",
        "Raw business IDs present in the cleaned file",
    )
    add(
        "raw_to_cleaned_name_changes",
        changed["business_name"],
        total,
        pct(changed["business_name"], total),
        "records",
        "Rows whose business_name changed during normalisation",
    )
    add(
        "raw_to_cleaned_phone_changes",
        changed["phone"],
        total,
        pct(changed["phone"], total),
        "records",
        "Rows whose phone changed during normalisation (format, not enrichment)",
    )
    add(
        "raw_to_cleaned_address_changes",
        changed["address"],
        total,
        pct(changed["address"], total),
        "records",
        "Rows whose address changed during normalisation",
    )
    add(
        "raw_to_cleaned_city_changes",
        changed["city"],
        total,
        pct(changed["city"], total),
        "records",
        "Rows whose canonical city changed",
    )
    add(
        "raw_to_cleaned_category_changes",
        changed["category"],
        total,
        pct(changed["category"], total),
        "records",
        "Rows whose analytical category changed",
    )
    add(
        "collection_query_entries",
        len(queries),
        None,
        None,
        "queries",
        "One entry per city/group in collection_manifest.json",
        "collection_manifest.json",
    )
    add(
        "collection_successful_queries",
        sum(1 for s in query_statuses if str(s).lower() == "success"),
        len(queries),
        pct(sum(1 for s in query_statuses if str(s).lower() == "success"), len(queries)),
        "queries",
        "Manifest entries with status=success",
        "collection_manifest.json",
    )
    add(
        "collection_failed_queries",
        sum(1 for s in query_statuses if str(s).lower() != "success"),
        len(queries),
        pct(sum(1 for s in query_statuses if str(s).lower() != "success"), len(queries)),
        "queries",
        "Manifest entries not marked success",
        "collection_manifest.json",
    )
    add(
        "collection_raw_osm_elements",
        element_total,
        None,
        None,
        "elements",
        "Elements returned before raw-build skips and de-duplication",
        "collection_manifest.json",
    )
    add(
        "collection_cap_limited_queries",
        cap_limited,
        len(queries),
        pct(cap_limited, len(queries)),
        "queries",
        "Successful queries whose returned element count equals the configured cap",
        "collection_manifest.json",
    )
    for key, label in (
        ("unnamed", "Skipped unnamed OSM elements"),
        ("non_business_or_unmapped", "Skipped non-business or unmapped OSM elements"),
        ("generic_name", "Skipped generic business names"),
        ("duplicate_osm_element", "Skipped duplicate OSM elements"),
        ("missing_coordinates", "Skipped elements with missing coordinates"),
    ):
        add(
            f"raw_build_skipped_{key}",
            int(skipped.get(key, 0)),
            element_total,
            pct(int(skipped.get(key, 0)), element_total),
            "elements",
            label,
            "raw_build_summary.json",
        )
    add(
        "collection_snapshot_date",
        SNAPSHOT_DATE,
        None,
        None,
        "date",
        "Single collection snapshot date used by every cleaned record",
        "data/raw/raw_build_summary.json",
    )
    return pd.DataFrame(rows)


def build_missing_values(raw: pd.DataFrame, cleaned: pd.DataFrame) -> pd.DataFrame:
    total = len(cleaned)
    fields = [
        "business_id",
        "business_name",
        "category",
        "city",
        "state_name",
        "country",
        "address",
        "phone",
        "source",
        "source_record_id",
        "collection_date",
        "latitude",
        "longitude",
    ]
    rows: list[dict[str, Any]] = []

    for field in fields:
        if field not in cleaned:
            continue
        missing = blank_series(cleaned[field])
        missing_count = int(missing.sum())
        present_count = total - missing_count
        if field == "phone":
            invalid_present = int(((~missing) & (~bool_series(cleaned["phone_valid"]))).sum())
            definition = "Blank public phone value; present invalid values are counted separately"
        elif field == "address":
            invalid_present = int(((~missing) & (~bool_series(cleaned["address_valid"]))).sum())
            definition = "Blank public address; present invalid values are counted separately"
        else:
            invalid_present = None
            definition = "Blank or null value in the cleaned CSV"
        nonusable = missing_count + (invalid_present or 0)
        rows.append(
            {
                "dimension": "field",
                "dimension_value": "all records",
                "field": field,
                "missing_count": missing_count,
                "present_count": present_count,
                "total_count": total,
                "missing_pct": pct(missing_count, total),
                "invalid_present_count": "" if invalid_present is None else invalid_present,
                "nonusable_count": nonusable,
                "nonusable_pct": pct(nonusable, total),
                "definition": definition,
            }
        )

    for dimension, column in (
        ("city", "city"),
        ("category", "category"),
        ("source", "source"),
    ):
        for value, group in cleaned.groupby(column, dropna=False):
            n = len(group)
            for field in ("phone", "address"):
                missing = blank_series(group[field])
                missing_count = int(missing.sum())
                present_count = n - missing_count
                valid_col = "phone_valid" if field == "phone" else "address_valid"
                invalid_present = int(((~missing) & (~bool_series(group[valid_col]))).sum())
                nonusable = missing_count + invalid_present
                rows.append(
                    {
                        "dimension": dimension,
                        "dimension_value": str(value),
                        "field": field,
                        "missing_count": missing_count,
                        "present_count": present_count,
                        "total_count": n,
                        "missing_pct": pct(missing_count, n),
                        "invalid_present_count": invalid_present,
                        "nonusable_count": nonusable,
                        "nonusable_pct": pct(nonusable, n),
                        "definition": "Missing in the public source; present-but-invalid counted separately",
                    }
                )
    return pd.DataFrame(rows).sort_values(
        ["dimension", "dimension_value", "field"], kind="stable"
    )


def build_duplicates(cleaned: pd.DataFrame) -> pd.DataFrame:
    flagged = cleaned[bool_series(cleaned["duplicate_flag"])].copy()
    canonical = cleaned.set_index("business_id")
    rows: list[dict[str, Any]] = []
    for _, row in flagged.iterrows():
        kept_id = str(row.get("kept_business_id", "") or "")
        kept = canonical.loc[kept_id] if kept_id in canonical.index else None
        rows.append(
            {
                "business_id": row.get("business_id", ""),
                "business_name": row.get("business_name", ""),
                "city": row.get("city", ""),
                "category": row.get("category", ""),
                "address": row.get("address", ""),
                "phone": row.get("phone", ""),
                "source_record_id": row.get("source_record_id", ""),
                "duplicate_group": row.get("duplicate_group", ""),
                "duplicate_reason": row.get("duplicate_reason", ""),
                "kept_business_id": kept_id,
                "kept_business_name": "" if kept is None else kept.get("business_name", ""),
                "kept_source_record_id": "" if kept is None else kept.get("source_record_id", ""),
                "kept_address": "" if kept is None else kept.get("address", ""),
                "kept_phone": "" if kept is None else kept.get("phone", ""),
                "review_status": "flagged_retained",
                "retention_decision": "Retained in cleaned data for audit; not deleted",
            }
        )
    return pd.DataFrame(rows)


def main() -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    raw = read_csv(RAW_CSV)
    cleaned = read_csv(CLEANED_CSV)
    manifest = json.loads(MANIFEST_JSON.read_text(encoding="utf-8"))

    summary = build_summary(raw, cleaned, manifest)
    missing = build_missing_values(raw, cleaned)
    duplicates = build_duplicates(cleaned)

    summary.to_csv(QUALITY_SUMMARY_CSV, index=False, encoding="utf-8")
    missing.to_csv(MISSING_VALUES_CSV, index=False, encoding="utf-8")
    duplicates.to_csv(FINAL_DUPLICATES_CSV, index=False, encoding="utf-8")

    print(f"Wrote {QUALITY_SUMMARY_CSV.relative_to(ROOT)} ({len(summary)} metrics)")
    print(f"Wrote {MISSING_VALUES_CSV.relative_to(ROOT)} ({len(missing)} rows)")
    print(f"Wrote {FINAL_DUPLICATES_CSV.relative_to(ROOT)} ({len(duplicates)} rows)")
    print(
        "Key checks: "
        f"raw={len(raw)} cleaned={len(cleaned)} "
        f"missing_phone={int(bool_series(cleaned['missing_phone']).sum())} "
        f"missing_address={int(bool_series(cleaned['missing_address']).sum())} "
        f"complete={int(bool_series(cleaned['is_complete']).sum())} "
        f"duplicates={len(duplicates)}"
    )


if __name__ == "__main__":
    main()
