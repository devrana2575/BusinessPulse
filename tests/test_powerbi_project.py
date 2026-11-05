from __future__ import annotations

import base64
import json
import re
import zlib
from copy import deepcopy
from pathlib import Path

import pytest

from scripts import build_powerbi_project as powerbi


def _write_tmdl(path: Path, text: str) -> None:
    path.write_bytes(text.encode("utf-8"))


def test_offline_snapshot_is_consistent_and_keyed():
    snapshot = powerbi.load_snapshot()

    assert len(snapshot.listings) == 2252
    assert len({row["business_id"] for row in snapshot.listings}) == 2252
    assert len({row["city"] for row in snapshot.listings}) == 12
    assert len({row["category"] for row in snapshot.listings}) == 12
    assert len(snapshot.opportunities) == 144
    assert sum(int(row["is_covered"]) for row in snapshot.opportunities) == 123


def test_snapshot_validator_rejects_duplicate_business_keys():
    snapshot = powerbi.load_snapshot()
    listings = deepcopy(snapshot.listings)
    listings[1]["business_id"] = listings[0]["business_id"]

    with pytest.raises(ValueError, match="duplicate business_id"):
        powerbi._validate_snapshot(listings, snapshot.opportunities)


def test_snapshot_validator_rejects_inconsistent_complete_flag():
    snapshot = powerbi.load_snapshot()
    listings = deepcopy(snapshot.listings)
    listings[0]["is_complete"] = (
        "False"
        if listings[0]["is_complete"].casefold() == "true"
        else "True"
    )

    with pytest.raises(ValueError, match="strict audit rule"):
        powerbi._validate_snapshot(listings, snapshot.opportunities)


def test_embedded_m_payload_round_trips_source_csv():
    snapshot = powerbi.load_snapshot()

    for source_csv in (snapshot.listing_csv, snapshot.opportunity_csv):
        expression = powerbi._compressed_m_expression(source_csv)
        payload = "".join(re.findall(r'"([A-Za-z0-9+/=]+)"', expression))
        compressed = base64.b64decode(payload)
        assert zlib.decompress(compressed, wbits=-15) == source_csv


def test_generated_pbip_contains_four_pages_and_required_visuals(tmp_path: Path):
    output_dir = tmp_path / "BusinessPulse"
    result = powerbi.generate_project(output_dir=output_dir)

    assert Path(result["project"]).is_file()
    assert result["listing_rows"] == 2252
    assert result["unique_business_ids"] == 2252
    assert result["opportunity_pairs"] == 144
    assert result["page_count"] == 4
    assert result["visual_count"] == 55
    assert result["visual_count"] >= 40
    assert result["desktop_validation"] == "pending"

    static_result = powerbi.validate_project(output_dir)
    assert static_result["static_validation"] == "passed"
    assert static_result["desktop_validation"] == "not performed"
    assert static_result["tables"] == 6
    assert static_result["relationships"] == 6
    assert static_result["tmdl_documents"] == 10
    assert static_result["visuals"] == 55
    assert static_result["measures"] == len(
        powerbi.parse_dax_measures(
            (powerbi.POWERBI_DIR / "dax_measures.dax").read_text(encoding="utf-8")
        )
    )
    assert set(static_result["pages"].values()) == {
        "Executive Overview",
        "Geographic Market Analysis",
        "Data Quality Analysis",
        "Market Opportunity Analysis",
    }


def test_generator_refuses_an_unmarked_output_directory(tmp_path: Path):
    output_dir = tmp_path / "existing"
    output_dir.mkdir()
    (output_dir / "user-file.txt").write_text("preserve", encoding="utf-8")

    with pytest.raises(FileExistsError, match="unmarked directory"):
        powerbi.generate_project(output_dir=output_dir)

    assert (output_dir / "user-file.txt").read_text(encoding="utf-8") == "preserve"


