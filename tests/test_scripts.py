"""Tests for operational scripts that do not require a live server."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

import scripts.businesspulse as automation
from scripts.businesspulse import (
    build_parser,
    configured_database,
    ensure_no_imported_rows,
    is_read_only_sql,
    missing_dependencies,
    PlannedStage,
    run_stage_plan,
    run_command,
    verify_analytical_queries_are_read_only,
)
from scripts.export_database_dump import quote_option_value, strip_definers
from scripts.run_pipeline import ROOT
from scripts.setup_database import account_host
from analytics.config import ConfigurationError


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


@pytest.mark.parametrize(
    ("configured_host", "expected_account_host"),
    [
        ("localhost", "localhost"),
        ("127.0.0.1", "127.0.0.1"),
        ("::1", "::1"),
        ("[::1]", "::1"),
    ],
)
def test_account_provisioning_is_limited_to_loopback(
    configured_host, expected_account_host
):
    assert account_host(configured_host) == expected_account_host


@pytest.mark.parametrize("configured_host", ["192.168.1.10", "db.example.com", "%"])
def test_account_provisioning_rejects_non_loopback_hosts(configured_host):
    with pytest.raises(ConfigurationError, match="loopback"):
        account_host(configured_host)


def test_setup_requires_explicit_database_and_account_approval():
    args = build_parser().parse_args(["setup", "--database", "businesspulse"])
    with pytest.raises(SystemExit, match="Both .* are required"):
        run_command(args)


def test_import_requires_empty_target_confirmation_before_database_access():
    args = build_parser().parse_args(["import"])
    with pytest.raises(SystemExit, match="--confirm-target-empty"):
        run_command(args)


def test_import_guard_rejects_existing_data():
    with pytest.raises(RuntimeError, match="already contains imported data"):
        ensure_no_imported_rows(
            {
                "listing_master": 1,
                "data_quality_audit": 0,
                "import_batches": 0,
                "listing_rejects": 0,
            }
        )


def test_import_guard_allows_empty_data_tables():
    ensure_no_imported_rows(
        {
            "listing_master": 0,
            "data_quality_audit": 0,
            "import_batches": 0,
            "listing_rejects": 0,
        }
    )


def test_import_command_does_not_expose_data_replacement_option():
    with pytest.raises(SystemExit):
        build_parser().parse_args(["import", "--replace-data"])


def test_clean_requires_confirmation_before_replacing_derived_outputs():
    args = build_parser().parse_args(["clean"])
    with pytest.raises(SystemExit, match="--confirm-regenerate"):
        run_command(args)


def test_analytical_queries_are_read_only():
    assert is_read_only_sql("SELECT 1")
    assert is_read_only_sql("SELECT 'UPDATE FROM users' AS note")
    assert is_read_only_sql("WITH totals AS (SELECT 1) SELECT * FROM totals")
    assert not is_read_only_sql("DELETE FROM listing_master")
    assert not is_read_only_sql("DROP TABLE listing_master")
    assert not is_read_only_sql("WITH rows AS (SELECT 1) DELETE FROM listing_master")
    assert not is_read_only_sql("SELECT 1; DELETE FROM listing_master")
    assert not is_read_only_sql("SELECT 1 INTO OUTFILE 'export.csv'")
    assert not is_read_only_sql("SELECT * FROM listing_master FOR UPDATE")
    assert not is_read_only_sql("SELECT SLEEP(5)")
    assert not is_read_only_sql("/*! INSERT INTO listing_master VALUES (1) */ SELECT 1")
    verify_analytical_queries_are_read_only()


def test_stage_plan_records_success_and_explicit_skips(tmp_path):
    log_path = tmp_path / "automation.jsonl"
    calls = []
    exit_code = run_stage_plan(
        [
            PlannedStage("preflight"),
            PlannedStage("import", "database write is opt-in"),
            PlannedStage("eda"),
        ],
        lambda name: calls.append(name) or 0,
        log_path=log_path,
    )
    events = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]
    finished = [event for event in events if event["event"] == "stage_finished"]
    assert exit_code == 0
    assert calls == ["preflight", "eda"]
    assert [event["status"] for event in finished] == ["PASSED", "SKIPPED", "PASSED"]
    assert [event["stage"] for event in finished] == ["preflight", "import", "eda"]


def test_stage_failure_stops_workflow_and_marks_remaining_stages_skipped(tmp_path):
    log_path = tmp_path / "automation.jsonl"
    calls = []
    exit_code = run_stage_plan(
        [PlannedStage("preflight"), PlannedStage("sql-analysis"), PlannedStage("eda")],
        lambda name: calls.append(name) or (7 if name == "sql-analysis" else 0),
        log_path=log_path,
    )
    events = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]
    finished = [event for event in events if event["event"] == "stage_finished"]
    assert exit_code == 1
    assert calls == ["preflight", "sql-analysis"]
    assert [event["status"] for event in finished] == ["PASSED", "FAILED", "SKIPPED"]
    assert events[-1]["event"] == "workflow_finished"
    assert events[-1]["status"] == "FAILED"


def test_missing_stage_dependencies_are_reported(monkeypatch):
    monkeypatch.setattr(
        automation.importlib.util,
        "find_spec",
        lambda module: None if module == "matplotlib" else object(),
    )
    assert missing_dependencies("eda") == ["matplotlib"]


def test_missing_stage_dependency_fails_without_invoking_a_runner(monkeypatch):
    monkeypatch.setattr(automation, "missing_dependencies", lambda stage: ["SQLAlchemy"])
    monkeypatch.setattr(
        automation,
        "run_step",
        lambda *command: pytest.fail("A stage with missing dependencies must not run"),
    )
    args = build_parser().parse_args(["eda"])
    assert automation.execute_stage("eda", args) == 1


def test_unsafe_database_names_are_rejected_before_connection():
    with pytest.raises(SystemExit, match="system database"):
        configured_database("mysql")


def test_database_target_must_match_local_configuration(monkeypatch):
    monkeypatch.setattr(
        "analytics.config.get_settings",
        lambda: SimpleNamespace(mysql_database="businesspulse", mysql_host="localhost"),
    )
    with pytest.raises(SystemExit, match="must exactly match MYSQL_DATABASE"):
        configured_database("businesspulse_test")


def test_non_loopback_database_target_is_rejected(monkeypatch):
    monkeypatch.setattr(
        "analytics.config.get_settings",
        lambda: SimpleNamespace(mysql_database="businesspulse", mysql_host="db.example.com"),
    )
    with pytest.raises(SystemExit, match="non-loopback"):
        configured_database("businesspulse")


def test_database_stage_rejects_mariadb_without_a_real_connection(monkeypatch):
    class Result:
        def one(self):
            return ("11.5.2-MariaDB", "businesspulse")

    class Connection:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def execute(self, _query):
            return Result()

    class Engine:
        disposed = False

        def connect(self):
            return Connection()

        def dispose(self):
            self.disposed = True

    engine = Engine()
    monkeypatch.setattr("sqlalchemy.create_engine", lambda *args, **kwargs: engine)
    with pytest.raises(SystemExit, match="MariaDB"):
        automation.verify_target_mysql(
            SimpleNamespace(database_url="unused", mysql_database="businesspulse")
        )
    assert engine.disposed


def test_database_stage_rejects_wrong_connected_schema(monkeypatch):
    class Result:
        def one(self):
            return ("9.1.0", "another_database")

    class Connection:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def execute(self, _query):
            return Result()

    class Engine:
        def connect(self):
            return Connection()

        def dispose(self):
            pass

    monkeypatch.setattr("sqlalchemy.create_engine", lambda *args, **kwargs: Engine())
    with pytest.raises(SystemExit, match="does not match"):
        automation.verify_target_mysql(
            SimpleNamespace(database_url="unused", mysql_database="businesspulse")
        )


def test_workflow_import_requires_database_and_empty_target_confirmation():
    args = build_parser().parse_args(["workflow", "--include-import"])
    with pytest.raises(SystemExit, match="explicit --database"):
        automation.workflow_plan(args)

    args = build_parser().parse_args(
        ["workflow", "--database", "businesspulse", "--include-import"]
    )
    with pytest.raises(SystemExit, match="--confirm-target-empty"):
        automation.workflow_plan(args)


def test_workflow_without_database_skips_all_database_stages(monkeypatch):
    monkeypatch.setattr(
        automation,
        "configured_database",
        lambda database: SimpleNamespace(mysql_database=database),
    )
    args = build_parser().parse_args(["workflow"])
    plan = automation.workflow_plan(args)
    skipped = {stage.name: stage.skip_reason for stage in plan if stage.skip_reason}
    assert skipped["import"]
    assert skipped["sql-analysis"]
    assert skipped["business-insights"]
    assert skipped["reconciliation"]
    assert plan[1].name == "clean"
    assert plan[1].skip_reason == "requires --confirm-regenerate"


def test_powerbi_implementation_checklist_is_machine_readable_and_honest():
    path = ROOT / "powerbi" / "implementation_checklist.json"
    checklist = json.loads(path.read_text(encoding="utf-8"))
    assert checklist["status"] == "PBIP GENERATED — DESKTOP VALIDATION PENDING"
    assert checklist["desktop"]["validation_performed"] is False
    assert checklist["generated_project"]["pbip_generated"] is True
    assert checklist["generated_project"]["pbix_generated"] is False
    assert checklist["generated_project"]["visual_count"] == 55
    assert [page["id"] for page in checklist["pages"]] == [
        "executive-overview",
        "geographic-market-analysis",
        "data-quality-analysis",
        "market-opportunity-analysis",
    ]
    assert all(
        page["status"] == "generated_not_desktop_validated"
        for page in checklist["pages"]
    )
    assert all(
        item["status"] == "generated_static_validation_passed"
        and item["desktop_validation_required"]
        for page in checklist["pages"]
        for item in page["checklist"]
    )
