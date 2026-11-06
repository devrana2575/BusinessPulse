"""Validate the cleaned dataset and write machine-readable reports."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from analytics.constants import CLEANED_CSV, REPORTS_DIR, ensure_directories  # noqa: E402
from analytics.validation.validation import validate_dataframe  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate cleaned BusinessPulse listings")
    parser.add_argument("--input", default=str(CLEANED_CSV))
    args = parser.parse_args()

    ensure_directories()
    input_path = Path(args.input)
    if not input_path.exists():
        raise SystemExit(f"Input file not found: {input_path}")

    df = pd.read_csv(input_path, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    result = validate_dataframe(df)
    result.issues.to_csv(REPORTS_DIR / "validation_issues.csv", index=False, encoding="utf-8")
    pd.DataFrame(
        [{"metric": key, "value": value} for key, value in result.summary.items()]
    ).to_csv(REPORTS_DIR / "validation_summary.csv", index=False, encoding="utf-8")

    print(f"Rows checked: {result.summary['rows_checked']}")
    print(f"Errors: {result.summary['error_count']}")
    print(f"Warnings: {result.summary['warning_count']}")
    print(f"Blocking rows: {result.summary['blocking_rows']}")
    print(f"Missing phone: {result.summary['missing_phone_count']} "
          f"({result.summary['missing_phone_pct']}%)")
    print(f"Missing address: {result.summary['missing_address_count']} "
          f"({result.summary['missing_address_pct']}%)")
    print(f"Completeness: {result.summary['completeness_pct']}%")
    print(f"Wrote: {REPORTS_DIR / 'validation_issues.csv'}")
    if result.summary["error_count"]:
        raise SystemExit("Validation found blocking errors; see validation_issues.csv")


if __name__ == "__main__":
    main()
