from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from scripts import build_powerbi_desktop_project as powerbi


def test_six_snapshots_reconcile_and_have_unique_relationship_keys():
    snapshots = powerbi.load_snapshots()

    assert powerbi.validate_snapshots(snapshots) == {
        "DimCity": 12,
        "DimCategory": 12,
        "DimSource": 1,
        "FactListings": 2252,
        "FactQualityIssues": 3762,
        "FactCityCategoryCoverage": 144,
    }


def test_snapshot_validator_rejects_duplicate_listing_business_keys():
    snapshots = powerbi.load_snapshots()
    altered = deepcopy(snapshots)
    headers, rows = altered["FactListings"]
    rows[1]["business_id"] = rows[0]["business_id"]
    altered["FactListings"] = (headers, rows)

    with pytest.raises(ValueError, match="duplicate keys"):
        powerbi.validate_snapshots(altered)


def test_generator_creates_four_report_pages_and_all_measures(tmp_path: Path):
    output_dir = tmp_path / "BusinessPulse"

    result = powerbi.generate_project(output_dir)

    assert Path(result["project"]).is_file()
    assert result["tables"] == 7
    assert result["relationships"] == 6
    assert result["measures"] == 50
    assert result["visuals"] == 59
    assert result["desktop_validation"] == "pending"
    assert set(result["pages"].values()) == set(powerbi.PAGE_TITLES.values())
    assert sum(result["visuals_per_page"].values()) == result["visuals"]
    static_result = powerbi.validate_project(output_dir)
    assert static_result["row_counts"]["FactListings"] == 2252


def test_relationships_are_single_direction_and_preserve_issue_grain(tmp_path: Path):
    output_dir = tmp_path / "BusinessPulse"
    powerbi.generate_project(output_dir)

    relationships = (
        output_dir
        / "BusinessPulse.SemanticModel"
        / "definition"
        / "relationships.tmdl"
    ).read_text(encoding="utf-8")

    assert "fromColumn: FactQualityIssues.business_id" in relationships
    assert "toColumn: FactListings.business_id" in relationships
    assert "fromCardinality: many" in relationships
    assert "toCardinality: one" in relationships
    assert "crossFilteringBehavior: oneDirection" in relationships
    assert "bothDirections" not in relationships


def test_generator_refuses_an_unmarked_output_directory(tmp_path: Path):
    output_dir = tmp_path / "existing"
    output_dir.mkdir()
    (output_dir / "user-file.txt").write_text("preserve", encoding="utf-8")

    with pytest.raises(FileExistsError, match="unmarked directory"):
        powerbi.generate_project(output_dir)

    assert (output_dir / "user-file.txt").read_text(encoding="utf-8") == "preserve"
