"""Unit tests for the documented cleaning rules."""

from __future__ import annotations

import pandas as pd
import pytest

from analytics.cleaning.cleaning import (
    build_address,
    clean_dataframe,
    compute_quality_score,
    detect_duplicates,
    is_valid_address,
    is_valid_phone,
    map_category,
    normalize_address,
    normalize_business_name,
    normalize_category,
    normalize_city,
    normalize_phone,
    validation_status,
)
from tests.conftest import make_raw_row


class TestNormalisation:
    def test_phone_keeps_country_code_and_strips_punctuation(self):
        assert normalize_phone("+91 (98765) 43210") == "+919876543210"

    def test_phone_converts_00_prefix(self):
        assert normalize_phone("0091 98765 43210") == "+919876543210"

    def test_phone_uses_first_of_multiple_numbers(self):
        assert normalize_phone("+91 98765 43210 / +91 90000 00000") == "+919876543210"

    def test_phone_removes_extension(self):
        assert normalize_phone("+91 98765 43210 ext. 22") == "+919876543210"

    def test_placeholder_phone_is_blank(self):
        for value in ("", "n/a", "N/A", "-", "0", None, float("nan")):
            assert normalize_phone(value) == ""

    def test_phone_validation(self):
        assert is_valid_phone("+91 98765 43210")
        assert is_valid_phone("020 1234 5678")
        assert not is_valid_phone("123")
        assert not is_valid_phone("1111111")
        assert not is_valid_phone("call me")
        assert not is_valid_phone("")

    def test_city_and_category_aliases(self):
        assert normalize_city("Bombay") == "Mumbai"
        assert normalize_city("bengaluru") == "Bengaluru"
        assert normalize_city("Atlantis") is None
        assert normalize_category("food and beverage") == "Food & Beverage"
        assert normalize_category("shop") == "Retail"
        assert normalize_category("unknown") is None

    def test_business_name_trimming(self):
        assert normalize_business_name("  'Cafe  A.'  ") == "Cafe A"
        assert normalize_business_name(None) == ""

    def test_address_normalisation_and_validity(self):
        assert normalize_address("  12,  MG   Road , Pune ") == "12, MG Road, Pune"
        assert is_valid_address("12 MG Road, Pune")
        assert not is_valid_address("Pune")
        assert not is_valid_address("")

    def test_build_address_uses_published_components_only(self):
        tags = {
            "addr:housenumber": "12",
            "addr:street": "MG Road",
            "addr:suburb": "Shivajinagar",
            "addr:postcode": "411001",
        }
        assert build_address(tags) == "12 MG Road, Shivajinagar, 411001"
        assert build_address({}) == ""

    def test_build_address_prefers_full_address(self):
        assert build_address({"addr:full": "1 Main Road, Pune", "addr:street": "Ignored"}) == "1 Main Road, Pune"


class TestCategoryMapping:
    @pytest.mark.parametrize(
        ("tags", "expected"),
        [
            ({"amenity": "restaurant"}, "Food & Beverage"),
            ({"shop": "bakery"}, "Food & Beverage"),
            ({"shop": "car_repair"}, "Automotive"),
            ({"shop": "hardware"}, "Home & Repair Services"),
            ({"office": "lawyer"}, "Professional Services"),
            ({"shop": "beauty"}, "Beauty & Personal Care"),
            ({"tourism": "hotel"}, "Hospitality"),
            ({"leisure": "fitness_centre"}, "Fitness & Recreation"),
            ({"shop": "clothes"}, "Retail"),
        ],
    )
    def test_categories(self, tags, expected):
        assert map_category(tags)[0] == expected

    def test_non_business_is_excluded(self):
        assert map_category({"office": "government"})[0] is None
        assert map_category({"amenity": "school"})[0] is None
        assert map_category({"shop": "vacant"})[0] is None

    def test_unmapped_is_none(self):
        assert map_category({"name": "A thing"})[0] is None


class TestQualityRules:
    def test_score_penalties_are_documented(self):
        assert compute_quality_score(False, False, False, True, True) == 100
        assert compute_quality_score(True, False, False, False, True) == 80
        assert compute_quality_score(False, True, False, True, False) == 75
        assert compute_quality_score(True, True, True, False, False) == 35
        assert compute_quality_score(False, False, False, False, False) == 85

    def test_status_and_completeness(self):
        assert validation_status(False, False, False, True, True) == "valid"
        assert validation_status(True, False, False, False, True) == "needs_review"
        assert validation_status(False, False, True, True, True) == "needs_review"


