"""Run the deterministic BusinessPulse pipeline end to end.

Usage (PowerShell):
    python scripts/run_pipeline.py --replace-data

The collector is not run by default because a full polite Overpass refresh can
take a long time. Use ``--collect`` when the cache is missing or intentionally
being refreshed. The script stops at the first failing step and prints the exact
command it ran.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run_step(label: str, module: str, *args: str) -> None:
    command = [sys.executable, "-m", module, *args]
    print("\n" + "=" * 78)
    print(f"[{label}] " + " ".join(command))
    print("=" * 78, flush=True)
    completed = subprocess.run(command, cwd=ROOT)
    if completed.returncode != 0:
        raise SystemExit(
            f"Pipeline stopped at {label!r} with exit code {completed.returncode}."
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the BusinessPulse pipeline")
    parser.add_argument(
        "--collect",
        action="store_true",
        help="Run the polite full Overpass collection before building raw data",
    )
    parser.add_argument(
        "--replace-data",
        action="store_true",
        help="Replace existing listings/audits in MySQL during import",
    )
    parser.add_argument("--skip-eda", action="store_true")
    parser.add_argument("--skip-sql", action="store_true")
    parser.add_argument("--skip-opportunity", action="store_true")
    parser.add_argument("--skip-reconciliation", action="store_true")
    args = parser.parse_args()

    if args.collect:
        run_step("collect OSM", "analytics.data_collection.collect_osm_data")
    run_step("build raw", "analytics.data_collection.build_raw_dataset")
    run_step("clean", "analytics.cleaning.run_cleaning")
    run_step("validate", "analytics.validation.run_validation")

    import_args = ["--replace-data"] if args.replace_data else []
    run_step("import MySQL", "scripts.import_data", *import_args)

    if not args.skip_sql:
        run_step("analytical SQL", "analytics.sql_analysis.run_queries")
    if not args.skip_eda:
        run_step("EDA", "analytics.eda.run_eda")
    if not args.skip_opportunity:
        run_step(
            "opportunity",
            "analytics.business_insights.opportunity_analysis",
        )
    if not args.skip_reconciliation:
        run_step("reconciliation", "scripts.verify_reconciliation")

    print("\nPipeline complete. Review generated reports and the honest limitations.")


if __name__ == "__main__":
    main()
