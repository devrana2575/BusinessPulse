"""Unit tests for the transparent opportunity score and tier logic."""

from __future__ import annotations

import math

import pytest

from analytics.business_insights.opportunity_analysis import (
    compute_opportunity_score,
    opportunity_tier,
)
from analytics.constants import OPPORTUNITY_WEIGHTS


class TestOpportunityScore:
    def test_equal_representation_and_full_coverage_scores_only_reliability(self):
        result = compute_opportunity_score(1.0, 100.0, 100.0)
        assert result["underrepresentation_index"] == 0.0
        assert result["city_breadth_gap"] == 0.0
        assert result["reliability_index"] == 1.0
        assert result["opportunity_score"] == 15.0

    def test_known_score(self):
        result = compute_opportunity_score(0.5, 50.0, 0.0)
        assert result["underrepresentation_points"] == 30.0
        assert result["breadth_points"] == 12.5
        assert result["reliability_points"] == 0.0
        assert result["opportunity_score"] == 42.5

    def test_null_representation_is_treated_as_zero(self):
        result = compute_opportunity_score(None, 0.0, 0.0)
        assert result["underrepresentation_index"] == 1.0
        assert result["opportunity_score"] == 85.0

    def test_nan_input_is_treated_as_zero(self):
        result = compute_opportunity_score(math.nan, math.nan, math.nan)
        assert result["opportunity_score"] == 85.0

    def test_overrepresentation_is_capped_at_zero_underrepresentation(self):
        result = compute_opportunity_score(2.5, 100.0, 100.0)
        assert result["underrepresentation_index"] == 0.0
        assert result["opportunity_score"] == 15.0

    def test_weights_must_sum_to_one(self):
        with pytest.raises(ValueError, match="sum to 1"):
            compute_opportunity_score(0.5, 50.0, 50.0, {"a": 0.5})

    def test_default_weights_are_transparent(self):
        assert OPPORTUNITY_WEIGHTS == {
            "underrepresentation_weight": 0.60,
            "city_breadth_weight": 0.25,
            "reliability_weight": 0.15,
        }
        assert abs(sum(OPPORTUNITY_WEIGHTS.values()) - 1.0) < 1e-9


class TestOpportunityTier:
    @pytest.mark.parametrize(
        ("score", "candidate", "expected"),
        [
            (60.0, True, "High"),
            (59.99, True, "Medium"),
            (40.0, True, "Medium"),
            (39.99, True, "Low"),
            (99.0, False, "Insufficient evidence"),
        ],
    )
    def test_thresholds(self, score, candidate, expected):
        assert opportunity_tier(score, candidate) == expected

    def test_threshold_overrides(self):
        assert opportunity_tier(70.0, True, high_threshold=75.0, medium_threshold=50.0) == "Medium"
