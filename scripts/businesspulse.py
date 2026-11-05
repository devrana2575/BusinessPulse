"""Safe command entry point for the BusinessPulse analyst workflow.

Database creation and import are opt-in, guarded actions. This CLI never
supports database reset or data replacement.
"""

from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
EXPECTED_LISTINGS = 2252
EXPECTED_TABLES = 8
EXPECTED_VIEWS = 7
EXPECTED_QUERIES = 35
BASE_TABLES = (
    "dim_city",
    "dim_category",
    "dim_source",
    "import_batches",
    "listing_master",
    "data_quality_audit",
    "listing_rejects",
    "opportunity_config",
)
IMPORT_DATA_TABLES = (
    "listing_master",
    "data_quality_audit",
    "import_batches",
    "listing_rejects",
)
REQUIRED_PACKAGES = {
    "pandas": "pandas",
    "numpy": "numpy",
    "matplotlib": "matplotlib",
    "pymysql": "PyMySQL",
    "sqlalchemy": "SQLAlchemy",
    "dotenv": "python-dotenv",
    "openpyxl": "openpyxl",
    "requests": "requests",
    "pytest": "pytest",
}
STAGE_DEPENDENCIES = {
    "preflight": tuple(REQUIRED_PACKAGES),
    "clean": ("pandas",),
    "validate": ("pandas",),
    "setup": ("pymysql", "dotenv"),
    "import": ("pandas", "sqlalchemy", "pymysql", "dotenv"),
    "sql-analysis": ("pandas", "sqlalchemy", "pymysql", "dotenv"),
    "eda": ("pandas", "numpy", "matplotlib"),
    "business-insights": (
        "pandas", "numpy", "matplotlib", "sqlalchemy", "pymysql", "dotenv",
    ),
    "reconciliation": ("pandas", "sqlalchemy", "pymysql", "dotenv"),
    "reporting": (),
}
AUTOMATION_LOG = ROOT / "data" / "reports" / "businesspulse_automation.jsonl"


@dataclass(frozen=True)
class PlannedStage:
    name: str
    skip_reason: str | None = None


@dataclass(frozen=True)
class StageResult:
    name: str
    status: str
    exit_code: int | None
    duration_seconds: float
    detail: str = ""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run BusinessPulse checks and analytics with guarded DB writes."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    preflight = subparsers.add_parser(
        "preflight",
        help="Check Python, dependencies and repository data without database writes.",
    )
    preflight.add_argument(
        "--check-database",
        action="store_true",
        help="Also test the configured database with read-only SELECT statements.",
    )
    preflight.add_argument(
        "--database",
        help="Explicit database target required with --check-database.",
    )

    clean = subparsers.add_parser(
        "clean", help="Regenerate derived cleaned files from the raw CSV."
    )
    clean.add_argument(
        "--confirm-regenerate",
        action="store_true",
        help="Confirm that existing derived cleaning outputs may be replaced.",
    )
    subparsers.add_parser(
        "validate", help="Validate the existing cleaned CSV and write validation reports."
    )
    setup = subparsers.add_parser(
        "setup", help="Create a new database and provision its application account."
    )
    setup.add_argument("--database", required=True, help="Must match MYSQL_DATABASE.")
    setup.add_argument(
        "--confirm-database-create",
        action="store_true",
        help="Confirm creation of this new database on the configured server.",
    )
    setup.add_argument(
        "--confirm-account-provisioning",
        action="store_true",
        help="Confirm creation/granting of the configured application account.",
    )

    importer = subparsers.add_parser(
        "import", help="Import only when the target has no imported listing data."
    )
    importer.add_argument(
        "--confirm-target-empty",
        action="store_true",
        help="Confirm the configured target is the intended empty migration target.",
    )
    importer.add_argument("--csv", help="Optional cleaned CSV path.")
    importer.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate the CSV only; does not connect to or write to MySQL.",
    )
    importer.add_argument(
        "--database",
        help="Must explicitly match MYSQL_DATABASE before any database access.",
    )

    analyze = subparsers.add_parser(
        "analyze", help="Run the read-only analytical SQL queries."
    )
    analyze.add_argument("--database", required=True, help="Explicit configured MySQL target.")

    subparsers.add_parser("eda", help="Generate local exploratory-analysis outputs.")

    insights = subparsers.add_parser(
        "insights", aliases=["business-insights"],
        help="Run the read-only MySQL opportunity analysis.",
    )
    insights.add_argument("--database", required=True, help="Explicit configured MySQL target.")

    reconcile = subparsers.add_parser(
        "reconcile", help="Compare Python metrics with read-only MySQL views."
    )
    reconcile.add_argument("--database", required=True, help="Explicit configured MySQL target.")

    subparsers.add_parser(
        "report", help="Create an index of generated project deliverables."
    )

    workflow = subparsers.add_parser(
        "workflow", help="Run the safe staged workflow; database writes are opt-in."
    )
    workflow.add_argument("--database", help="Explicit configured MySQL target.")
    workflow.add_argument(
        "--confirm-regenerate",
        action="store_true",
        help="Allow the cleaning stage to replace derived cleaned outputs.",
    )
    workflow.add_argument(
        "--include-import",
        action="store_true",
        help="Include the guarded CSV import stage (requires explicit target confirmation).",
    )
    workflow.add_argument(
        "--confirm-target-empty",
        action="store_true",
        help="Confirm the selected database is the intended empty import target.",
    )
    workflow.add_argument("--csv", help="Optional cleaned CSV path for import.")
    return parser