def test_generator_emits_required_pbir_report_definition(tmp_path: Path):
    output_dir = tmp_path / "BusinessPulse"
    powerbi.generate_project(output_dir=output_dir)

    report_definition = (
        output_dir / "BusinessPulse.Report" / "definition"
    )
    report_json = json.loads((report_definition / "report.json").read_text(encoding="utf-8"))
    assert report_json["$schema"] == powerbi.REPORT_DEFINITION_SCHEMA
    assert not (output_dir / "BusinessPulse.Report" / "report.json").exists()


def test_generator_removes_empty_desktop_legacy_report_on_regeneration(
    tmp_path: Path,
):
    output_dir = tmp_path / "BusinessPulse"
    powerbi.generate_project(output_dir=output_dir)
    legacy_report = output_dir / "BusinessPulse.Report" / "report.json"
    legacy_report.write_text(
        json.dumps(
            {
                "config": json.dumps(
                    {
                        "version": "5.44",
                        "themeCollection": {},
                        "activeSectionIndex": 0,
                        "linguisticSchemaSyncVersion": 2,
                        "settings": {},
                    }
                ),
                "layoutOptimization": 0,
                "report": {},
                "sections": [],
            }
        ),
        encoding="utf-8",
    )

    powerbi.generate_project(output_dir=output_dir)

    assert not legacy_report.exists()


