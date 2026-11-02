"""Tests for operational scripts that do not require a live server."""

from __future__ import annotations

from pathlib import Path

from scripts.export_database_dump import quote_option_value, strip_definers
from scripts.run_pipeline import ROOT


def test_mysql_option_file_quoting():
    assert quote_option_value("simple") == '"simple"'
    assert quote_option_value('a"b') == '"a\\"b"'
    assert quote_option_value("a\\b") == '"a\\\\b"'


def test_dump_definers_are_stripped():
    sql = (
        "/*!50013 DEFINER=`bp_user`@`%` SQL SECURITY DEFINER */\n"
        "CREATE VIEW v AS SELECT 1;\n"
    )
    cleaned = strip_definers(sql)
    assert "DEFINER=" not in cleaned
    assert "SQL SECURITY DEFINER" in cleaned
    assert "CREATE VIEW v" in cleaned


def test_pipeline_root_is_project_root():
    assert (ROOT / "README.md").exists()
    assert (ROOT / "analytics").is_dir()
    assert (ROOT / "database").is_dir()


def test_dump_output_path_contract():
    # The documented default is inside database/ and is a .sql file.
    default = ROOT / "database" / "businesspulse_dump.sql"
    assert Path(default).suffix == ".sql"