def check_repository() -> bool:
    failed = False

    def report(ok: bool, label: str, detail: str) -> None:
        nonlocal failed
        print(f"{'PASS' if ok else 'FAIL'} {label}: {detail}")
        failed = failed or not ok

    report(
        sys.version_info >= (3, 11),
        "Python",
        f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}; 3.11+ required",
    )

    missing = [
        package for module, package in REQUIRED_PACKAGES.items()
        if importlib.util.find_spec(module) is None
    ]
    report(not missing, "Dependencies", "all required packages found" if not missing else
           f"missing: {', '.join(missing)}")

    paths = {
        "raw CSV": ROOT / "data" / "raw" / "business_listings_raw.csv",
        "cleaned CSV": ROOT / "data" / "processed" / "cleaned_business_listings.csv",
        "schema": ROOT / "database" / "schema.sql",
        "views": ROOT / "database" / "views.sql",
        "SQL queries": ROOT / "database" / "analytical_queries.sql",
        "SQL dump": ROOT / "database" / "businesspulse_dump.sql",
        "Power BI checklist": ROOT / "powerbi" / "implementation_checklist.json",
    }
    for label, path in paths.items():
        report(path.is_file(), label, "present" if path.is_file() else "missing")

    for label in ("raw CSV", "cleaned CSV"):
        path = paths[label]
        if not path.is_file():
            continue
        try:
            with path.open(encoding="utf-8-sig", newline="") as stream:
                row_count = sum(1 for _ in csv.DictReader(stream))
            report(
                row_count == EXPECTED_LISTINGS,
                f"{label} rows",
                f"{row_count}; expected {EXPECTED_LISTINGS}",
            )
        except (OSError, UnicodeError, csv.Error) as exc:
            report(False, f"{label} read", type(exc).__name__)

    if paths["schema"].is_file():
        schema = paths["schema"].read_text(encoding="utf-8")
        table_count = len(
            re.findall(r"(?im)^\s*CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+", schema)
        )
        report(
            table_count == EXPECTED_TABLES,
            "Schema tables",
            f"{table_count}; expected {EXPECTED_TABLES}",
        )
        for name in BASE_TABLES:
            present = re.search(
                rf"(?im)^\s*CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+`?{re.escape(name)}`?\s*\(",
                schema,
            ) is not None
            report(present, f"Table {name}", "declared" if present else "missing")

    if paths["views"].is_file():
        view_count = len(
            re.findall(r"(?im)^\s*CREATE\s+OR\s+REPLACE\s+VIEW\s+", paths["views"].read_text(encoding="utf-8"))
        )
        report(
            view_count == EXPECTED_VIEWS,
            "Reporting views",
            f"{view_count}; expected {EXPECTED_VIEWS}",
        )

    if paths["SQL queries"].is_file():
        query_text = paths["SQL queries"].read_text(encoding="utf-8")
        ids = re.findall(r"(?im)^\s*--\s*QUERY:\s*(Q\d+)\s*\|", query_text)
        expected_ids = [f"Q{number:02d}" for number in range(1, EXPECTED_QUERIES + 1)]
        report(
            ids == expected_ids,
            "Analytical queries",
            f"{len(ids)} ordered query markers; expected {EXPECTED_QUERIES}",
        )

    checklist_path = paths["Power BI checklist"]
    if checklist_path.is_file():
        try:
            checklist = json.loads(checklist_path.read_text(encoding="utf-8"))
            page_ids = [page["id"] for page in checklist["pages"]]
            expected_pages = [
                "executive-overview",
                "geographic-market-analysis",
                "data-quality-analysis",
                "market-opportunity-analysis",
            ]
            valid = (
                checklist["status"] == "NOT BUILT OR VALIDATED IN POWER BI DESKTOP"
                and page_ids == expected_pages
                and all(
                    page["status"] == "specified_not_built"
                    and page["checklist"]
                    for page in checklist["pages"]
                )
            )
            report(
                valid,
                "Power BI checklist",
                "four specified pages; Desktop validation remains pending"
                if valid
                else "invalid or incomplete page checklist",
            )
        except (KeyError, TypeError, json.JSONDecodeError) as exc:
            report(False, "Power BI checklist", f"invalid JSON contract: {type(exc).__name__}")

    return failed


