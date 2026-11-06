"""Reusable, explainable cleaning and validation logic.

Design principles
-----------------
* Raw values are preserved in data/raw/business_listings_raw.csv.
* Suspicious records are rejected with a reason, not silently dropped.
* Missing phone/address values stay missing; we never invent contact data.
* Every derived flag has a documented, testable rule.
"""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone
from difflib import SequenceMatcher
from typing import Any

import pandas as pd

from analytics.constants import (
    CATEGORIES,
    CITY_METADATA,
    REQUIRED_FIELDS,
    SOURCE_METADATA,
    SOURCE_NAME,
)

# ---------------------------------------------------------------------------
# Canonical values and aliases
# ---------------------------------------------------------------------------

CITY_ALIASES: dict[str, str] = {
    "pune": "Pune",
    "poona": "Pune",
    "mumbai": "Mumbai",
    "bombay": "Mumbai",
    "bengaluru": "Bengaluru",
    "bangalore": "Bengaluru",
    "delhi": "Delhi",
    "new delhi": "Delhi",
    "ncr": "Delhi",
    "hyderabad": "Hyderabad",
    "chennai": "Chennai",
    "madras": "Chennai",
    "kolkata": "Kolkata",
    "calcutta": "Kolkata",
    "ahmedabad": "Ahmedabad",
    "jaipur": "Jaipur",
    "surat": "Surat",
    "lucknow": "Lucknow",
    "chandigarh": "Chandigarh",
}

CATEGORY_ALIASES: dict[str, str] = {
    "food & beverage": "Food & Beverage",
    "food and beverage": "Food & Beverage",
    "food": "Food & Beverage",
    "restaurant": "Food & Beverage",
    "retail": "Retail",
    "shop": "Retail",
    "health & pharmacy": "Health & Pharmacy",
    "health and pharmacy": "Health & Pharmacy",
    "health": "Health & Pharmacy",
    "pharmacy": "Health & Pharmacy",
    "finance & banking": "Finance & Banking",
    "finance and banking": "Finance & Banking",
    "finance": "Finance & Banking",
    "professional services": "Professional Services",
    "professional": "Professional Services",
    "hospitality": "Hospitality",
    "hotel": "Hospitality",
    "beauty & personal care": "Beauty & Personal Care",
    "beauty and personal care": "Beauty & Personal Care",
    "beauty": "Beauty & Personal Care",
    "automotive": "Automotive",
    "education & training": "Education & Training",
    "education and training": "Education & Training",
    "education": "Education & Training",
    "fitness & recreation": "Fitness & Recreation",
    "fitness and recreation": "Fitness & Recreation",
    "fitness": "Fitness & Recreation",
    "home & repair services": "Home & Repair Services",
    "home and repair services": "Home & Repair Services",
    "home repair": "Home & Repair Services",
    "other services": "Other Services",
    "other": "Other Services",
}

GENERIC_NAMES: frozenset[str] = frozenset(
    {
        "",
        "-",
        "--",
        "n/a",
        "na",
        "none",
        "null",
        "unknown",
        "shop",
        "store",
        "business",
        "restaurant",
        "cafe",
        "hotel",
        "bank",
        "pharmacy",
        "hospital",
        "clinic",
        "office",
        "company",
        "market",
        "supermarket",
        "yes",
    }
)

# ---------------------------------------------------------------------------
# OSM tag -> category mapping
# ---------------------------------------------------------------------------

