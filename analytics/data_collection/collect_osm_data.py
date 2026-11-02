"""Collect real OpenStreetMap POIs through the public Overpass API.

This script is intentionally polite:
* bounded per-city/group queries,
* one request at a time with a delay,
* exponential backoff on 429/5xx/timeouts,
* HTTP responses cached so a rerun does not re-query unnecessarily.

Provenance and licence: © OpenStreetMap contributors, ODbL 1.0.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

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
    OSM_QUERY_GROUPS,
    RAW_DIR,
    SOURCE_METADATA,
    SOURCE_NAME,
    ensure_directories,
)

DEFAULT_ENDPOINT = os.getenv(
    "OVERPASS_ENDPOINT", "https://overpass-api.de/api/interpreter"
)
USER_AGENT = (
    "BusinessPulsePortfolio/1.0 "
    "(educational data-analyst project; contact: local portfolio owner)"
)
CACHE_DIR = RAW_DIR / "osm_responses"
MANIFEST_PATH = RAW_DIR / "collection_manifest.json"
RAW_CSV = RAW_DIR / "business_listings_raw.csv"


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.casefold()).strip("_")


def bbox_string(city: str) -> str:
    south, west, north, east = CITY_METADATA[city]["bbox"]
    return f"{south},{west},{north},{east}"


def build_query(city: str, group: dict[str, Any]) -> str:
    bbox = bbox_string(city)
    statements: list[str] = []
    for tag, regex in group["filters"]:
        if regex is None:
            statements.append(f'  nwr["{tag}"]({bbox});')
        else:
            statements.append(f'  nwr["{tag}"~"^({regex})$"]({bbox});')
    joined = "\n".join(statements)
    return (
        "[out:json][timeout:120];\n"
        "(\n"
        f"{joined}\n"
        ");\n"
        f"out center {int(group['limit'])};\n"
    )


def cache_path(city: str, group_key: str) -> Path:
    return CACHE_DIR / f"{slug(city)}__{group_key}.json"


def metadata_path(city: str, group_key: str) -> Path:
    """Sidecar metadata keeps cache provenance when endpoints change."""
    return CACHE_DIR / f"{slug(city)}__{group_key}.meta.json"


def write_cache_metadata(
    city: str,
    group_key: str,
    endpoint: str,
    collected_at: str,
    element_count: int,
    attempts: int,
) -> None:
    metadata_path(city, group_key).write_text(
        json.dumps(
            {
                "city": city,
                "group": group_key,
                "endpoint": endpoint,
                "collected_at": collected_at,
                "http_status": 200,
                "element_count": element_count,
                "attempts": attempts,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def fetch_group(
    session: requests.Session,
    endpoint: str,
    city: str,
    group: dict[str, Any],
    max_attempts: int,
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    query = build_query(city, group)
    record: dict[str, Any] = {
        "city": city,
        "group": group["key"],
        "endpoint": endpoint,
        "query": query,
        "attempted_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "attempts": 0,
        "status": "failed",
        "http_status": None,
        "element_count": 0,
        "error": "",
        "cache_file": str(cache_path(city, group["key"]).relative_to(RAW_DIR.parent)),
    }
    last_error = ""
    for attempt in range(1, max_attempts + 1):
        record["attempts"] = attempt
        try:
            response = session.post(
                endpoint,
                data={"data": query},
                headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
                timeout=150,
            )
            record["http_status"] = response.status_code
            if response.status_code == 200:
                try:
                    payload = response.json()
                except ValueError as exc:
                    last_error = f"invalid JSON: {exc}"
                else:
                    elements = payload.get("elements", [])
                    if isinstance(elements, list):
                        if not elements:
                            # A broad city/group query returning zero elements is
                            # almost always a mirror/quota problem, not a real empty
                            # market. Treat it as a failed attempt rather than
                            # recording a misleading successful empty response.
                            last_error = (
                                "HTTP 200 but zero elements; treated as a failed query"
                            )
                        else:
                            cache_path(city, group["key"]).write_text(
                                json.dumps(payload, ensure_ascii=False), encoding="utf-8"
                            )
                            record["status"] = "ok"
                            record["element_count"] = len(elements)
                            record["collected_at"] = datetime.now(timezone.utc).isoformat(
                                timespec="seconds"
                            )
                            record["error"] = ""
                            write_cache_metadata(
                                city,
                                group["key"],
                                endpoint,
                                record["collected_at"],
                                len(elements),
                                attempt,
                            )
                            return payload, record
                    else:
                        last_error = "response has no elements list"
            else:
                last_error = f"HTTP {response.status_code}: {response.text[:200]}"
        except requests.RequestException as exc:
            last_error = f"{type(exc).__name__}: {exc}"

        record["error"] = last_error
        if attempt < max_attempts:
            # Exponential backoff with jitter; public Overpass instances are
            # shared infrastructure and must not be hammered.
            delay = min(60, 8 * (2 ** (attempt - 1))) + random.uniform(0, 3)
            print(
                f"  attempt {attempt} failed ({last_error[:100]}); "
                f"retrying in {delay:.1f}s..."
            )
            time.sleep(delay)
    return None, record


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect OSM business POIs via Overpass")
    parser.add_argument(
        "--cities",
        default=",".join(CITY_METADATA.keys()),
        help="Comma-separated city names (default: all 12)",
    )
    parser.add_argument("--endpoint", default=DEFAULT_ENDPOINT)
    parser.add_argument("--refresh", action="store_true", help="Ignore cached responses")
    parser.add_argument("--delay", type=float, default=2.0, help="Seconds between requests")
    parser.add_argument("--max-attempts", type=int, default=6)
    args = parser.parse_args()

    ensure_directories()
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cities = [c.strip() for c in args.cities.split(",") if c.strip()]
    unknown = [c for c in cities if c not in CITY_METADATA]
    if unknown:
        raise SystemExit(f"Unknown city/cities: {unknown}. Known: {list(CITY_METADATA)}")

    session = requests.Session()
    manifest: dict[str, Any] = {
        "project": "BusinessPulse",
        "source_name": SOURCE_NAME,
        "source_type": SOURCE_METADATA["source_type"],
        "source_url": SOURCE_METADATA["source_url"],
        "license_name": SOURCE_METADATA["license_name"],
        "license_url": SOURCE_METADATA["license_url"],
        "attribution": SOURCE_METADATA["attribution"],
        "collection_started_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "endpoint": args.endpoint,
        "requested_endpoint": args.endpoint,
        "endpoint_note": (
            "Per-query endpoint fields record cache origin or the endpoint used for "
            "a new request. The public Overpass main endpoint was at capacity when "
            "collection was resumed, so a public mirror was used for missing groups; "
            "all data remains OpenStreetMap."
        ),
        "cities": cities,
        "groups": [group["key"] for group in OSM_QUERY_GROUPS],
        "queries": [],
        "notes": (
            "Real OpenStreetMap POIs collected through the public Overpass API. "
            "This is not a complete business census and is not customer-demand data."
        ),
    }

    request_count = 0
    for city in cities:
        print(f"[{city}]")
        for group in OSM_QUERY_GROUPS:
            path = cache_path(city, group["key"])
            if path.exists() and not args.refresh:
                try:
                    payload = json.loads(path.read_text(encoding="utf-8"))
                    elements = payload.get("elements", [])
                    if isinstance(elements, list):
                        metadata: dict[str, Any] = {}
                        try:
                            metadata = json.loads(
                                metadata_path(city, group["key"]).read_text(encoding="utf-8")
                            )
                        except (ValueError, OSError):
                            metadata = {}
                        collected_at = metadata.get("collected_at") or datetime.fromtimestamp(
                            path.stat().st_mtime, timezone.utc
                        ).isoformat(timespec="seconds")
                        origin = metadata.get("endpoint") or "unknown (pre-metadata cache)"
                        print(
                            f"  {group['key']}: cache ({len(elements)} elements, {origin})"
                        )
                        manifest["queries"].append(
                            {
                                "city": city,
                                "group": group["key"],
                                "endpoint": origin,
                                "status": "cache",
                                "http_status": None,
                                "element_count": len(elements),
                                "attempts": 0,
                                "collected_at": collected_at,
                                "error": "",
                                "cache_file": str(path.relative_to(RAW_DIR.parent)),
                            }
                        )
                        continue
                except (ValueError, OSError):
                    pass
            print(f"  {group['key']}: querying...")
            payload, record = fetch_group(
                session, args.endpoint, city, group, args.max_attempts
            )
            manifest["queries"].append(record)
            request_count += 1
            if payload is None:
                print(f"  {group['key']}: FAILED - {record['error'][:140]}")
            else:
                print(f"  {group['key']}: {record['element_count']} elements")
            time.sleep(max(0.0, args.delay))

    manifest["collection_finished_at"] = datetime.now(timezone.utc).isoformat(
        timespec="seconds"
    )
    manifest["request_count"] = request_count
    manifest["successful_query_entries"] = sum(
        1 for q in manifest["queries"] if q["status"] in {"ok", "cache"}
    )
    manifest["failed_query_entries"] = sum(
        1 for q in manifest["queries"] if q["status"] == "failed"
    )
    manifest["endpoints_observed"] = sorted(
        {
            str(q.get("endpoint"))
            for q in manifest["queries"]
            if q.get("endpoint") and not str(q.get("endpoint")).startswith("unknown")
        }
    )
    MANIFEST_PATH.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"\nManifest written to {MANIFEST_PATH}")
    print(f"Successful/cached query entries: {manifest['successful_query_entries']}")
    print(f"Failed query entries: {manifest['failed_query_entries']}")


if __name__ == "__main__":
    main()