def missing_dependencies(stage: str) -> list[str]:
    return [
        REQUIRED_PACKAGES[module]
        for module in STAGE_DEPENDENCIES[stage]
        if importlib.util.find_spec(module) is None
    ]


def configured_database(database: str | None):
    from analytics.config import ConfigurationError, get_settings
    if importlib.util.find_spec("pymysql") is None:
        raise SystemExit(
            "Missing dependency PyMySQL, required for local database-target checks."
        )
    from scripts.setup_database import IDENTIFIER, account_host

    if not database:
        raise SystemExit("Select the database explicitly with --database.")
    if not IDENTIFIER.fullmatch(database) or database.casefold() in {
        "mysql",
        "information_schema",
        "performance_schema",
        "sys",
    }:
        raise SystemExit("Refusing an invalid or system database target.")
    try:
        settings = get_settings()
    except ConfigurationError as exc:
        raise SystemExit(f"Configuration error: {exc}") from exc
    if database != settings.mysql_database:
        raise SystemExit(
            "Selected database must exactly match MYSQL_DATABASE in local configuration."
        )
    try:
        account_host(settings.mysql_host)
    except ConfigurationError as exc:
        raise SystemExit(
            "Refusing a non-loopback database host for this local workflow."
        ) from exc
    return settings


def append_execution_event(log_path: Path, event: dict) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    safe_event = {
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
        **event,
    }
    with log_path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(safe_event, sort_keys=True) + "\n")


def print_stage_summary(results: Sequence[StageResult]) -> None:
    print("\nWorkflow summary")
    print(f"{'Stage':<22} {'Status':<10} {'Exit':<6} Duration")
    print("-" * 58)
    for result in results:
        exit_code = "-" if result.exit_code is None else str(result.exit_code)
        print(
            f"{result.name:<22} {result.status:<10} {exit_code:<6} "
            f"{result.duration_seconds:.2f}s"
            + (f" — {result.detail}" if result.detail else "")
        )