FOOD_AMENITIES = {
    "restaurant",
    "cafe",
    "fast_food",
    "bar",
    "pub",
    "food_court",
    "ice_cream",
    "biergarten",
}
FOOD_SHOPS = {
    "bakery",
    "butcher",
    "greengrocer",
    "confectionery",
    "cheese",
    "meat",
    "fish",
    "seafood",
    "delicatessen",
    "beverages",
    "alcohol",
    "wine",
    "coffee",
    "tea",
    "spices",
    "health_food",
    "farm",
}
BEAUTY_SHOPS = {
    "beauty",
    "hairdresser",
    "massage",
    "tattoo",
    "piercing",
    "cosmetics",
    "perfumery",
    "nail_salon",
}
AUTO_SHOPS = {
    "car",
    "car_repair",
    "car_parts",
    "motorcycle",
    "motorcycle_repair",
    "tyres",
    "truck",
    "truck_repair",
}
AUTO_AMENITIES = {"fuel", "car_wash", "car_rental", "car_sharing"}
HEALTH_SHOPS = {"chemist", "optician", "medical_supply", "hearing_aids"}
HEALTH_AMENITIES = {
    "pharmacy",
    "hospital",
    "clinic",
    "doctors",
    "dentist",
    "veterinary",
}
FINANCE_OFFICES = {"financial", "insurance"}
FINANCE_AMENITIES = {"bank", "bureau_de_change"}
PROFESSIONAL_OFFICES = {
    "lawyer",
    "accountant",
    "estate_agent",
    "architect",
    "engineer",
    "company",
    "it",
    "consulting",
    "employment_agency",
    "surveyor",
    "tax_advisor",
    "travel_agent",
    "yes",
}
PROFESSIONAL_SHOPS = {"estate_agent", "travel_agency", "employment_agency"}
HOSPITALITY_TOURISM = {"hotel", "guest_house", "hostel", "motel", "apartment"}
FITNESS_LEISURE = {"fitness_centre", "sports_centre", "swimming_pool", "stadium"}
FITNESS_AMENITIES = {"cinema", "theatre", "nightclub", "casino"}
EDUCATION_AMENITIES = {
    "driving_school",
    "language_school",
    "music_school",
    "training",
}
EDUCATION_OFFICES = {"educational_institution"}
HOME_REPAIR_SHOPS = {
    "hardware",
    "doityourself",
    "building_materials",
    "paint",
    "electrical",
    "plumbing",
    "garden_centre",
}
OTHER_AMENITIES = {"laundry", "dry_cleaning", "funeral_directors", "vending_machine"}
OTHER_SHOPS = {
    "laundry",
    "dry_cleaning",
    "tailor",
    "pet_grooming",
    "funeral_directors",
    "copy_shop",
    "printing",
    "photo",
    "locksmith",
    "key_cutting",
    "shoe_repair",
    "repair",
}
NON_BUSINESS_OFFICES = {
    "government",
    "political_party",
    "diplomatic",
    "ngo",
    "association",
    "quango",
    "religion",
    "administrative",
}
NON_BUSINESS_AMENITIES = {
    "police",
    "fire_station",
    "townhall",
    "courthouse",
    "post_office",
    "community_centre",
    "social_facility",
    "place_of_worship",
    "school",
    "college",
    "university",
    "kindergarten",
    "public_building",
    "toilets",
    "parking",
    "bus_station",
}
NON_BUSINESS_TOURISM = {
    "information",
    "attraction",
    "museum",
    "artwork",
    "viewpoint",
    "picnic_site",
}
NON_BUSINESS_LEISURE = {"park", "playground", "pitch", "garden"}
NON_BUSINESS_SHOPS = {"vacant", "charity", "no"}


def is_non_business(tags: dict[str, Any]) -> bool:
    """Exclude clearly public/non-commercial POIs from the business frame."""
    return (
        str(tags.get("office", "")).lower() in NON_BUSINESS_OFFICES
        or str(tags.get("amenity", "")).lower() in NON_BUSINESS_AMENITIES
        or str(tags.get("tourism", "")).lower() in NON_BUSINESS_TOURISM
        or str(tags.get("leisure", "")).lower() in NON_BUSINESS_LEISURE
        or str(tags.get("shop", "")).lower() in NON_BUSINESS_SHOPS
    )


