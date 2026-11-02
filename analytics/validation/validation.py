"""Data validation checks with explicit severities and row-level evidence.

Blocking errors prevent a row from being imported. Warnings document quality
issues (for example a missing phone) but do not make a record unusable.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

import pandas as pd

from analytics.cleaning.cleaning import (
    is_blank,
    is_valid_address,
    is_valid_phone,
    normalize_category,
    normalize_city,
)
from analytics.constants import REQUIRED_FIELDS, SOURCE_NAME


@dataclass
class ValidationResult:
    issues: pd.DataFrame
    summary: dict[str, Any]
    blocking_indices: set[int]


ISSUE_COLUMNS = [
    "row_index",
    "business_id",
    "field",
    "issue_type",
    "severity",
    "message",
    "value",
]


def _issue(
    issues: list[dict[str, Any]],
    row_index: int,
    business_id: str,
    field: str,
    issue_type: str,
    severity: str,
    message: str,
    value: Any,
) -> None:
    issues.append(
        {
            "row_index": int(row_index),
            "business_id": business_id,
            "field": field,
            "issue_type": issue_type,
            "severity": severity,
            "message": message,
            "value": "" if is_blank(value) else str(value)[:500],
        }
    )


def _parse_date(value: Any) -> bool:
    if is_blank(value):
        return False
    try:
        pd.to_datetime(value)
        return True
    except (TypeError, ValueError):
        return False


def validate_dataframe(df: pd.DataFrame) -> ValidationResult:
    """Run required-field, format, duplicate, source and consistency checks."""
    issues: list[dict[str, Any]] = []
    if df.empty:
        return ValidationResult(
            issues=pd.DataFrame(columns=ISSUE_COLUMNS),
            summary={
                "rows_checked": 0,
                "error_count": 0,
                "warning_count": 0,
                "blocking_rows": 0,
            },
            blocking_indices=set(),
        )

    work = df.reset_index(drop=True).copy()

    # 1. Required fields
    for field in REQUIRED_FIELDS:
        if field not in work.columns:
            _issue(
                issues,
                0,
                "",
                field,
                "missing_column",
                "error",
                f"Required column {field} is absent",
                "",
            )
            continue
        for idx, value in work[field].items():
            if is_blank(value):
                _issue(
                    issues,
                    idx,
                    str(work.at[idx, "business_id"]) if "business_id" in work.columns else "",
                    field,
                    "required_missing",
                    "error",
                    f"Required field {field} is blank",
                    value,
                )

    # 2. City and category validity
    if "city" in work.columns:
        for idx, value in work["city"].items():
            if not is_blank(value) and normalize_city(value) is None:
                _issue(
                    issues, idx, str(work.at[idx, "business_id"]), "city",
                    "invalid_city", "error", f"City is not in the canonical city list: {value}", value,
                )
    if "category" in work.columns:
        for idx, value in work["category"].items():
            if not is_blank(value) and normalize_category(value) is None:
                _issue(
                    issues, idx, str(work.at[idx, "business_id"]), "category",
                    "invalid_category", "error", f"Category is not in the canonical category list: {value}", value,
                )

    # 3. Source validity
    if "source" in work.columns:
        for idx, value in work["source"].items():
            if str(value).strip() != SOURCE_NAME:
                _issue(
                    issues, idx, str(work.at[idx, "business_id"]), "source",
                    "invalid_source", "error", f"Unexpected source: {value}", value,
                )

    # 4. Phone availability and format
    for idx, row in work.iterrows():
        bid = str(row.get("business_id", ""))
        phone = row.get("phone", "")
        phone_raw = row.get("phone_raw", "") if "phone_raw" in work.columns else phone
        missing_phone = is_blank(phone)
        if missing_phone:
            _issue(issues, idx, bid, "phone", "missing_phone", "warning",
                   "Phone is missing; no number was invented", phone)
        elif not is_valid_phone(phone_raw):
            _issue(issues, idx, bid, "phone", "invalid_phone_format", "warning",
                   "Phone is present but does not match the 7-15 digit rule", phone_raw)

        address = row.get("address", "")
        missing_address = is_blank(address)
        if missing_address:
            _issue(issues, idx, bid, "address", "missing_address", "warning",
                   "Address is missing; no address was invented", address)
        elif not is_valid_address(address):
            _issue(issues, idx, bid, "address", "invalid_address", "warning",
                   "Address is present but too short/unstructured", address)

    # 5. Duplicate business IDs and source records
    if "business_id" in work.columns:
        duplicate_mask = work["business_id"].duplicated(keep="first")
        for idx in work.index[duplicate_mask]:
            _issue(issues, idx, str(work.at[idx, "business_id"]), "business_id",
                   "duplicate_business_id", "error",
                   "business_id occurs more than once; first occurrence kept", work.at[idx, "business_id"])
    if {"source", "source_record_id"}.issubset(work.columns):
        duplicate_mask = work.duplicated(["source", "source_record_id"], keep="first")
        for idx in work.index[duplicate_mask]:
            _issue(issues, idx, str(work.at[idx, "business_id"]), "source_record_id",
                   "duplicate_source_record", "error",
                   "source/source_record_id occurs more than once; first occurrence kept",
                   work.at[idx, "source_record_id"])

    # 6. Date and coordinate validation
    today = date.today()
    for idx, row in work.iterrows():
        bid = str(row.get("business_id", ""))
        if not _parse_date(row.get("collection_date")):
            _issue(issues, idx, bid, "collection_date", "invalid_date", "error",
                   "collection_date is missing or not a valid date", row.get("collection_date"))
        else:
            parsed = pd.to_datetime(row.get("collection_date")).date()
            if parsed > today + timedelta(days=1):
                _issue(issues, idx, bid, "collection_date", "future_date", "warning",
                       "collection_date is in the future", parsed)
        if not _parse_date(row.get("created_at")):
            _issue(issues, idx, bid, "created_at", "invalid_datetime", "error",
                   "created_at is missing or not a valid datetime", row.get("created_at"))
        for field, low, high in (("latitude", -90, 90), ("longitude", -180, 180)):
            if field not in work.columns:
                continue
            value = row.get(field)
            if is_blank(value):
                _issue(issues, idx, bid, field, "missing_coordinate", "warning",
                       f"{field} is missing; map placement unavailable", value)
                continue
            try:
                number = float(value)
                if not low <= number <= high:
                    raise ValueError
            except (TypeError, ValueError):
                _issue(issues, idx, bid, field, "invalid_coordinate", "error",
                       f"{field} is outside [{low}, {high}]", value)

    # 7. Audit consistency
    consistency_fields = [
        "missing_phone", "missing_address", "duplicate_flag", "phone_valid",
        "address_valid", "is_complete", "quality_score", "validation_status",
    ]
    present_audit = [f for f in consistency_fields if f in work.columns]
    for idx, row in work.iterrows():
        bid = str(row.get("business_id", ""))
        if "quality_score" in work.columns and not is_blank(row.get("quality_score")):
            try:
                score = float(row.get("quality_score"))
                if not 0 <= score <= 100:
                    _issue(issues, idx, bid, "quality_score", "invalid_score", "error",
                           "quality_score must be between 0 and 100", score)
            except (TypeError, ValueError):
                _issue(issues, idx, bid, "quality_score", "invalid_score", "error",
                       "quality_score is not numeric", row.get("quality_score"))
        if "is_complete" in work.columns and str(row.get("is_complete")).strip().lower() in {"true", "1"}:
            if (
                str(row.get("missing_phone")).strip().lower() in {"true", "1"}
                or str(row.get("missing_address")).strip().lower() in {"true", "1"}
                or str(row.get("duplicate_flag")).strip().lower() in {"true", "1"}
                or str(row.get("phone_valid")).strip().lower() in {"false", "0"}
                or str(row.get("address_valid")).strip().lower() in {"false", "0"}
            ):
                _issue(issues, idx, bid, "is_complete", "audit_inconsistency", "error",
                       "is_complete=True conflicts with missing/invalid/duplicate flags", "")
        if "validation_status" in work.columns:
            status = str(row.get("validation_status"))
            if status not in {"valid", "needs_review", "invalid"}:
                _issue(issues, idx, bid, "validation_status", "invalid_status", "error",
                       f"Unknown validation_status: {status}", status)
            if status == "valid" and "is_complete" in work.columns:
                if str(row.get("is_complete")).strip().lower() in {"false", "0"}:
                    _issue(issues, idx, bid, "validation_status", "audit_inconsistency", "warning",
                           "validation_status=valid but is_complete=False", status)

    issues_df = pd.DataFrame(issues, columns=ISSUE_COLUMNS)
    blocking_indices = set(
        int(value) for value in issues_df.loc[issues_df["severity"] == "error", "row_index"].unique()
    )
    error_count = int((issues_df["severity"] == "error").sum()) if not issues_df.empty else 0
    warning_count = int((issues_df["severity"] == "warning").sum()) if not issues_df.empty else 0
    total = len(work)
    missing_phone_count = int(
        work["missing_phone"].astype(str).str.lower().isin({"true", "1"}).sum()
    ) if "missing_phone" in work.columns else 0
    missing_address_count = int(
        work["missing_address"].astype(str).str.lower().isin({"true", "1"}).sum()
    ) if "missing_address" in work.columns else 0
    complete_count = int(
        work["is_complete"].astype(str).str.lower().isin({"true", "1"}).sum()
    ) if "is_complete" in work.columns else 0
    duplicate_count = int(
        work["duplicate_flag"].astype(str).str.lower().isin({"true", "1"}).sum()
    ) if "duplicate_flag" in work.columns else 0
    summary = {
        "rows_checked": total,
        "error_count": error_count,
        "warning_count": warning_count,
        "blocking_rows": len(blocking_indices),
        "missing_phone_count": missing_phone_count,
        "missing_phone_pct": round(100 * missing_phone_count / total, 2) if total else 0.0,
        "missing_address_count": missing_address_count,
        "missing_address_pct": round(100 * missing_address_count / total, 2) if total else 0.0,
        "complete_listings": complete_count,
        "completeness_pct": round(100 * complete_count / total, 2) if total else 0.0,
        "duplicate_listings": duplicate_count,
        "duplicate_rate_pct": round(100 * duplicate_count / total, 2) if total else 0.0,
        "invalid_phone_count": int((issues_df["issue_type"] == "invalid_phone_format").sum())
        if not issues_df.empty else 0,
        "invalid_address_count": int((issues_df["issue_type"] == "invalid_address").sum())
        if not issues_df.empty else 0,
        "invalid_city_count": int((issues_df["issue_type"] == "invalid_city").sum())
        if not issues_df.empty else 0,
        "invalid_category_count": int((issues_df["issue_type"] == "invalid_category").sum())
        if not issues_df.empty else 0,
        "invalid_source_count": int((issues_df["issue_type"] == "invalid_source").sum())
        if not issues_df.empty else 0,
        "duplicate_business_id_count": int((issues_df["issue_type"] == "duplicate_business_id").sum())
        if not issues_df.empty else 0,
        "duplicate_source_record_count": int((issues_df["issue_type"] == "duplicate_source_record").sum())
        if not issues_df.empty else 0,
    }
    return ValidationResult(issues=issues_df, summary=summary, blocking_indices=blocking_indices)