def run_stage_plan(
    plan: Sequence[PlannedStage],
    executor: Callable[[str], int],
    *,
    log_path: Path = AUTOMATION_LOG,
) -> int:
    results: list[StageResult] = []
    halted = False
    for stage in plan:
        if halted:
            result = StageResult(stage.name, "SKIPPED", None, 0, "stopped after prior failure")
            append_execution_event(
                log_path,
                {"event": "stage_finished", "stage": stage.name, "status": "SKIPPED",
                 "exit_code": None, "duration_seconds": 0, "detail": result.detail},
            )
            results.append(result)
            continue
        if stage.skip_reason:
            result = StageResult(stage.name, "SKIPPED", None, 0, stage.skip_reason)
            append_execution_event(
                log_path,
                {"event": "stage_finished", "stage": stage.name, "status": "SKIPPED",
                 "exit_code": None, "duration_seconds": 0, "detail": stage.skip_reason},
            )
            results.append(result)
            continue

        started = time.perf_counter()
        append_execution_event(
            log_path, {"event": "stage_started", "stage": stage.name}
        )
        detail = ""
        try:
            exit_code = int(executor(stage.name))
        except SystemExit as exc:
            exit_code = exc.code if isinstance(exc.code, int) else 1
            detail = str(exc) if exc.code is not None else "stage exited unsuccessfully"
        except OSError as exc:
            exit_code = 1
            detail = f"{type(exc).__name__}: {exc}"
        duration = round(time.perf_counter() - started, 3)
        status = "PASSED" if exit_code == 0 else "FAILED"
        result = StageResult(stage.name, status, exit_code, duration, detail)
        append_execution_event(
            log_path,
            {"event": "stage_finished", "stage": stage.name, "status": status,
             "exit_code": exit_code, "duration_seconds": duration, "detail": detail},
        )
        results.append(result)
        halted = exit_code != 0

    append_execution_event(
        log_path,
        {
            "event": "workflow_finished",
            "status": (
                "FAILED"
                if any(result.status == "FAILED" for result in results)
                else "COMPLETED"
            ),
            "stages": [result.__dict__ for result in results],
        },
    )
    print_stage_summary(results)
    return 1 if any(result.status == "FAILED" for result in results) else 0


def check_database(database: str) -> bool:
    configured_database(database)
    missing = [
        package
        for module, package in REQUIRED_PACKAGES.items()
        if module in {"sqlalchemy", "pymysql", "dotenv"}
        and importlib.util.find_spec(module) is None
    ]
    if missing:
        print(f"FAIL Database check dependencies: missing {', '.join(missing)}")
        return True

    from sqlalchemy import create_engine, text
    from sqlalchemy.exc import SQLAlchemyError

    from analytics.config import ConfigurationError, get_settings

    try:
        settings = get_settings()
    except ConfigurationError as exc:
        print(f"FAIL Database configuration: {exc}")
        return True

    print(
        f"Database target: {settings.mysql_host}:{settings.mysql_port}/"
        f"{settings.mysql_database} (credentials hidden)"
    )
    engine = create_engine(settings.database_url, pool_pre_ping=True, future=True)
    try:
        with engine.connect() as connection:
            version, database = connection.execute(
                text("SELECT VERSION(), DATABASE()")
            ).one()
        if "mariadb" in str(version).casefold():
            print(
                f"FAIL Database server product: {version}; Oracle MySQL is required."
            )
            return True
        print(
            f"PASS Database connection: server={version}; database={database}. "
            "Standalone service identity is not verified by this check."
        )
        return False
    except (SQLAlchemyError, OSError) as exc:
        original = getattr(exc, "orig", None)
        code = original.args[0] if original is not None and getattr(original, "args", ()) else None
        suffix = f"; error code {code}" if code is not None else ""
        print(
            f"FAIL Database connection: {type(exc).__name__}{suffix}; "
            "credentials and connection details suppressed"
        )
        return True
    finally:
        engine.dispose()


