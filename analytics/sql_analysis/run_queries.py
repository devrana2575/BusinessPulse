"""Execute every analytical SQL query and export each result set to CSV."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from analytics.config import ConfigurationError, get_settings  # noqa: E402
from analytics.constants import DATABASE_DIR, SQL_RESULTS_DIR, ensure_directories  # noqa: E402

QUERY_FILE = DATABASE_DIR / "analytical_queries.sql"
QUERY_PATTERN = re.compile(r"^-- QUERY:\s*(Q\d+)\s*\|\s*(.+?)\s*$", re.MULTILINE)


def parse_queries(text_content: str) -> list[dict[str, str]]:
    matches = list(QUERY_PATTERN.finditer(text_content))
    queries: list[dict[str, str]] = []
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text_content)
        block = text_content[start:end].strip()
        # Remove leading comment lines from the executable SQL but retain them
        # in the source file for documentation.
        sql_lines = []
        for line in block.splitlines():
            if line.lstrip().startswith("--"):
                continue
            sql_lines.append(line)
        sql = "\n".join(sql_lines).strip()
        queries.append(
            {
                "query_id": match.group(1),
                "title": match.group(2).strip(),
                "sql": sql,
            }
        )
    return queries


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.casefold()).strip("_")[:60]


def run_queries(engine: Engine, selected: set[str] | None = None) -> pd.DataFrame:
    ensure_directories()
    SQL_RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    queries = parse_queries(QUERY_FILE.read_text(encoding="utf-8"))
    if not queries:
        raise SystemExit("No queries found in analytical_queries.sql")
    rows: list[dict] = []
    with engine.connect() as conn:
        for query in queries:
            if selected and query["query_id"] not in selected:
                continue
            output_name = f"{query['query_id']}_{slug(query['title'])}.csv"
            output_path = SQL_RESULTS_DIR / output_name
            print(f"{query['query_id']}: {query['title']}")
            try:
                frame = pd.read_sql(text(query["sql"].rstrip(";")), conn)
                frame.to_csv(output_path, index=False, encoding="utf-8")
                rows.append(
                    {
                        "query_id": query["query_id"],
                        "title": query["title"],
                        "row_count": len(frame),
                        "status": "ok",
                        "error": "",
                        "output_file": str(output_path.relative_to(ROOT)),
                    }
                )
                print(f"  {len(frame)} rows -> {output_path.name}")
            except Exception as exc:  # keep executing later queries for a full audit
                rows.append(
                    {
                        "query_id": query["query_id"],
                        "title": query["title"],
                        "row_count": 0,
                        "status": "failed",
                        "error": str(exc)[:500],
                        "output_file": "",
                    }
                )
                print(f"  FAILED: {exc}")
    summary = pd.DataFrame(rows)
    summary.to_csv(
        SQL_RESULTS_DIR.parent / "sql_query_results_index.csv",
        index=False,
        encoding="utf-8",
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Run BusinessPulse analytical SQL")
    parser.add_argument("--query", action="append", help="Run only this query id, e.g. Q01")
    args = parser.parse_args()
    try:
        settings = get_settings()
    except ConfigurationError as exc:
        raise SystemExit(f"Configuration error: {exc}") from exc
    engine = create_engine(settings.database_url, pool_pre_ping=True, future=True)
    try:
        summary = run_queries(engine, set(args.query) if args.query else None)
    finally:
        engine.dispose()
    failures = int((summary["status"] == "failed").sum()) if not summary.empty else 0
    print(f"\nQueries executed: {len(summary)}; failures: {failures}")
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