def test_generator_preserves_nonempty_desktop_legacy_report(tmp_path: Path):
    output_dir = tmp_path / "BusinessPulse"
    powerbi.generate_project(output_dir=output_dir)
    legacy_report = output_dir / "BusinessPulse.Report" / "report.json"
    legacy_report.write_text(
        json.dumps(
            {
                "config": json.dumps(
                    {
                        "version": "5.44",
                        "themeCollection": {},
                        "activeSectionIndex": 0,
                        "settings": {},
                    }
                ),
                "layoutOptimization": 0,
                "report": {},
                "sections": [{"name": "UserPage"}],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(FileExistsError, match="unrecognized or non-empty"):
        powerbi.generate_project(output_dir=output_dir)

    assert legacy_report.is_file()


def test_static_validator_rejects_root_level_pbir_legacy(tmp_path: Path):
    output_dir = tmp_path / "BusinessPulse"
    powerbi.generate_project(output_dir=output_dir)
    legacy_report = output_dir / "BusinessPulse.Report" / "report.json"
    legacy_report.write_text("{}", encoding="utf-8")

    with pytest.raises(ValueError, match="PBIR and PBIR-Legacy cannot coexist"):
        powerbi.validate_project(output_dir)


def test_static_validator_requires_pbir_report_definition(tmp_path: Path):
    output_dir = tmp_path / "BusinessPulse"
    powerbi.generate_project(output_dir=output_dir)
    report_json = (
        output_dir / "BusinessPulse.Report" / "definition" / "report.json"
    )
    report_json.unlink()

    with pytest.raises(FileNotFoundError, match="Generated project is incomplete"):
        powerbi.validate_project(output_dir)


def test_generator_removes_only_powerbi_auto_date_table_artifacts(tmp_path: Path):
    output_dir = tmp_path / "BusinessPulse"
    powerbi.generate_project(output_dir=output_dir)
    tables_dir = (
        output_dir
        / "BusinessPulse.SemanticModel"
        / "definition"
        / "tables"
    )
    auto_date_table = tables_dir / (
        "DateTableTemplate_5e09dd05-8fee-426a-aa87-0d923769aea3.tmdl"
    )
    auto_date_table.write_text(
        "table DateTableTemplate_5e09dd05-8fee-426a-aa87-0d923769aea3\n"
        "\tisPrivate\n"
        "\tcolumn Date\n"
        "\t\tdataCategory: PaddedDateTableDates\n"
        "\tcolumn Year\n"
        "\tcolumn MonthNo\n"
        "\tcolumn Month\n"
        "\tcolumn QuarterNo\n"
        "\tcolumn Quarter\n"
        "\tcolumn Day\n"
        "\tannotation TemplateId = Year\n"
        "\thierarchy 'Date Hierarchy'\n"
        "\tannotation TemplateId = DateHierarchy\n",
        encoding="utf-8",
    )
    powerbi.generate_project(output_dir=output_dir)

    assert not auto_date_table.exists()


def test_generator_preserves_unrecognized_tmdl_artifacts_on_refusal(tmp_path: Path):
    output_dir = tmp_path / "BusinessPulse"
    powerbi.generate_project(output_dir=output_dir)
    tables_dir = (
        output_dir
        / "BusinessPulse.SemanticModel"
        / "definition"
        / "tables"
    )
    auto_date_table = tables_dir / (
        "DateTableTemplate_5e09dd05-8fee-426a-aa87-0d923769aea3.tmdl"
    )
    auto_date_table.write_text(
        "table DateTableTemplate_5e09dd05-8fee-426a-aa87-0d923769aea3\n"
        "\tisPrivate\n"
        "\tcolumn Date\n"
        "\t\tdataCategory: PaddedDateTableDates\n"
        "\tcolumn Year\n"
        "\tcolumn MonthNo\n"
        "\tcolumn Month\n"
        "\tcolumn QuarterNo\n"
        "\tcolumn Quarter\n"
        "\tcolumn Day\n"
        "\tannotation TemplateId = Year\n"
        "\thierarchy 'Date Hierarchy'\n"
        "\tannotation TemplateId = DateHierarchy\n",
        encoding="utf-8",
    )
    unrelated = tables_dir / "user-added.tmdl"
    unrelated.write_text("user content\n", encoding="utf-8")
    legacy_report = output_dir / "BusinessPulse.Report" / "report.json"
    legacy_report.write_text(
        json.dumps(
            {
                "config": json.dumps(
                    {
                        "version": "5.44",
                        "themeCollection": {},
                        "activeSectionIndex": 0,
                        "settings": {},
                    }
                ),
                "layoutOptimization": 0,
                "report": {},
                "sections": [],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(FileExistsError, match="unrecognized TMDL document"):
        powerbi.generate_project(output_dir=output_dir)

    assert auto_date_table.is_file()
    assert unrelated.read_text(encoding="utf-8") == "user content\n"
    assert legacy_report.is_file()


def test_static_validator_detects_incomplete_relationship_contract(tmp_path: Path):
    output_dir = tmp_path / "BusinessPulse"
    powerbi.generate_project(output_dir=output_dir)
    relationship_file = (
        output_dir
        / "BusinessPulse.SemanticModel"
        / "definition"
        / "relationships.tmdl"
    )
    original = relationship_file.read_text(encoding="utf-8")
    _write_tmdl(
        relationship_file,
        original.replace("FactListings.city_id", "FactListings.unknown_city_id", 1),
    )

    with pytest.raises(ValueError, match="relationship contract"):
        powerbi.validate_project(output_dir)


def test_generated_fact_listings_has_one_key_column():
    snapshot = powerbi.load_snapshot()
    model_files = powerbi._model_files(
        (powerbi.POWERBI_DIR / "dax_measures.dax").read_text(encoding="utf-8"),
        snapshot,
    )
    table_text = model_files["definition/tables/FactListings.tmdl"]

    assert re.search(
        r"(?ms)^    column listing_id\n(?:(?!^    column ).)*?^        isHidden$",
        table_text,
    )
    assert re.search(
        r"(?ms)^    column business_id\n(?:(?!^    column ).)*?^        isKey$",
        table_text,
    )
    assert len(re.findall(r"^        isKey$", table_text, re.M)) == 1


def test_static_validator_rejects_multiple_key_columns_in_a_table(tmp_path: Path):
    output_dir = tmp_path / "BusinessPulse"
    powerbi.generate_project(output_dir=output_dir)
    table_file = (
        output_dir
        / "BusinessPulse.SemanticModel"
        / "definition"
        / "tables"
        / "FactListings.tmdl"
    )
    content = table_file.read_text(encoding="utf-8").replace(
        "        sourceColumn: listing_id\n",
        "        sourceColumn: listing_id\n        isKey\n",
        1,
    )
    _write_tmdl(table_file, content)

    with pytest.raises(ValueError, match="Invalid TMDL key-column declarations"):
        powerbi.validate_project(output_dir)


def test_static_validator_detects_stale_visual_files(tmp_path: Path):
    output_dir = tmp_path / "BusinessPulse"
    powerbi.generate_project(output_dir=output_dir)
    stale_visual = (
        output_dir
        / "BusinessPulse.Report"
        / "definition"
        / "pages"
        / "Data_Quality_Analysis"
        / "visuals"
        / "stale_visual"
        / "visual.json"
    )
    stale_visual.parent.mkdir()
    stale_visual.write_text("{}", encoding="utf-8")

    with pytest.raises(ValueError, match="Visual inventory mismatch"):
        powerbi.validate_project(output_dir)


def test_static_validator_rejects_invalid_first_line_tmdl_comment(tmp_path: Path):
    output_dir = tmp_path / "BusinessPulse"
    powerbi.generate_project(output_dir=output_dir)
    database_file = (
        output_dir / "BusinessPulse.SemanticModel" / "definition" / "database.tmdl"
    )
    original = database_file.read_text(encoding="utf-8")
    _write_tmdl(database_file, "// Generated by test; invalid TMDL comment\n" + original)

    with pytest.raises(ValueError, match="Invalid TMDL comment syntax in database.tmdl"):
        powerbi.validate_project(output_dir)


def test_static_validator_rejects_empty_line_after_expression_document_comment(
    tmp_path: Path,
):
    output_dir = tmp_path / "BusinessPulse"
    powerbi.generate_project(output_dir=output_dir)
    expressions_file = (
        output_dir
        / "BusinessPulse.SemanticModel"
        / "definition"
        / "expressions.tmdl"
    )
    original = expressions_file.read_text(encoding="utf-8")
    _write_tmdl(
        expressions_file,
        original.replace(
            "/// Generated by scripts/build_powerbi_project.py; do not edit by hand.\n",
            "/// Generated by scripts/build_powerbi_project.py; do not edit by hand.\n\n",
            1,
        ),
    )

    with pytest.raises(ValueError, match="Invalid empty line after TMDL documentation comment"):
        powerbi.validate_project(output_dir)


def test_static_validator_rejects_malformed_tmdl_declaration_header(tmp_path: Path):
    output_dir = tmp_path / "BusinessPulse"
    powerbi.generate_project(output_dir=output_dir)
    database_file = (
        output_dir / "BusinessPulse.SemanticModel" / "definition" / "database.tmdl"
    )
    original = database_file.read_text(encoding="utf-8")
    _write_tmdl(database_file, original.replace("database\n", "database BusinessPulse\n", 1))

    with pytest.raises(ValueError, match="Invalid TMDL declaration header"):
        powerbi.validate_project(output_dir)


def test_static_validator_requires_all_tmdl_model_table_references(tmp_path: Path):
    output_dir = tmp_path / "BusinessPulse"
    powerbi.generate_project(output_dir=output_dir)
    model_file = (
        output_dir / "BusinessPulse.SemanticModel" / "definition" / "model.tmdl"
    )
    original = model_file.read_text(encoding="utf-8")
    _write_tmdl(model_file, original.replace("\nref table DimCity", "", 1))

    with pytest.raises(ValueError, match="all table, expression, and culture references"):
        powerbi.validate_project(output_dir)


def test_static_validator_rejects_unindented_table_objects(tmp_path: Path):
    output_dir = tmp_path / "BusinessPulse"
    powerbi.generate_project(output_dir=output_dir)
    table_file = (
        output_dir
        / "BusinessPulse.SemanticModel"
        / "definition"
        / "tables"
        / "DimCity.tmdl"
    )
    original = table_file.read_text(encoding="utf-8")
    _write_tmdl(table_file, original.replace("    column city_id", "column city_id", 1))

    with pytest.raises(ValueError, match="Invalid TMDL root declaration"):
        powerbi.validate_project(output_dir)


@pytest.mark.parametrize(
    ("document", "old", "new"),
    [
        (
            Path("relationships.tmdl"),
            "    fromColumn:",
            "    description: invalid relationship description\n"
            "    fromColumn:",
        ),
    ],
)
def test_static_validator_rejects_descriptions_on_unsupported_tmdl_objects(
    tmp_path: Path,
    document: Path,
    old: str,
    new: str,
):
    output_dir = tmp_path / "BusinessPulse"
    powerbi.generate_project(output_dir=output_dir)
    target = output_dir / "BusinessPulse.SemanticModel" / "definition" / document
    content = target.read_text(encoding="utf-8")
    content = content.replace(old, new, 1)
    _write_tmdl(target, content)

    with pytest.raises(
        ValueError, match="Unsupported description property on TMDL relationship"
    ):
        powerbi.validate_project(output_dir)


def test_static_validator_rejects_relationship_documentation_comments(
    tmp_path: Path,
):
    output_dir = tmp_path / "BusinessPulse"
    powerbi.generate_project(output_dir=output_dir)
    relationship_file = (
        output_dir
        / "BusinessPulse.SemanticModel"
        / "definition"
        / "relationships.tmdl"
    )
    content = relationship_file.read_text(encoding="utf-8")
    assert not content.startswith("///")
    _write_tmdl(relationship_file, "/// Generated project marker\n" + content)

    with pytest.raises(
        ValueError,
        match="cannot contain documentation comments.*relationship descriptions",
    ):
        powerbi.validate_project(output_dir)


def test_static_validator_rejects_unknown_relationship_property(tmp_path: Path):
    output_dir = tmp_path / "BusinessPulse"
    powerbi.generate_project(output_dir=output_dir)
    relationship_file = (
        output_dir
        / "BusinessPulse.SemanticModel"
        / "definition"
        / "relationships.tmdl"
    )
    content = relationship_file.read_text(encoding="utf-8").replace(
        "    fromColumn:",
        "    unsupportedProperty: value\n    fromColumn:",
        1,
    )
    _write_tmdl(relationship_file, content)

    with pytest.raises(
        ValueError, match="Unsupported TMDL relationship property or flag"
    ):
        powerbi.validate_project(output_dir)


def test_static_validator_preserves_descriptions_on_supported_model_objects(
    tmp_path: Path,
):
    output_dir = tmp_path / "BusinessPulse"
    powerbi.generate_project(output_dir=output_dir)
    model_root = output_dir / "BusinessPulse.SemanticModel" / "definition"
    database_file = model_root / "database.tmdl"
    database_text = database_file.read_text(encoding="utf-8").replace(
        "database\n",
        "database\n    description: Database description\n",
        1,
    )
    _write_tmdl(database_file, database_text)

    model_file = model_root / "model.tmdl"
    model_text = model_file.read_text(encoding="utf-8").replace(
        "    culture: en-US\n",
        "    culture: en-US\n    description: Model description\n",
        1,
    )
    _write_tmdl(model_file, model_text)

    table_file = model_root / "tables" / "FactListings.tmdl"
    table_text = table_file.read_text(encoding="utf-8")
    table_text = table_text.replace(
        "table FactListings\n",
        "table FactListings\n    description: Listing fact description\n",
        1,
    )
    table_text = table_text.replace(
        "    column listing_id\n        dataType: string\n",
        "    column listing_id\n        dataType: string\n"
        "        description: Listing key description\n",
        1,
    )
    table_text = table_text.replace(
        "    measure 'Total Listings' =\n"
        "            COUNTROWS ( FactListings )\n",
        "    measure 'Total Listings' =\n"
        "            COUNTROWS ( FactListings )\n"
        "        description: Total listing count description\n",
        1,
    )
    table_text = table_text.replace(
        "    partition FactListings = m\n",
        "    partition FactListings = m\n"
        "        description: Offline partition description\n",
        1,
    )
    _write_tmdl(table_file, table_text)

    result = powerbi.validate_project(output_dir)
    assert result["static_validation"] == "passed"
    assert "description: Database description" in database_file.read_text(
        encoding="utf-8"
    )
    assert "description: Listing fact description" in table_file.read_text(
        encoding="utf-8"
    )
