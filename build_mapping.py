"""
Orchestrator: builds the full SW2 → SW3 mapping table.

1. Loads SW3 data (from cache or API)
2. Parses and classifies SW2 paths
3. For datasets: runs fuzzy matcher → specific SW3 dataset URL or category fallback
4. For categories: applies hardcoded topic mapping → SW3 topic URL
5. For download fileName: extracts code prefix → category → topic URL
6. For export/shortlink: → SW3 homepage
7. For other: → SW3 homepage

Outputs data/mapping.csv
"""

import csv
import os

from config import (
    CODE_PREFIX_TO_CATEGORY,
    DATA_DIR,
    MAPPING_CSV,
    OVERRIDES_CSV,
    SEQUENCE_MATCHER_THRESHOLD,
    SW3_HOME,
    TOKEN_OVERLAP_MIN,
    sw3_dataset_url,
    sw3_topic_url_for_category,
)
from matcher import MatchResult, match_slug
from sw2_path_parser import ParsedPath, parse_paths
from sw3_api_client import load_or_fetch_datasets, load_or_fetch_topics


FIELDNAMES = [
    "sw2_path",
    "sw3_url",
    "match_type",
    "confidence",
    "sw3_title",
    "needs_review",
]


def _load_overrides() -> dict[str, dict]:
    """Load manual review overrides from overrides.csv if it exists."""
    overrides = {}
    if os.path.exists(OVERRIDES_CSV):
        with open(OVERRIDES_CSV, newline="") as f:
            for row in csv.DictReader(f):
                overrides[row["sw2_path"]] = row
    return overrides


def _map_dataset(
    parsed: ParsedPath,
    sw3_datasets: list[dict],
) -> dict:
    """Map a dataset path to an SW3 URL using fuzzy matching."""
    if not parsed.slug:
        return _fallback_to_category(parsed)

    result = match_slug(parsed.slug, sw3_datasets, parsed.category)

    if result.sw3_id and result.confidence >= TOKEN_OVERLAP_MIN:
        needs_review = result.confidence < SEQUENCE_MATCHER_THRESHOLD
        return {
            "sw2_path": parsed.path,
            "sw3_url": sw3_dataset_url(result.sw3_id),
            "match_type": result.match_type,
            "confidence": round(result.confidence, 3),
            "sw3_title": result.sw3_title or "",
            "needs_review": needs_review,
        }

    return _fallback_to_category(parsed)


def _fallback_to_category(parsed: ParsedPath) -> dict:
    """Fall back to the SW3 topic URL for the path's category."""
    if parsed.category:
        sw3_url = sw3_topic_url_for_category(parsed.category)
    else:
        sw3_url = SW3_HOME
    return {
        "sw2_path": parsed.path,
        "sw3_url": sw3_url,
        "match_type": "category_fallback",
        "confidence": 0.0,
        "sw3_title": "",
        "needs_review": False,
    }


def _map_category(parsed: ParsedPath) -> dict:
    """Map a category/navigation path to an SW3 topic URL."""
    if parsed.category:
        sw3_url = sw3_topic_url_for_category(parsed.category)
    else:
        sw3_url = SW3_HOME
    return {
        "sw2_path": parsed.path,
        "sw3_url": sw3_url,
        "match_type": "category",
        "confidence": 1.0,
        "sw3_title": "",
        "needs_review": False,
    }


def _map_download_file(parsed: ParsedPath) -> dict:
    """Map a download file path using code prefix → category → topic."""
    if parsed.code_prefix and parsed.code_prefix in CODE_PREFIX_TO_CATEGORY:
        category = CODE_PREFIX_TO_CATEGORY[parsed.code_prefix]
        sw3_url = sw3_topic_url_for_category(category)
    else:
        sw3_url = SW3_HOME
    return {
        "sw2_path": parsed.path,
        "sw3_url": sw3_url,
        "match_type": "download_prefix",
        "confidence": 0.5,
        "sw3_title": "",
        "needs_review": False,
    }


def _map_to_homepage(parsed: ParsedPath, match_type: str) -> dict:
    """Map a path directly to the SW3 homepage."""
    return {
        "sw2_path": parsed.path,
        "sw3_url": SW3_HOME,
        "match_type": match_type,
        "confidence": 0.0,
        "sw3_title": "",
        "needs_review": False,
    }


def build_mapping() -> list[dict]:
    """Build the complete SW2 → SW3 mapping."""
    print("Loading SW3 data...")
    load_or_fetch_topics()
    sw3_datasets = load_or_fetch_datasets()
    print(f"  {len(sw3_datasets)} SW3 datasets available")

    print("Parsing SW2 paths...")
    parsed_paths = parse_paths()
    print(f"  {len(parsed_paths)} SW2 paths parsed")

    print("Loading overrides...")
    overrides = _load_overrides()
    print(f"  {len(overrides)} manual overrides loaded")

    print("Building mapping...")
    mapping = []
    for parsed in parsed_paths:
        # Check for manual override
        if parsed.path in overrides:
            override = overrides[parsed.path]
            mapping.append({
                "sw2_path": parsed.path,
                "sw3_url": override["sw3_url"],
                "match_type": "manual_override",
                "confidence": 1.0,
                "sw3_title": override.get("sw3_title", ""),
                "needs_review": False,
            })
            continue

        if parsed.path_type == "dataset":
            row = _map_dataset(parsed, sw3_datasets)
        elif parsed.path_type == "category":
            row = _map_category(parsed)
        elif parsed.path_type == "download_file":
            row = _map_download_file(parsed)
        elif parsed.path_type == "download_id":
            row = _map_to_homepage(parsed, "download_id")
        elif parsed.path_type == "export":
            row = _map_to_homepage(parsed, "export")
        elif parsed.path_type == "shortlink":
            row = _map_to_homepage(parsed, "shortlink")
        else:
            row = _map_to_homepage(parsed, "other")

        mapping.append(row)

    return mapping


def write_mapping(mapping: list[dict]) -> None:
    """Write the mapping to CSV."""
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(MAPPING_CSV, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        for row in sorted(mapping, key=lambda r: r["sw2_path"]):
            writer.writerow(row)
    print(f"Mapping written to {MAPPING_CSV} ({len(mapping)} rows)")


def main():
    mapping = build_mapping()
    write_mapping(mapping)

    # Quick summary
    by_type: dict[str, int] = {}
    needs_review = 0
    for row in mapping:
        by_type[row["match_type"]] = by_type.get(row["match_type"], 0) + 1
        if row["needs_review"]:
            needs_review += 1

    print("\nMapping summary:")
    for match_type, count in sorted(by_type.items(), key=lambda x: -x[1]):
        print(f"  {match_type:25s} {count:6d}")
    print(f"\n  Needs review: {needs_review}")


if __name__ == "__main__":
    main()
