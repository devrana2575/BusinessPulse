"""Import the cleaned BusinessPulse CSV into MySQL in one transaction.

Guarantees:
* file extension and size are checked before reading,
* the same file cannot be imported twice (SHA-256 + unique DB constraint),
* dimension lookups are resolved by name,
* listing + data-quality audit rows are committed atomically,
* rejected rows are recorded, never silently discarded.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from analytics.cleaning.cleaning import is_blank, normalize_city, normalize_category  # noqa: E402
from analytics.config import ConfigurationError, get_settings  # noqa: E402
from analytics.constants import (  # noqa: E402
    CLEANED_CSV,
    REJECTED_CSV,
    REPORTS_DIR,
    SOURCE_METADATA,
    SOURCE_NAME,
    ensure_directories,
)
from analytics.validation.validation import validate_dataframe  # noqa: E402

MAX_FILE_BYTES = 25 * 1024 * 1024
IMPORT_REQUIRED_COLUMNS = {
    "business_id",
    "business_name",
    "category",
    "city",
    "address",
    "phone",
    "source",
    "source_record_id",
    "collection_date",
    "created_at",
    "missing_phone",
    "missing_address",
    "duplicate_flag",
    "potential_duplicate_flag",
    "phone_valid",
    "address_valid",
    "is_complete",
    "validation_status",
    "quality_score",
}

logger = logging.getLogger("businesspulse.import")


def configure_logging() -> None:
    ensure_directories()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(REPORTS_DIR / "import_log.txt", encoding="utf-8"),
            logging.StreamHandler(),
        ],
        force=True,
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_csv_path(path: Path) -> None:
    if not path.exists() or not path.is_file():
        raise ValueError(f"CSV file not found: {path}")
    if path.suffix.lower() != ".csv":
        raise ValueError("Only .csv files are accepted")
    if path.stat().st_size > MAX_FILE_BYTES:
        raise ValueError("CSV exceeds the 25 MB import limit")
    if path.stat().st_size == 0:
        raise ValueError("CSV is empty")


def bool_value(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    try:
        if pd.isna(value):
            return False
    except (TypeError, ValueError):
        pass
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def to_naive_utc(value: Any) -> datetime:
    if is_blank(value):
        return datetime.now(timezone.utc).replace(tzinfo=None)
    parsed = pd.to_datetime(value, utc=True)
    if isinstance(parsed, pd.Series):
        parsed = parsed.iloc[0]
    return parsed.to_pydatetime().replace(tzinfo=None)


def nullable_text(value: Any) -> str | None:
    return None if is_blank(value) else str(value).strip()


def nullable_float(value: Any) -> float | None:
    if is_blank(value):
        return None
    return float(value)


def _get_or_create_city(conn, city_name: str, row: pd.Series) -> int:
    conn.execute(
        text(
            "INSERT IGNORE INTO dim_city (city_name, state_name, country) "
            "VALUES (:city_name, :state_name, :country)"
        ),
        {
            "city_name": city_name,
            "state_name": nullable_text(row.get("state_name")) or "",
            "country": nullable_text(row.get("country")) or "India",
        },
    )
    city_id = conn.execute(
        text("SELECT city_id FROM dim_city WHERE city_name = :city_name"),
        {"city_name": city_name},
    ).scalar_one()
    return int(city_id)


def _get_or_create_category(conn, category_name: str) -> int:
    conn.execute(
        text("INSERT IGNORE INTO dim_category (category_name) VALUES (:category_name)"),
        {"category_name": category_name},
    )
    category_id = conn.execute(
        text("SELECT category_id FROM dim_category WHERE category_name = :category_name"),
        {"category_name": category_name},
    ).scalar_one()
    return int(category_id)


def _get_or_create_source(conn, source_name: str) -> int:
    conn.execute(
        text(
            "INSERT IGNORE INTO dim_source "
            "(source_name, source_type, source_url, license_name, license_url, attribution) "
            "VALUES (:source_name, :source_type, :source_url, :license_name, :license_url, :attribution)"
        ),
        {
            "source_name": source_name,
            "source_type": SOURCE_METADATA["source_type"],
            "source_url": SOURCE_METADATA["source_url"],
            "license_name": SOURCE_METADATA["license_name"],
            "license_url": SOURCE_METADATA["license_url"],
            "attribution": SOURCE_METADATA["attribution"],
        },
    )
    source_id = conn.execute(
        text("SELECT source_id FROM dim_source WHERE source_name = :source_name"),
        {"source_name": source_name},
    ).scalar_one()
    return int(source_id)


def _insert_reject(
    conn,
    batch_id: int,
    row: pd.Series,
    reason: str,
    raw_record: dict[str, Any] | None = None,
) -> None:
    payload = raw_record if isinstance(raw_record, dict) else {
        key: (None if is_blank(value) else str(value)) for key, value in row.to_dict().items()
    }
    conn.execute(
        text(
            "INSERT INTO listing_rejects "
            "(import_batch_id, source_record_id, business_name, city_name, category_name, "
            " rejection_reason, raw_record) "
            "VALUES (:batch_id, :source_record_id, :business_name, :city_name, "
            "        :category_name, :reason, :raw_record)"
        ),
        {
            "batch_id": batch_id,
            "source_record_id": nullable_text(row.get("source_record_id")),
            "business_name": nullable_text(row.get("business_name")),
            "city_name": nullable_text(row.get("city")),
            "category_name": nullable_text(row.get("category")),
            "reason": reason[:500],
            "raw_record": json.dumps(payload, ensure_ascii=False, default=str),
        },
    )


def import_cleaned_csv(
    csv_path: Path,
    engine: Engine,
    *,
    replace_data: bool = False,
    rejects_csv: Path | None = None,
    include_pipeline_rejects: bool = True,
) -> dict[str, Any]:
    validate_csv_path(csv_path)
    file_hash = sha256_file(csv_path)
    try:
        df = pd.read_csv(csv_path, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    except (pd.errors.ParserError, pd.errors.EmptyDataError) as exc:
        raise ValueError(f"Malformed CSV: {exc}") from exc

    missing_columns = sorted(IMPORT_REQUIRED_COLUMNS - set(df.columns))
    if missing_columns:
        raise ValueError(f"Cleaned CSV is missing required columns: {missing_columns}")

    validation = validate_dataframe(df)
    blocking = sorted(validation.blocking_indices)
    valid_df = df.drop(index=blocking).copy()
    reject_reasons: dict[int, str] = {}
    error_issues = validation.issues[validation.issues["severity"] == "error"]
    for row_index, group in error_issues.groupby("row_index"):
        reject_reasons[int(row_index)] = "; ".join(group["message"].astype(str).unique())[:500]

    logger.info(
        "Import file=%s hash=%s rows=%s valid=%s blocking=%s",
        csv_path.name, file_hash[:12], len(df), len(valid_df), len(blocking),
    )

    summary: dict[str, Any] = {
        "file": csv_path.name,
        "file_hash": file_hash,
        "rows_received": len(df),
        "rows_valid": len(valid_df),
        "rows_rejected": len(blocking),
        "rows_inserted": 0,
        "rows_flagged_duplicate": int(valid_df["duplicate_flag"].map(bool_value).sum()),
        "batch_id": None,
    }

    with engine.begin() as conn:
        if replace_data:
            logger.warning("Replacing all existing listing/audit/reject/batch rows")
            conn.execute(text("DELETE FROM data_quality_audit"))
            conn.execute(text("DELETE FROM listing_master"))
            conn.execute(text("DELETE FROM listing_rejects"))
            conn.execute(text("DELETE FROM import_batches"))

        source_id = _get_or_create_source(conn, SOURCE_NAME)
        existing = conn.execute(
            text(
                "SELECT batch_id FROM import_batches "
                "WHERE source_id = :source_id AND file_hash = :file_hash LIMIT 1"
            ),
            {"source_id": source_id, "file_hash": file_hash},
        ).first()
        if existing:
            raise ValueError(
                f"This exact cleaned CSV was already imported (batch_id={existing[0]}). "
                "Use --replace-data only when you intentionally want to rebuild the dataset."
            )

        batch_result = conn.execute(
            text(
                "INSERT INTO import_batches "
                "(source_id, file_name, file_hash, rows_received, rows_rejected, status, notes) "
                "VALUES (:source_id, :file_name, :file_hash, :rows_received, :rows_rejected, "
                "        'started', :notes)"
            ),
            {
                "source_id": source_id,
                "file_name": csv_path.name,
                "file_hash": file_hash,
                "rows_received": len(df),
                "rows_rejected": len(blocking),
                "notes": "BusinessPulse transactional import",
            },
        )
        batch_id = int(batch_result.lastrowid)
        summary["batch_id"] = batch_id

        city_ids: dict[str, int] = {}
        category_ids: dict[str, int] = {}
        for _, row in valid_df.iterrows():
            city = normalize_city(row.get("city"))
            category = normalize_category(row.get("category"))
            if not city or not category:
                # This should already be blocked by validation, but fail closed.
                raise ValueError(f"Unresolved dimension for {row.get('business_id')}")
            if city not in city_ids:
                city_ids[city] = _get_or_create_city(conn, city, row)
            if category not in category_ids:
                category_ids[category] = _get_or_create_category(conn, category)

        inserted = 0
        for _, row in valid_df.iterrows():
            city_id = city_ids[normalize_city(row["city"])]  # type: ignore[index]
            category_id = category_ids[normalize_category(row["category"])]  # type: ignore[index]
            listing_result = conn.execute(
                text(
                    "INSERT INTO listing_master "
                    "(business_id, business_name, category_id, city_id, address, phone, "
                    " source_id, source_record_id, collection_date, latitude, longitude, created_at) "
                    "VALUES (:business_id, :business_name, :category_id, :city_id, :address, :phone, "
                    "        :source_id, :source_record_id, :collection_date, :latitude, :longitude, :created_at)"
                ),
                {
                    "business_id": str(row["business_id"]).strip()[:40],
                    "business_name": str(row["business_name"]).strip()[:255],
                    "category_id": category_id,
                    "city_id": city_id,
                    "address": nullable_text(row.get("address")),
                    "phone": nullable_text(row.get("phone")),
                    "source_id": source_id,
                    "source_record_id": str(row["source_record_id"]).strip()[:64],
                    "collection_date": pd.to_datetime(row["collection_date"]).date(),
                    "latitude": nullable_float(row.get("latitude")),
                    "longitude": nullable_float(row.get("longitude")),
                    "created_at": to_naive_utc(row.get("created_at")),
                },
            )
            listing_id = int(listing_result.lastrowid)
            conn.execute(
                text(
                    "INSERT INTO data_quality_audit "
                    "(listing_id, missing_phone, missing_address, duplicate_flag, "
                    " potential_duplicate_flag, phone_valid, address_valid, is_complete, "
                    " validation_status, quality_score, audit_timestamp) "
                    "VALUES (:listing_id, :missing_phone, :missing_address, :duplicate_flag, "
                    "        :potential_duplicate_flag, :phone_valid, :address_valid, :is_complete, "
                    "        :validation_status, :quality_score, :audit_timestamp)"
                ),
                {
                    "listing_id": listing_id,
                    "missing_phone": bool_value(row.get("missing_phone")),
                    "missing_address": bool_value(row.get("missing_address")),
                    "duplicate_flag": bool_value(row.get("duplicate_flag")),
                    "potential_duplicate_flag": bool_value(row.get("potential_duplicate_flag")),
                    "phone_valid": bool_value(row.get("phone_valid")),
                    "address_valid": bool_value(row.get("address_valid")),
                    "is_complete": bool_value(row.get("is_complete")),
                    "validation_status": str(row.get("validation_status", "needs_review")),
                    "quality_score": float(row.get("quality_score", 0)),
                    "audit_timestamp": to_naive_utc(row.get("audit_timestamp")),
                },
            )
            inserted += 1

        # Blocking validation rows
        for row_index in blocking:
            if 0 <= row_index < len(df):
                _insert_reject(
                    conn,
                    batch_id,
                    df.iloc[row_index],
                    reject_reasons.get(row_index, "Validation error"),
                )

        # Rows rejected earlier in the cleaning stage (e.g. unnamed POIs)
        pipeline_rejects = 0
        if include_pipeline_rejects and rejects_csv and rejects_csv.exists():
            try:
                rejects_df = pd.read_csv(
                    rejects_csv, dtype=str, keep_default_na=False, encoding="utf-8-sig"
                )
            except pd.errors.EmptyDataError:
                rejects_df = pd.DataFrame()
            for _, row in rejects_df.iterrows():
                raw_record = None
                if not is_blank(row.get("raw_record")):
                    try:
                        raw_record = json.loads(str(row.get("raw_record")))
                    except json.JSONDecodeError:
                        raw_record = None
                _insert_reject(
                    conn,
                    batch_id,
                    row,
                    str(row.get("rejection_reason", "Rejected in cleaning stage"))[:500],
                    raw_record=raw_record,
                )
                pipeline_rejects += 1

        total_rejected = len(blocking) + pipeline_rejects
        conn.execute(
            text(
                "UPDATE import_batches SET rows_inserted = :inserted, rows_rejected = :rejected, "
                "rows_flagged_duplicate = :duplicates, status = 'completed', "
                "notes = :notes WHERE batch_id = :batch_id"
            ),
            {
                "inserted": inserted,
                "rejected": total_rejected,
                "duplicates": summary["rows_flagged_duplicate"],
                "notes": (
                    f"Imported {inserted} listings; {len(blocking)} validation rejects; "
                    f"{pipeline_rejects} cleaning-stage rejects"
                )[:500],
                "batch_id": batch_id,
            },
        )
        summary["rows_inserted"] = inserted
        summary["rows_rejected"] = total_rejected
        summary["rows_rejected_validation"] = len(blocking)
        summary["rows_rejected_pipeline"] = pipeline_rejects

    logger.info("Import complete: %s", summary)
    return summary


def database_counts(engine: Engine) -> dict[str, int]:
    with engine.connect() as conn:
        return {
            "listings": int(conn.execute(text("SELECT COUNT(*) FROM listing_master")).scalar_one()),
            "audits": int(conn.execute(text("SELECT COUNT(*) FROM data_quality_audit")).scalar_one()),
            "batches": int(conn.execute(text("SELECT COUNT(*) FROM import_batches")).scalar_one()),
            "views": int(
                conn.execute(
                    text(
                        "SELECT COUNT(*) FROM information_schema.tables "
                        "WHERE table_schema = DATABASE() AND table_type = 'VIEW'"
                    )
                ).scalar_one()
            ),
        }


def main() -> None:
    parser = argparse.ArgumentParser(description="Import cleaned listings into MySQL")
    parser.add_argument("--csv", default=str(CLEANED_CSV))
    parser.add_argument("--rejects", default=str(REJECTED_CSV))
    parser.add_argument("--replace-data", action="store_true")
    parser.add_argument("--skip-pipeline-rejects", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    configure_logging()

    csv_path = Path(args.csv)
    rejects_path = Path(args.rejects) if args.rejects else None
    if args.dry_run:
        validate_csv_path(csv_path)
        df = pd.read_csv(csv_path, dtype=str, keep_default_na=False, encoding="utf-8-sig")
        result = validate_dataframe(df)
        print(f"Rows: {len(df)}")
        print(f"Validation errors: {result.summary['error_count']}")
        print(f"Blocking rows: {result.summary['blocking_rows']}")
        print(f"Warnings: {result.summary['warning_count']}")
        print(f"Completeness: {result.summary['completeness_pct']}%")
        return

    try:
        settings = get_settings()
    except ConfigurationError as exc:
        raise SystemExit(f"Configuration error: {exc}") from exc
    engine = create_engine(settings.database_url, pool_pre_ping=True, future=True)
    try:
        summary = import_cleaned_csv(
            csv_path,
            engine,
            replace_data=args.replace_data,
            rejects_csv=rejects_path,
            include_pipeline_rejects=not args.skip_pipeline_rejects,
        )
        print(json.dumps(summary, indent=2, default=str))
        print(json.dumps(database_counts(engine), indent=2))
    except ValueError as exc:
        raise SystemExit(f"Import failed: {exc}") from exc
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
