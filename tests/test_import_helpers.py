"""Tests for import helper functions (no live database required)."""

from __future__ import annotations

import hashlib
from datetime import datetime
from pathlib import Path

import pandas as pd
import pytest

from scripts.import_data import (
    bool_value,
    nullable_float,
    nullable_text,
    sha256_file,
    to_naive_utc,
    validate_csv_path,
)


class TestImportHelpers:
    def test_sha256(self, tmp_path):
        path = tmp_path / "x.csv"
        path.write_bytes(b"business_id\nabc\n")
        assert sha256_file(path) == hashlib.sha256(b"business_id\nabc\n").hexdigest()

    def test_validate_csv_path_accepts_csv(self, tmp_path):
        path = tmp_path / "ok.csv"
        path.write_text("a,b\n1,2\n", encoding="utf-8")
        validate_csv_path(path)

    def test_validate_csv_path_rejects_extension(self, tmp_path):
        path = tmp_path / "bad.txt"
        path.write_text("a,b\n1,2\n", encoding="utf-8")
        with pytest.raises(ValueError, match="Only .csv"):
            validate_csv_path(path)

    def test_validate_csv_path_rejects_empty(self, tmp_path):
        path = tmp_path / "empty.csv"
        path.touch()
        with pytest.raises(ValueError, match="empty"):
            validate_csv_path(path)

    def test_validate_csv_path_rejects_missing(self, tmp_path):
        with pytest.raises(ValueError, match="not found"):
            validate_csv_path(tmp_path / "missing.csv")

    @pytest.mark.parametrize(
        ("value", "expected"),
        [(True, True), (False, False), (1, True), ("1", True), ("true", True),
         ("YES", True), (0, False), ("false", False), (None, False), ("", False)],
    )
    def test_bool_value(self, value, expected):
        assert bool_value(value) is expected

    def test_bool_value_pandas_na(self):
        assert bool_value(pd.NA) is False

    def test_nullable_helpers(self):
        assert nullable_text("  x ") == "x"
        assert nullable_text("") is None
        assert nullable_text(pd.NA) is None
        assert nullable_float("1.5") == 1.5
        assert nullable_float("") is None

    def test_to_naive_utc(self):
        value = to_naive_utc("2026-11-02T00:00:00+00:00")
        assert isinstance(value, datetime)
        assert value.tzinfo is None
        assert value.isoformat() == "2026-11-02T00:00:00"

    def test_import_required_columns_contract(self):
        from scripts.import_data import IMPORT_REQUIRED_COLUMNS

        for column in (
            "business_id",
            "quality_score",
            "validation_status",
            "duplicate_flag",
            "collection_date",
        ):
            assert column in IMPORT_REQUIRED_COLUMNS