class TestCleaningPipeline:
    def test_complete_row_is_kept_and_audited(self):
        result = clean_dataframe(pd.DataFrame([make_raw_row()]))
        assert len(result.cleaned) == 1
        row = result.cleaned.iloc[0]
        assert row["phone"] == "+919876543210"
        assert bool(row["phone_valid"]) is True
        assert bool(row["address_valid"]) is True
        assert bool(row["is_complete"]) is True
        assert row["validation_status"] == "valid"
        assert int(row["quality_score"]) == 100
        assert result.rejected.empty
        assert result.duplicates.empty

    def test_missing_contact_is_not_invented(self):
        raw = pd.DataFrame(
            [
                make_raw_row(
                    business_id="BP-OSM-N-9",
                    business_name="No Contact Store",
                    address="",
                    phone="",
                    phone_raw="",
                    source_record_id="node/9",
                )
            ]
        )
        result = clean_dataframe(raw)
        row = result.cleaned.iloc[0]
        assert row["address"] == ""
        assert row["phone"] == ""
        assert bool(row["missing_phone"]) is True
        assert bool(row["missing_address"]) is True
        assert bool(row["is_complete"]) is False
        assert row["validation_status"] == "needs_review"

    def test_invalid_city_is_rejected_with_reason(self):
        result = clean_dataframe(
            pd.DataFrame([make_raw_row(city="Atlantis", business_id="BP-OSM-N-8")])
        )
        assert result.cleaned.empty
        assert len(result.rejected) == 1
        assert "invalid or missing city" in result.rejected.iloc[0]["rejection_reason"]

    def test_duplicate_business_id_is_rejected(self):
        result = clean_dataframe(
            pd.DataFrame(
                [
                    make_raw_row(),
                    make_raw_row(
                        business_name="Different Name",
                        address="99 Other Road, Pune",
                        phone="+91 90000 00000",
                        phone_raw="+91 90000 00000",
                        source_record_id="node/99",
                    ),
                ]
            )
        )
        assert len(result.cleaned) == 1
        assert len(result.rejected) == 1
        assert "duplicate business_id" in result.rejected.iloc[0]["rejection_reason"]

    def test_exact_duplicate_is_flagged_not_deleted(self):
        first = make_raw_row()
        second = make_raw_row(
            business_id="BP-OSM-N-77",
            source_record_id="node/77",
            phone="+91 90000 00000",
            phone_raw="+91 90000 00000",
        )
        result = clean_dataframe(pd.DataFrame([first, second]))
        assert len(result.cleaned) == 2
        assert int(result.cleaned["duplicate_flag"].sum()) == 1
        assert len(result.duplicates) == 1
        assert result.duplicates.iloc[0]["duplicate_reason"] == "name + city + address"
        assert result.cleaned["business_id"].nunique() == 2

    def test_duplicate_detection_requires_name_and_city(self):
        frame = pd.DataFrame(
            [
                {
                    "business_id": "A",
                    "business_name": "Same Name",
                    "name_key": "samename",
                    "city": "Pune",
                    "address": "1 Road, Pune",
                    "address_key": "1roadpune",
                    "phone": "1234567",
                    "phone_key": "1234567",
                    "source_record_id": "node/1",
                },
                {
                    "business_id": "B",
                    "business_name": "Same Name",
                    "name_key": "samename",
                    "city": "Mumbai",
                    "address": "1 Road, Pune",
                    "address_key": "1roadpune",
                    "phone": "1234567",
                    "phone_key": "1234567",
                    "source_record_id": "node/2",
                },
            ]
        )
        result, _ = detect_duplicates(frame)
        assert int(result["duplicate_flag"].sum()) == 0

    def test_empty_dataframe_raises(self):
        with pytest.raises(ValueError, match="Raw dataset is empty"):
            clean_dataframe(pd.DataFrame())

    def test_missing_required_columns_raise(self):
        with pytest.raises(ValueError, match="missing required columns"):
            clean_dataframe(pd.DataFrame([{"business_id": "x"}]))