def verify_target_mysql(settings) -> None:
    from sqlalchemy import create_engine, text
    from sqlalchemy.exc import SQLAlchemyError

    engine = create_engine(settings.database_url, pool_pre_ping=True, future=True)
    try:
        with engine.connect() as connection:
            version, selected_database = connection.execute(
                text("SELECT VERSION(), DATABASE()")
            ).one()
        if "mariadb" in str(version).casefold():
            raise SystemExit(
                f"Refusing database stage: server product is MariaDB ({version}); "
                "Oracle MySQL is required."
            )
        if selected_database != settings.mysql_database:
            raise SystemExit(
                "Refusing database stage because the connected schema does not match "
                "the explicitly selected target."
            )
    except SQLAlchemyError as exc:
        original = getattr(exc, "orig", None)
        code = original.args[0] if original is not None and getattr(original, "args", ()) else None
        suffix = f"; error code {code}" if code is not None else ""
        raise SystemExit(
            f"Could not verify the MySQL target: {type(exc).__name__}{suffix}; "
            "credentials and connection details suppressed."
        ) from exc
    finally:
        engine.dispose()


def run_step(label: str, *command: str) -> int:
    print(f"\n[{label}] {' '.join(command)}", flush=True)
    result = subprocess.run(command, cwd=ROOT, check=False)
    if result.returncode:
        print(f"{label} failed with exit code {result.returncode}.")
    return result.returncode


def sql_code_only(statement: str) -> str:
    """Mask quoted text and comments before applying the conservative SQL guard."""
    output: list[str] = []
    index = 0
    quote: str | None = None
    line_comment = False
    block_comment = False
    while index < len(statement):
        char = statement[index]
        next_char = statement[index + 1] if index + 1 < len(statement) else ""
        if line_comment:
            if char in "\r\n":
                line_comment = False
                output.append(char)
            else:
                output.append(" ")
            index += 1
            continue
        if block_comment:
            if char == "*" and next_char == "/":
                output.extend((" ", " "))
                block_comment = False
                index += 2
            else:
                output.append("\n" if char == "\n" else " ")
                index += 1
            continue
        if quote:
            if char == "\\" and quote != "`" and next_char:
                output.extend((" ", " "))
                index += 2
                continue
            if char == quote:
                if next_char == quote:
                    output.extend((" ", " "))
                    index += 2
                    continue
                quote = None
            output.append(" ")
            index += 1
            continue
        if char in {"'", '"', "`"}:
            quote = char
            output.append(" ")
            index += 1
        elif char == "-" and next_char == "-" and (
            index + 2 == len(statement) or statement[index + 2].isspace()
        ):
            line_comment = True
            output.extend((" ", " "))
            index += 2
        elif char == "#":
            line_comment = True
            output.append(" ")
            index += 1
        elif char == "/" and next_char == "*":
            block_comment = True
            output.extend((" ", " "))
            index += 2
        else:
            output.append(char)
            index += 1
    return "".join(output)


def is_read_only_sql(statement: str) -> bool:
    if "/*!" in statement:
        return False
    normalized = sql_code_only(statement).strip()
    if normalized.endswith(";"):
        normalized = normalized[:-1].rstrip()
    if ";" in normalized:
        return False
    if re.match(r"(?:SELECT|WITH)\b", normalized, re.IGNORECASE) is None:
        return False
    modifying = re.compile(
        r"\b(?:INSERT|UPDATE|DELETE|REPLACE|CREATE|ALTER|DROP|TRUNCATE|"
        r"CALL|DO|LOAD|GRANT|REVOKE)\b",
        re.IGNORECASE,
    )
    side_effects = re.compile(
        r"\b(?:INTO|OUTFILE|DUMPFILE|FOR\s+(?:UPDATE|SHARE)|LOCK\s+IN|"
        r"GET_LOCK|RELEASE_LOCK|SLEEP|BENCHMARK|LOAD_FILE)\b",
        re.IGNORECASE,
    )
    return modifying.search(normalized) is None and side_effects.search(normalized) is None


def verify_analytical_queries_are_read_only() -> None:
    from analytics.sql_analysis.run_queries import parse_queries

    query_path = ROOT / "database" / "analytical_queries.sql"
    queries = parse_queries(query_path.read_text(encoding="utf-8"))
    if len(queries) != EXPECTED_QUERIES:
        raise SystemExit(
            f"Expected {EXPECTED_QUERIES} analytical queries; found {len(queries)}."
        )
    unsafe = [
        query["query_id"]
        for query in queries
        if not is_read_only_sql(query["sql"])
    ]
    if unsafe:
        raise SystemExit(
            "Refusing SQL analysis because these queries are not read-only "
            "(SELECT/WITH): " + ", ".join(unsafe)
        )


