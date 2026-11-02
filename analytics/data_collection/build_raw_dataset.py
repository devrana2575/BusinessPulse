"""Build the combined raw CSV from cached Overpass responses.

The raw CSV is the immutable input to the cleaning pipeline. It preserves
source IDs, URLs, raw phones, raw addresses and the original OSM tag JSON.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from analytics.cleaning.cleaning import (
    GENERIC_NAMES,
    build_address,
    clean_text,
    extract_phone,
    map_category,
    name_key,
)
from analytics.constants import (
    CITY_METADATA,
    RAW_CSV,
    RAW_DIR,
    SOURCE_METADATA,
    SOURCE_NAME,
    ensure_directories,
)
from analytics.data_collection.collect_osm_data import CACHE_DIR, MANIFEST_PATH, slug


def first_name(tags: dict[str, Any]) -> str:
    for key in ("name", "name:en", "brand"):
        value = clean_text(tags.get(key))
        if value:
            return value
    return ""


def source_business_id(osm_type: str, osm_id: int) -> str:
    prefix = {"node": "N", "way": "W", "relation": "R"}.get(osm_type, "X")
    return f"BP-OSM-{prefix}-{osm_id}"


def build_rows() -> tuple[pd.DataFrame, dict[str, Any]]:
    if not MANIFEST_PATH.exists():
        raise SystemExit(
            "No collection manifest found. Run "
            "`python -m analytics.data_collection.collect_osm_data` first."
        )
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    entries = manifest.get("queries", [])
    if not entries:
        raise SystemExit("Collection manifest has no query entries.")

    manifest_by_file = {Path(entry["cache_file"]).name: entry for entry in entries}
    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, int]] = set()
    seen_source_ids: set[str] = set()
    skipped = {
        "unnamed": 0,
        "non_business_or_unmapped": 0,
        "generic_name": 0,
        "duplicate_osm_element": 0,
        "missing_coordinates": 0,
    }
    files_scanned = 0

    for path in sorted(CACHE_DIR.glob("*.json")):
        if path.name.endswith(".meta.json"):
            continue
        if "__" not in path.stem:
            continue
        city_slug, group_key = path.stem.split("__", 1)
        matched_city = next((c for c in CITY_METADATA if slug(c) == city_slug), None)
        if not matched_city:
            continue
        entry = manifest_by_file.get(path.name, {})
        collected_at = entry.get("collected_at") or manifest.get(
            "collection_finished_at", datetime.now(timezone.utc).isoformat()
        )
        collection_date = str(collected_at)[:10]
        city_info = CITY_METADATA[matched_city]
        files_scanned += 1
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        for element in payload.get("elements", []):
            osm_type = str(element.get("type", ""))
            osm_id = element.get("id")
            if not osm_type or osm_id is None:
                continue
            key = (osm_type, int(osm_id))
            if key in seen:
                skipped["duplicate_osm_element"] += 1
                continue
            tags = element.get("tags") or {}
            if not isinstance(tags, dict):
                tags = {}
            name = first_name(tags)
            if not name:
                skipped["unnamed"] += 1
                continue
            if name.casefold() in GENERIC_NAMES or name_key(name) in GENERIC_NAMES:
                skipped["generic_name"] += 1
                continue
            category, rule = map_category(tags)
            if not category:
                skipped["non_business_or_unmapped"] += 1
                continue
            lat = element.get("lat")
            lon = element.get("lon")
            center = element.get("center") or {}
            if lat is None:
                lat = center.get("lat")
            if lon is None:
                lon = center.get("lon")
            try:
                lat = float(lat) if lat is not None else None
                lon = float(lon) if lon is not None else None
            except (TypeError, ValueError):
                lat, lon = None, None
            if lat is None or lon is None:
                skipped["missing_coordinates"] += 1
                continue
            if not (-90 <= lat <= 90 and -180 <= lon <= 180):
                skipped["missing_coordinates"] += 1
                continue
            seen.add(key)
            business_id = source_business_id(osm_type, int(osm_id))
            if business_id in seen_source_ids:
                skipped["duplicate_osm_element"] += 1
                continue
            seen_source_ids.add(business_id)
            address = build_address(tags)
            phone_raw = extract_phone(tags)
            rows.append(
                {
                    "business_id": business_id,
                    "business_name": name,
                    "category": category,
                    "category_raw": rule,
                    "city": matched_city,
                    "state_name": city_info["state_name"],
                    "country": city_info["country"],
                    "address": address,
                    "phone": phone_raw,
                    "phone_raw": phone_raw,
                    "latitude": lat,
                    "longitude": lon,
                    "source": SOURCE_NAME,
                    "source_type": SOURCE_METADATA["source_type"],
                    "source_record_id": f"{osm_type}/{osm_id}",
                    "source_record_url": f"https://www.openstreetmap.org/{osm_type}/{osm_id}",
                    "collection_date": collection_date,
                    "created_at": f"{collection_date}T00:00:00+00:00",
                    "collection_group": group_key,
                    "osm_tags_json": json.dumps(tags, ensure_ascii=False, sort_keys=True),
                }
            )

    df = pd.DataFrame(rows)
    if df.empty:
        raise SystemExit("No usable records built from the cached Overpass responses.")

    df = df.drop_duplicates("business_id", keep="first")
    df = df.sort_values(
        ["city", "category", "business_name", "source_record_id"]
    ).reset_index(drop=True)
    summary = {
        "raw_rows": int(len(df)),
        "cities": int(df["city"].nunique()),
        "categories": int(df["category"].nunique()),
        "sources": int(df["source"].nunique()),
        "collection_date": str(df["collection_date"].mode().iloc[0]),
        "files_scanned": files_scanned,
        "skipped": skipped,
        "source_name": SOURCE_NAME,
        "license": SOURCE_METADATA["license_name"],
        "attribution": SOURCE_METADATA["attribution"],
        "built_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    return df, summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Build raw BusinessPulse CSV")
    parser.add_argument("--output", default=str(RAW_CSV))
    args = parser.parse_args()
    ensure_directories()
    df, summary = build_rows()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output, index=False, encoding="utf-8")
    summary_path = RAW_DIR / "raw_build_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"Raw records: {len(df)}")
    print(f"Cities: {summary['cities']}; categories: {summary['categories']}")
    print(f"Written: {output}")
    print(f"Summary: {summary_path}")


if __name__ == "__main__":
    main()