def map_category(tags: dict[str, Any]) -> tuple[str | None, str | None]:
    """Map OSM tags to one of the 12 analytical categories.

    Returns (category, rule). ``rule`` records which tag produced the
    classification, e.g. ``amenity=restaurant``. The mapping is deliberately
    deterministic and documented in docs/methodology.md.
    """
    amenity = str(tags.get("amenity", "")).lower()
    shop = str(tags.get("shop", "")).lower()
    office = str(tags.get("office", "")).lower()
    tourism = str(tags.get("tourism", "")).lower()
    leisure = str(tags.get("leisure", "")).lower()
    healthcare = str(tags.get("healthcare", "")).lower()
    craft = str(tags.get("craft", "")).lower()

    if is_non_business(tags):
        return None, "excluded_non_business"

    if amenity in FOOD_AMENITIES:
        return "Food & Beverage", f"amenity={amenity}"
    if shop in FOOD_SHOPS:
        return "Food & Beverage", f"shop={shop}"
    if shop in BEAUTY_SHOPS:
        return "Beauty & Personal Care", f"shop={shop}"
    if shop in AUTO_SHOPS:
        return "Automotive", f"shop={shop}"
    if amenity in AUTO_AMENITIES:
        return "Automotive", f"amenity={amenity}"
    if shop in HEALTH_SHOPS:
        return "Health & Pharmacy", f"shop={shop}"
    if amenity in HEALTH_AMENITIES:
        return "Health & Pharmacy", f"amenity={amenity}"
    if healthcare:
        return "Health & Pharmacy", f"healthcare={healthcare}"
    if amenity in FINANCE_AMENITIES:
        return "Finance & Banking", f"amenity={amenity}"
    if office in FINANCE_OFFICES:
        return "Finance & Banking", f"office={office}"
    if tourism in HOSPITALITY_TOURISM:
        return "Hospitality", f"tourism={tourism}"
    if amenity in FITNESS_AMENITIES:
        return "Fitness & Recreation", f"amenity={amenity}"
    if leisure in FITNESS_LEISURE:
        return "Fitness & Recreation", f"leisure={leisure}"
    if amenity in EDUCATION_AMENITIES:
        return "Education & Training", f"amenity={amenity}"
    if office in EDUCATION_OFFICES:
        return "Education & Training", f"office={office}"
    if shop in HOME_REPAIR_SHOPS:
        return "Home & Repair Services", f"shop={shop}"
    if craft:
        return "Home & Repair Services", f"craft={craft}"
    if shop in OTHER_SHOPS or amenity in OTHER_AMENITIES:
        return "Other Services", f"shop={shop}" if shop else f"amenity={amenity}"
    if office in PROFESSIONAL_OFFICES:
        return "Professional Services", f"office={office}"
    if shop in PROFESSIONAL_SHOPS:
        return "Professional Services", f"shop={shop}"
    if shop:
        return "Retail", f"shop={shop}"
    if office:
        return "Professional Services", f"office={office}"
    if tourism:
        return "Hospitality", f"tourism={tourism}"
    if leisure:
        return "Fitness & Recreation", f"leisure={leisure}"
    return None, None


# ---------------------------------------------------------------------------
# Text / field normalisation
# ---------------------------------------------------------------------------


def is_blank(value: Any) -> bool:
    if value is None:
        return True
    try:
        if pd.isna(value):
            return True
    except (TypeError, ValueError):
        pass
    return str(value).strip() == ""