def provision_new_database(database: str) -> int:
    from analytics.config import ConfigurationError, get_settings
    from scripts.setup_database import IDENTIFIER, admin_connection

    if not IDENTIFIER.fullmatch(database):
        raise SystemExit("Database name must contain only letters, digits and underscores.")
    try:
        settings = get_settings()
    except ConfigurationError as exc:
        raise SystemExit(f"Configuration error: {exc}") from exc
    if database != settings.mysql_database:
        raise SystemExit("Requested database must match MYSQL_DATABASE in local configuration.")
    configured_database(database)
    if not settings.mysql_admin_user:
        raise SystemExit("MYSQL_ADMIN_USER is required for database/account provisioning.")

    import pymysql

    try:
        admin = admin_connection(settings)
    except pymysql.MySQLError as exc:
        code = exc.args[0] if exc.args else "unknown"
        raise SystemExit(
            f"Could not inspect the configured MySQL server; error code {code}; "
            "credentials and connection details suppressed."
        ) from exc
    try:
        with admin.cursor() as cursor:
            cursor.execute("SELECT VERSION()")
            version = str(cursor.fetchone()[0])
            if "mariadb" in version.casefold():
                raise SystemExit(
                    f"Refusing database setup: server product is MariaDB ({version}); "
                    "Oracle MySQL is required."
                )
            cursor.execute(
                "SELECT COUNT(*) FROM information_schema.schemata WHERE schema_name = %s",
                (database,),
            )
            exists = int(cursor.fetchone()[0]) > 0
    except pymysql.MySQLError as exc:
        code = exc.args[0] if exc.args else "unknown"
        raise SystemExit(
            f"Could not inspect the configured MySQL server; error code {code}; "
            "credentials and connection details suppressed."
        ) from exc
    finally:
        admin.close()
    if exists:
        raise SystemExit(
            f"Refusing setup: database {database!r} already exists. "
            "This command creates new targets only and never resets an existing database."
        )

    return run_step(
        "Create and provision new database",
        sys.executable,
        "scripts/setup_database.py",
        "--database",
        database,
    )


def assert_empty_import_target(engine, expected_database: str) -> None:
    from sqlalchemy import text

    with engine.connect() as connection:
        version, connected_database = connection.execute(
            text("SELECT VERSION(), DATABASE()")
        ).one()
        if "mariadb" in str(version).casefold():
            raise RuntimeError(
                f"Refusing import: server product is MariaDB ({version}); Oracle MySQL is required."
            )
        if connected_database != expected_database:
            raise RuntimeError(
                "Connected schema does not match the explicitly selected database."
            )
        existing = {
            row[0]
            for row in connection.execute(
                text(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = DATABASE() AND table_type = 'BASE TABLE'"
                )
            )
        }
        missing = sorted(set(BASE_TABLES) - existing)
        if missing:
            raise RuntimeError(
                "Target schema is incomplete; missing tables: " + ", ".join(missing)
            )
        counts = {
            table: int(connection.execute(text(f"SELECT COUNT(*) FROM `{table}`")).scalar_one())
            for table in IMPORT_DATA_TABLES
        }
    ensure_no_imported_rows(counts)


def ensure_no_imported_rows(counts: dict[str, int]) -> None:
    populated = {table: count for table, count in counts.items() if count > 0}
    if populated:
        details = ", ".join(f"{table}={count}" for table, count in populated.items())
        raise RuntimeError(
            f"Refusing import because target already contains imported data ({details}). "
            "This workflow does not replace existing rows."
        )


