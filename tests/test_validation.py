"""Unit tests for validation severities and audit consistency."""

from __future__ import annotations

import pandas as pd

from analytics.validation.validation import validate_dataframe
from tests.conftest import make_raw_row


def validation_frame(**overrides) -> pd.DataFrame:
    row = make_raw_row()
    row.update(
        {
            "phone": "+919876543210",
            "phone_raw": "+91 98765 43210",
            "address": "12 MG Road, Pune",
            "missing_phone": False,
            "missing_address": False,
            "duplicate_flag": False,
            "potential_duplicate_flag": False,
            "phone_valid": True,
            "address_valid": True,
            "is_complete": True,
            "validation_status": "valid",
            "quality_score": 100,
        }
    )
    row.update(overrides)
    return pd.DataFrame([row])


class TestValidation:
    def test_clean_row_has_no_errors(self):
        result = validate_dataframe(validation_frame())
        assert result.summary["rows_checked"] == 1
        assert result.summary["error_count"] == 0
        assert result.summary["blocking_rows"] == 0
        assert result.summary["completeness_pct"] == 100.0

    def test_missing_contact_is_warning_not_blocking(self):
        result = validate_dataframe(
            validation_frame(
                phone="",
                phone_raw="",
                missing_phone=True,
                phone_valid=False,
                is_complete=False,
                validation_status="needs_review",
                quality_score=80,
            )
        )
        assert result.summary["error_count"] == 0
        assert result.summary["warning_count"] >= 1
        assert result.summary["blocking_rows"] == 0
        assert result.summary["missing_phone_count"] == 1
        assert result.summary["missing_phone_pct"] == 100.0

    def test_invalid_city_is_blocking(self):
        result = validate_dataframe(validation_frame(city="Atlantis"))
        assert result.summary["error_count"] == 1
        assert 0 in result.blocking_indices

    def test_invalid_category_is_blocking(self):
        result = validate_dataframe(validation_frame(category="Mystery"))
        assert result.summary["error_count"] == 1
        assert 0 in result.blocking_indices

    def test_duplicate_business_id_is_blocking(self):
        frame = pd.concat([validation_frame(), validation_frame()], ignore_index=True)
        result = validate_dataframe(frame)
        assert result.summary["duplicate_business_id_count"] == 1
        assert 1 in result.blocking_indices

    def test_duplicate_source_record_is_blocking(self):
        second = validation_frame(business_id="BP-OSM-N-999")
        frame = pd.concat([validation_frame(), second], ignore_index=True)
        result = validate_dataframe(frame)
        assert result.summary["duplicate_source_record_count"] == 1
        assert 1 in result.blocking_indices

    def test_invalid_coordinate_is_blocking(self):
        result = validate_dataframe(validation_frame(latitude=999))
        assert result.summary["error_count"] == 1
        assert 0 in result.blocking_indices

    def test_audit_inconsistency_is_blocking(self):
        result = validate_dataframe(
            validation_frame(
                missing_phone=True,
                is_complete=True,
                validation_status="valid",
            )
        )
        assert result.summary["error_count"] >= 1
        assert 0 in result.blocking_indices

    def test_future_collection_date_is_warning(self):
        result = validate_dataframe(validation_frame(collection_date="2099-01-01"))
        assert result.summary["error_count"] == 0
        assert result.summary["warning_count"] >= 1

    def test_empty_input_returns_zero_summary(self):
        result = validate_dataframe(pd.DataFrame())
        assert result.summary["rows_checked"] == 0
        assert result.summary["blocking_rows"] == 0
        assert result.issues.empty