def clean_text(value: Any) -> str:
    """Unicode-normalise, collapse whitespace and trim. Never fills blanks."""
    if is_blank(value):
        return ""
    text = unicodedata.normalize("NFKC", str(value))
    text = text.replace("\u200b", "").replace("\ufeff", "")
    text = re.sub(r"[\r\n\t]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def normalize_business_name(value: Any) -> str:
    text = clean_text(value)
    text = text.strip("\"'`.,;:- ")
    text = re.sub(r"\s+", " ", text)
    return text


def name_key(value: Any) -> str:
    """Comparison key: lowercase alphanumerics only."""
    text = unicodedata.normalize("NFKD", clean_text(value)).casefold()
    return re.sub(r"[^a-z0-9]+", "", text)


def normalize_city(value: Any) -> str | None:
    text = clean_text(value).casefold()
    if not text:
        return None
    text = re.sub(r"\s+", " ", text)
    return CITY_ALIASES.get(text)


def normalize_category(value: Any) -> str | None:
    text = clean_text(value).casefold()
    if not text:
        return None
    return CATEGORY_ALIASES.get(text)


def normalize_phone(value: Any) -> str:
    """Normalise a published phone number without inventing digits.

    Rules: use the first number if several are separated by ; or /, strip an
    extension, keep a leading +, drop punctuation/spaces, convert 00 prefix to
    +. Empty/invalid placeholders return an empty string.
    """
    text = clean_text(value)
    if not text:
        return ""
    if text.casefold() in {"n/a", "na", "none", "null", "-", "--", "0", "000"}:
        return ""
    # Several numbers: the first one is kept, and the original is preserved
    # in phone_raw so the decision is auditable.
    text = re.split(r"\s*[;/]\s*", text)[0]
    text = re.sub(r"\s*(?:ext\.?|extension|x)\s*\d+\s*$", "", text, flags=re.IGNORECASE)
    text = text.strip()
    if not text:
        return ""
    plus = text.startswith("+")
    digits = re.sub(r"\D", "", text)
    if text.startswith("00"):
        digits = digits[2:] if digits.startswith("00") else digits
        plus = True
    if not digits:
        return ""
    # Do not keep absurdly long strings as if they were phone numbers.
    if len(digits) > 18:
        return ""
    return ("+" if plus else "") + digits


def phone_digits(value: Any) -> str:
    return re.sub(r"\D", "", clean_text(value))


def is_valid_phone(value: Any) -> bool:
    """Explainable phone rule: 7-15 digits, no letters (extension allowed),
    not a repeated single-digit string."""
    raw = clean_text(value)
    if not raw:
        return False
    if raw.casefold() in {"n/a", "na", "none", "null", "-", "--", "0", "000"}:
        return False
    without_extension = re.sub(
        r"\s*(?:ext\.?|extension|x)\s*\d+\s*$", "", raw, flags=re.IGNORECASE
    )
    if re.search(r"[A-Za-z]", without_extension):
        return False
    digits = phone_digits(without_extension)
    if not 7 <= len(digits) <= 15:
        return False
    if len(set(digits)) <= 1:
        return False
    return True


def normalize_address(value: Any) -> str:
    text = clean_text(value)
    if not text:
        return ""
    text = re.sub(r"\s*,\s*", ", ", text)
    text = re.sub(r"(?:,\s*){2,}", ", ", text)
    text = text.strip(" ,;")
    return text


def address_key(value: Any) -> str:
    text = unicodedata.normalize("NFKD", clean_text(value)).casefold()
    return re.sub(r"[^a-z0-9]+", "", text)


def is_valid_address(value: Any) -> bool:
    """A usable address needs at least two tokens and six characters."""
    text = normalize_address(value)
    if len(text) < 6:
        return False
    tokens = [token for token in re.split(r"[\s,]+", text) if token]
    return len(tokens) >= 2


def build_address(tags: dict[str, Any]) -> str:
    """Assemble an address from published OSM address components only."""
    full = clean_text(tags.get("addr:full"))
    if full:
        return normalize_address(full)
    parts: list[str] = []
    housenumber = clean_text(tags.get("addr:housenumber"))
    street = clean_text(tags.get("addr:street"))
    place = clean_text(tags.get("addr:place"))
    suburb = clean_text(tags.get("addr:suburb")) or clean_text(
        tags.get("addr:neighbourhood")
    )
    postcode = clean_text(tags.get("addr:postcode"))
    if street:
        parts.append(f"{housenumber} {street}".strip())
    elif place:
        parts.append(f"{housenumber} {place}".strip())
    if suburb and not any(suburb.casefold() in p.casefold() for p in parts):
        parts.append(suburb)
    if postcode:
        parts.append(postcode)
    return normalize_address(", ".join(dict.fromkeys(parts)))


def extract_phone(tags: dict[str, Any]) -> str:
    for key in ("phone", "contact:phone", "mobile", "contact:mobile", "telephone"):
        value = clean_text(tags.get(key))
        if value:
            return value
    return ""


# ---------------------------------------------------------------------------
# Duplicate detection
# ---------------------------------------------------------------------------


def _find(parent: list[int], i: int) -> int:
    while parent[i] != i:
        parent[i] = parent[parent[i]]
        i = parent[i]
    return i


def _union(parent: list[int], i: int, j: int) -> None:
    root_i, root_j = _find(parent, i), _find(parent, j)
    if root_i != root_j:
        parent[max(root_i, root_j)] = min(root_i, root_j)


def detect_duplicates(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Flag exact and potential duplicates using transparent pairwise rules.

    Exact duplicate (kept in the dataset, flagged for audit) when two records
    share a normalised name and city and either:
      * the same non-empty normalised address, or
      * the same non-empty phone number.
    Chains with the same brand but different branches/phones are not exact
    duplicates.

    Potential duplicate when the name and city match and normalised addresses
    are highly similar (>= 0.90) but not identical. These are reported for
    review but do not count toward the duplicate rate.
    """
    work = df.copy()
    work["duplicate_flag"] = False
    work["duplicate_group"] = ""
    work["duplicate_reason"] = ""
    work["kept_business_id"] = ""
    work["potential_duplicate_flag"] = False
    work["potential_duplicate_reason"] = ""

    if work.empty:
        return work, pd.DataFrame()

    work = work.sort_values(
        ["city", "name_key", "address_key", "phone_key", "business_id"]
    ).reset_index(drop=True)

    duplicate_rows: list[dict[str, Any]] = []
    potential_rows: list[dict[str, Any]] = []
    group_number = 0

    for (city, nkey), group in work.groupby(["city", "name_key"], sort=False, dropna=False):
        if len(group) < 2 or not nkey:
            continue
        indices = list(group.index)
        parent = list(range(len(indices)))
        reasons: dict[tuple[int, int], set[str]] = {}

        for a in range(len(indices)):
            row_a = work.loc[indices[a]]
            for b in range(a + 1, len(indices)):
                row_b = work.loc[indices[b]]
                matched: set[str] = set()
                if row_a["address_key"] and row_a["address_key"] == row_b["address_key"]:
                    matched.add("address")
                if row_a["phone_key"] and row_a["phone_key"] == row_b["phone_key"]:
                    matched.add("phone")
                if matched:
                    _union(parent, a, b)
                    key = (a, b)
                    reasons[key] = matched

        # Collect connected components with more than one record.
        components: dict[int, list[int]] = {}
        for pos, idx in enumerate(indices):
            components.setdefault(_find(parent, pos), []).append(idx)
        for members in components.values():
            if len(members) < 2:
                continue
            group_number += 1
            group_id = f"DUP-{group_number:04d}"
            members = sorted(members, key=lambda i: str(work.loc[i, "source_record_id"]))
            canonical = members[0]
            for member in members:
                if member == canonical:
                    work.at[member, "duplicate_group"] = group_id
                    work.at[member, "kept_business_id"] = work.at[member, "business_id"]
                    continue
                matched_fields = "name + city + address" if (
                    work.loc[member, "address_key"]
                    and work.loc[member, "address_key"] == work.loc[canonical, "address_key"]
                ) else "name + city + phone"
                work.at[member, "duplicate_flag"] = True
                work.at[member, "duplicate_group"] = group_id
                work.at[member, "kept_business_id"] = work.at[canonical, "business_id"]
                work.at[member, "duplicate_reason"] = matched_fields
                duplicate_rows.append(
                    {
                        "business_id": work.at[member, "business_id"],
                        "business_name": work.at[member, "business_name"],
                        "city": work.at[member, "city"],
                        "address": work.at[member, "address"],
                        "phone": work.at[member, "phone"],
                        "source": work.at[member, "source"],
                        "source_record_id": work.at[member, "source_record_id"],
                        "duplicate_group": group_id,
                        "kept_business_id": work.at[canonical, "business_id"],
                        "duplicate_reason": matched_fields,
                    }
                )

        # Potential duplicates: same name/city, similar but non-identical
        # addresses. This is a review aid only and is not counted as a
        # duplicate in the quality KPIs.
        for a in range(len(indices)):
            row_a = work.loc[indices[a]]
            if not row_a["address_key"]:
                continue
            for b in range(a + 1, len(indices)):
                row_b = work.loc[indices[b]]
                if not row_b["address_key"]:
                    continue
                if row_a["address_key"] == row_b["address_key"]:
                    continue
                if row_a["phone_key"] and row_a["phone_key"] == row_b["phone_key"]:
                    continue
                similarity = SequenceMatcher(None, row_a["address_key"], row_b["address_key"]).ratio()
                if similarity >= 0.90:
                    for left, right in ((indices[a], indices[b]), (indices[b], indices[a])):
                        if not work.at[left, "potential_duplicate_flag"]:
                            work.at[left, "potential_duplicate_flag"] = True
                            work.at[left, "potential_duplicate_reason"] = (
                                f"Similar address to {work.at[right, 'business_id']} "
                                f"(similarity {similarity:.2f}); not counted as duplicate"
                            )
                    potential_rows.append(
                        {
                            "business_id": row_a["business_id"],
                            "business_name": row_a["business_name"],
                            "city": row_a["city"],
                            "address": row_a["address"],
                            "other_business_id": row_b["business_id"],
                            "other_address": row_b["address"],
                            "address_similarity": round(similarity, 4),
                            "phone_a": row_a["phone"],
                            "phone_b": row_b["phone"],
                        }
                    )

    work = work.sort_values("business_id").reset_index(drop=True)
    return work, pd.DataFrame(potential_rows)


# ---------------------------------------------------------------------------
# Quality scoring
# ---------------------------------------------------------------------------


def compute_quality_score(
    missing_phone: bool,
    missing_address: bool,
    duplicate_flag: bool,
    phone_valid: bool,
    address_valid: bool,
) -> int:
    """Documented 0-100 quality score.

    Starts at 100 and subtracts:
      -20 missing phone, -25 missing address, -20 duplicate,
      -10 present but malformed phone, -5 present but unusable address.
    """
    score = 100
    if missing_phone:
        score -= 20
    if missing_address:
        score -= 25
    if duplicate_flag:
        score -= 20
    if not missing_phone and not phone_valid:
        score -= 10
    if not missing_address and not address_valid:
        score -= 5
    return max(0, score)


def validation_status(
    missing_phone: bool,
    missing_address: bool,
    duplicate_flag: bool,
    phone_valid: bool,
    address_valid: bool,
) -> str:
    if duplicate_flag:
        return "needs_review"
    if missing_phone or missing_address:
        return "needs_review"
    if not phone_valid or not address_valid:
        return "needs_review"
    return "valid"


def is_complete(
    missing_phone: bool,
    missing_address: bool,
    duplicate_flag: bool,
    phone_valid: bool,
    address_valid: bool,
) -> bool:
    return not (
        missing_phone
        or missing_address
        or duplicate_flag
        or not phone_valid
        or not address_valid
    )


# ---------------------------------------------------------------------------
# Full cleaning pipeline
# ---------------------------------------------------------------------------


@dataclass
class CleaningResult:
    cleaned: pd.DataFrame
    rejected: pd.DataFrame
    duplicates: pd.DataFrame
    potential_duplicates: pd.DataFrame
    log: pd.DataFrame


def _reject(
    row: pd.Series,
    reason: str,
    rejected: list[dict[str, Any]],
    now: str,
) -> None:
    rejected.append(
        {
            "business_id": row.get("business_id", ""),
            "business_name": row.get("business_name", ""),
            "city": row.get("city", ""),
            "category": row.get("category", ""),
            "source": row.get("source", ""),
            "source_record_id": row.get("source_record_id", ""),
            "rejection_reason": reason,
            "raw_record": json.dumps(
                {k: (None if is_blank(v) else v) for k, v in row.to_dict().items()},
                ensure_ascii=False,
                default=str,
            ),
            "rejected_at": now,
        }
    )


def clean_dataframe(raw: pd.DataFrame, collection_date_fallback: str | None = None) -> CleaningResult:
    """Clean a raw listings dataframe and return all audit outputs."""
    if raw.empty:
        raise ValueError("Raw dataset is empty; run data collection first.")

    missing_required = [field for field in REQUIRED_FIELDS if field not in raw.columns]
    if missing_required:
        raise ValueError(f"Raw dataset is missing required columns: {missing_required}")

    raw = raw.copy()
    optional_defaults = {
        "address": "",
        "phone": "",
        "phone_raw": "",
        "latitude": None,
        "longitude": None,
        "state_name": "",
        "country": "India",
        "source_record_url": "",
        "category_raw": "",
        "osm_tags_json": "",
    }
    for field, default in optional_defaults.items():
        if field not in raw.columns:
            raw[field] = default

    if not collection_date_fallback:
        collection_date_fallback = datetime.now(timezone.utc).date().isoformat()

    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    rejected: list[dict[str, Any]] = []
    kept: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    seen_source_ids: set[str] = set()

    for _, row in raw.iterrows():
        raw_row = row.copy()

        business_id = clean_text(row.get("business_id"))
        source_record_id = clean_text(row.get("source_record_id"))
        source = clean_text(row.get("source"))
        business_name = normalize_business_name(row.get("business_name"))[:255]
        city = normalize_city(row.get("city"))
        category = normalize_category(row.get("category"))
        tags: dict[str, Any] = {}
        if not is_blank(row.get("osm_tags_json")):
            try:
                parsed = json.loads(str(row.get("osm_tags_json")))
                if isinstance(parsed, dict):
                    tags = parsed
            except (TypeError, ValueError, json.JSONDecodeError):
                tags = {}
        if not category and tags:
            category, _ = map_category(tags)

        reasons: list[str] = []
        if not business_id:
            reasons.append("missing business_id")
        if not business_name:
            reasons.append("missing business_name")
        elif business_name.casefold() in GENERIC_NAMES or name_key(business_name) in GENERIC_NAMES:
            reasons.append("generic/placeholder business_name")
        if not category:
            reasons.append("unmapped/invalid category")
        if not city:
            reasons.append("invalid or missing city")
        if source != SOURCE_NAME:
            reasons.append(f"invalid source: {source or '(blank)'}")
        if not source_record_id:
            reasons.append("missing source_record_id")
        if not clean_text(row.get("collection_date")):
            reasons.append("missing collection_date")
        if not clean_text(row.get("created_at")):
            reasons.append("missing created_at")
        if business_id in seen_ids:
            reasons.append("duplicate business_id")
        if source_record_id in seen_source_ids:
            reasons.append("duplicate source_record_id (collection overlap)")

        if reasons:
            _reject(raw_row, "; ".join(reasons), rejected, now)
            continue

        seen_ids.add(business_id)
        seen_source_ids.add(source_record_id)

        phone_raw = clean_text(row.get("phone_raw")) or clean_text(row.get("phone"))
        phone = normalize_phone(phone_raw)[:64]
        address = normalize_address(row.get("address"))[:500]
        phone_valid = is_valid_phone(phone_raw)
        address_valid = is_valid_address(address)
        missing_phone = not bool(phone)
        missing_address = not bool(address)

        state_name = clean_text(row.get("state_name"))
        country = clean_text(row.get("country")) or "India"
        if city in CITY_METADATA:
            state_name = state_name or str(CITY_METADATA[city]["state_name"])
            country = country or str(CITY_METADATA[city]["country"])

        latitude: float | None
        longitude: float | None
        try:
            latitude = float(row.get("latitude")) if not is_blank(row.get("latitude")) else None
            longitude = float(row.get("longitude")) if not is_blank(row.get("longitude")) else None
            if latitude is not None and not -90 <= latitude <= 90:
                latitude = None
            if longitude is not None and not -180 <= longitude <= 180:
                longitude = None
        except (TypeError, ValueError):
            latitude, longitude = None, None

        created_at = clean_text(row.get("created_at"))
        collection_date = clean_text(row.get("collection_date")) or collection_date_fallback
        try:
            collection_date = pd.to_datetime(collection_date).date().isoformat()
        except (TypeError, ValueError):
            _reject(raw_row, "invalid collection_date", rejected, now)
            continue
        if not created_at:
            created_at = f"{collection_date}T00:00:00+00:00"

        kept.append(
            {
                "business_id": business_id,
                "business_name": business_name,
                "name_key": name_key(business_name),
                "category": category,
                "category_raw": clean_text(row.get("category_raw")),
                "city": city,
                "state_name": state_name,
                "country": country,
                "address": address,
                "address_key": address_key(address),
                "phone": phone,
                "phone_raw": phone_raw,
                "phone_key": phone_digits(phone),
                "phone_valid": bool(phone_valid),
                "address_valid": bool(address_valid),
                "missing_phone": bool(missing_phone),
                "missing_address": bool(missing_address),
                "latitude": latitude,
                "longitude": longitude,
                "source": source,
                "source_type": SOURCE_METADATA["source_type"],
                "source_record_id": source_record_id[:64],
                "source_record_url": clean_text(row.get("source_record_url"))[:500],
                "collection_date": collection_date,
                "created_at": created_at,
            }
        )

    cleaned = pd.DataFrame(kept)
    rejected_df = pd.DataFrame(rejected)
    log_rows: list[dict[str, Any]] = [
        {
            "step": "raw records loaded",
            "rows_before": len(raw),
            "rows_after": len(raw),
            "rows_removed": 0,
            "notes": "Original raw file preserved",
        }
    ]

    if cleaned.empty:
        return CleaningResult(
            cleaned=cleaned,
            rejected=rejected_df,
            duplicates=pd.DataFrame(),
            potential_duplicates=pd.DataFrame(),
            log=pd.DataFrame(log_rows),
        )

    cleaned, potential_df = detect_duplicates(cleaned)
    cleaned["duplicate_flag"] = cleaned["duplicate_flag"].astype(bool)
    cleaned["potential_duplicate_flag"] = cleaned["potential_duplicate_flag"].astype(bool)

    cleaned["quality_score"] = [
        compute_quality_score(
            bool(row.missing_phone),
            bool(row.missing_address),
            bool(row.duplicate_flag),
            bool(row.phone_valid),
            bool(row.address_valid),
        )
        for row in cleaned.itertuples()
    ]
    cleaned["is_complete"] = [
        is_complete(
            bool(row.missing_phone),
            bool(row.missing_address),
            bool(row.duplicate_flag),
            bool(row.phone_valid),
            bool(row.address_valid),
        )
        for row in cleaned.itertuples()
    ]
    cleaned["validation_status"] = [
        validation_status(
            bool(row.missing_phone),
            bool(row.missing_address),
            bool(row.duplicate_flag),
            bool(row.phone_valid),
            bool(row.address_valid),
        )
        for row in cleaned.itertuples()
    ]
    cleaned["quality_band"] = [
        "High (80-100)" if float(score) >= 80 else "Medium (60-79)" if float(score) >= 60 else "Low (<60)"
        for score in cleaned["quality_score"]
    ]
    cleaned["audit_timestamp"] = now
    cleaned["cleaning_notes"] = ""
    cleaned.loc[cleaned["duplicate_flag"], "cleaning_notes"] = "Exact duplicate flagged; retained for audit"
    cleaned.loc[
        (~cleaned["duplicate_flag"]) & cleaned["potential_duplicate_flag"], "cleaning_notes"
    ] = "Potential duplicate for review; retained"

    duplicates_df = cleaned.loc[
        cleaned["duplicate_flag"],
        [
            "business_id",
            "business_name",
            "city",
            "address",
            "phone",
            "source",
            "source_record_id",
            "duplicate_group",
            "kept_business_id",
            "duplicate_reason",
        ],
    ].copy()

    cleaned = cleaned.sort_values(["city", "category", "business_name"]).reset_index(drop=True)

    log_rows.extend(
        [
            {
                "step": "normalised names, cities, categories, addresses and phones",
                "rows_before": len(raw),
                "rows_after": len(cleaned) + len(rejected_df),
                "rows_removed": 0,
                "notes": "Derived keys added; raw values retained in raw dataset",
            },
            {
                "step": "rejected records",
                "rows_before": len(raw),
                "rows_after": len(cleaned),
                "rows_removed": len(rejected_df),
                "notes": "Reasons recorded in rejected_records.csv",
            },
            {
                "step": "exact duplicates flagged",
                "rows_before": len(cleaned),
                "rows_after": len(cleaned),
                "rows_removed": 0,
                "notes": (
                    f"{len(duplicates_df)} records flagged and retained for data-quality analysis; "
                    "not silently deleted"
                ),
            },
            {
                "step": "potential duplicates flagged",
                "rows_before": len(cleaned),
                "rows_after": len(cleaned),
                "rows_removed": 0,
                "notes": f"{int(cleaned['potential_duplicate_flag'].sum())} records flagged for review only",
            },
        ]
    )

    return CleaningResult(
        cleaned=cleaned,
        rejected=rejected_df,
        duplicates=duplicates_df,
        potential_duplicates=potential_df,
        log=pd.DataFrame(log_rows),
    )


def category_is_valid(value: Any) -> bool:
    return normalize_category(value) in CATEGORIES


def city_is_valid(value: Any) -> bool:
    return normalize_city(value) is not None