def import_into_empty_target(args: argparse.Namespace) -> int:
    from sqlalchemy import create_engine
    from sqlalchemy.exc import SQLAlchemyError

    if not args.confirm_target_empty:
        raise SystemExit(
            "Import writes to MySQL. Re-run with --confirm-target-empty only after "
            "verifying the configured database is the intended empty target."
        )
    settings = configured_database(args.database)
    engine = create_engine(settings.database_url, pool_pre_ping=True, future=True)
    try:
        assert_empty_import_target(engine, settings.mysql_database)
    except RuntimeError as exc:
        raise SystemExit(str(exc)) from exc
    except SQLAlchemyError as exc:
        original = getattr(exc, "orig", None)
        code = original.args[0] if original is not None and getattr(original, "args", ()) else None
        suffix = f"; error code {code}" if code is not None else ""
        raise SystemExit(
            f"Could not verify an empty import target: {type(exc).__name__}{suffix}; "
            "credentials and connection details suppressed."
        ) from exc
    finally:
        engine.dispose()

    command = [sys.executable, "scripts/import_data.py"]
    if args.csv:
        command.extend(["--csv", args.csv])
    return run_step("Import into verified empty target", *command)


def build_project_report() -> int:
    report_dir = ROOT / "data" / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    deliverables = {
        "Automation execution log": report_dir / "businesspulse_automation.jsonl",
        "Cleaned listings": ROOT / "data" / "processed" / "cleaned_business_listings.csv",
        "Validation summary": report_dir / "validation_summary.csv",
        "SQL query index": report_dir / "sql_query_results_index.csv",
        "EDA report": ROOT / "docs" / "eda_report.md",
        "Opportunity summary": report_dir / "coverage_summary.csv",
        "Reconciliation report": report_dir / "reconciliation_report.md",
        "Power BI implementation checklist": ROOT / "powerbi" / "implementation_checklist.json",
        "Power BI project": ROOT / "powerbi" / "BusinessPulse.pbip",
        "Power BI PBIX": ROOT / "powerbi" / "BusinessPulse.pbix",
        "Executive Overview screenshot": (
            ROOT / "powerbi" / "screenshots" / "01_executive_overview.png"
        ),
        "Geographic Market Analysis screenshot": (
            ROOT / "powerbi" / "screenshots" / "02_geographic_market_analysis.png"
        ),
        "Data Quality Analysis screenshot": (
            ROOT / "powerbi" / "screenshots" / "03_data_quality_analysis.png"
        ),
        "Market Opportunity Analysis screenshot": (
            ROOT / "powerbi" / "screenshots" / "04_market_opportunity_analysis.png"
        ),
    }
    results = [
        {
            "deliverable": label,
            "path": str(path.relative_to(ROOT)).replace("\\", "/"),
            "status": "available" if path.exists() else "not generated",
        }
        for label, path in deliverables.items()
    ]
    (report_dir / "businesspulse_report_index.json").write_text(
        json.dumps({"generated_at_utc": datetime.now(timezone.utc).isoformat(),
                    "deliverables": results}, indent=2) + "\n",
        encoding="utf-8",
    )
    lines = [
        "# BusinessPulse generated deliverables",
        "",
        "This index reports file presence only; it does not assert live database "
        "or Power BI Desktop validation.",
        "",
        "| Deliverable | Status | Path |",
        "|---|---|---|",
    ]
    lines.extend(
        f"| {item['deliverable']} | {item['status']} | `{item['path']}` |"
        for item in results
    )
    (report_dir / "businesspulse_report_index.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
    print(f"Generated report index: {report_dir / 'businesspulse_report_index.md'}")
    return 0


def workflow_plan(args: argparse.Namespace) -> list[PlannedStage]:
    if args.include_import and not args.database:
        raise SystemExit("--include-import requires an explicit --database target.")
    if args.include_import and not args.confirm_target_empty:
        raise SystemExit(
            "--include-import requires --confirm-target-empty after verifying the target."
        )
    if args.database:
        configured_database(args.database)
    return [
        PlannedStage("preflight"),
        PlannedStage(
            "clean",
            None if args.confirm_regenerate else "requires --confirm-regenerate",
        ),
        PlannedStage("validate"),
        PlannedStage(
            "import",
            None if args.include_import else "database write is opt-in; use --include-import",
        ),
        PlannedStage(
            "sql-analysis",
            None if args.database else "requires explicit --database selection",
        ),
        PlannedStage("eda"),
        PlannedStage(
            "business-insights",
            None if args.database else "requires explicit --database selection",
        ),
        PlannedStage(
            "reconciliation",
            None if args.database else "requires explicit --database selection",
        ),
        PlannedStage("reporting"),
    ]


def execute_stage(name: str, args: argparse.Namespace) -> int:
    missing = missing_dependencies(name)
    if missing:
        print(f"Missing dependencies for {name}: {', '.join(missing)}")
        return 1

    if name == "preflight":
        failed = check_repository()
        if getattr(args, "check_database", False):
            if not getattr(args, "database", None):
                raise SystemExit("--check-database requires an explicit --database target.")
            failed = check_database(args.database) or failed
        return int(failed)
    if name == "clean":
        if not getattr(args, "confirm_regenerate", False):
            raise SystemExit(
                "Cleaning replaces derived outputs; pass --confirm-regenerate."
            )
        return run_step("Cleaning", sys.executable, "-m", "analytics.cleaning.run_cleaning")
    if name == "validate":
        return run_step(
            "Validation", sys.executable, "-m", "analytics.validation.run_validation"
        )
    if name == "setup":
        if not args.confirm_database_create or not args.confirm_account_provisioning:
            raise SystemExit(
                "Setup creates a database and provisions accounts. Both "
                "--confirm-database-create and --confirm-account-provisioning are required."
            )
        configured_database(args.database)
        return provision_new_database(args.database)
    if name == "import":
        if getattr(args, "dry_run", False):
            command = [sys.executable, "scripts/import_data.py", "--dry-run"]
            if args.csv:
                command.extend(["--csv", args.csv])
            return run_step("Validate import CSV without database access", *command)
        if not args.confirm_target_empty:
            raise SystemExit(
                "Import writes to MySQL; pass --confirm-target-empty only after verifying "
                "the selected empty target."
            )
        return import_into_empty_target(args)
    if name == "sql-analysis":
        settings = configured_database(args.database)
        verify_target_mysql(settings)
        verify_analytical_queries_are_read_only()
        return run_step(
            "Analytical SQL", sys.executable, "-m", "analytics.sql_analysis.run_queries"
        )
    if name == "eda":
        return run_step("Exploratory analysis", sys.executable, "-m", "analytics.eda.run_eda")
    if name == "business-insights":
        settings = configured_database(args.database)
        verify_target_mysql(settings)
        return run_step(
            "Business insights",
            sys.executable,
            "-m",
            "analytics.business_insights.opportunity_analysis",
        )
    if name == "reconciliation":
        settings = configured_database(args.database)
        verify_target_mysql(settings)
        return run_step(
            "Reconciliation", sys.executable, "scripts/verify_reconciliation.py"
        )
    if name == "reporting":
        return build_project_report()
    raise SystemExit(f"Unsupported workflow stage: {name}")


def run_command(args: argparse.Namespace) -> int:
    if args.command == "workflow":
        plan = workflow_plan(args)
    else:
        if args.command == "clean" and not args.confirm_regenerate:
            raise SystemExit(
                "Cleaning replaces derived outputs. Re-run with --confirm-regenerate."
            )
        if args.command == "setup" and (
            not args.confirm_database_create or not args.confirm_account_provisioning
        ):
            raise SystemExit(
                "Setup creates a database and provisions accounts. Both "
                "--confirm-database-create and --confirm-account-provisioning are required."
            )
        if args.command == "import" and not args.dry_run and not args.confirm_target_empty:
            raise SystemExit(
                "Import writes to MySQL; pass --confirm-target-empty only after "
                "verifying the selected empty target."
            )
        stage_name = {
            "analyze": "sql-analysis",
            "insights": "business-insights",
            "business-insights": "business-insights",
            "reconcile": "reconciliation",
            "eda": "eda",
            "report": "reporting",
        }.get(args.command, args.command)
        plan = [PlannedStage(stage_name)]

    return run_stage_plan(plan, lambda name: execute_stage(name, args))


def main() -> None:
    args = build_parser().parse_args()
    raise SystemExit(run_command(args))


if __name__ == "__main__":
    main()
