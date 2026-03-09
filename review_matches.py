"""
Manual review CLI for uncertain matches.

Shows SW2 slug, proposed SW3 match, and confidence score.
Allows accept/reject/search for alternatives.
Writes decisions to data/overrides.csv.
"""

import csv
import os
import sys

from config import MAPPING_CSV, OVERRIDES_CSV, DATA_DIR, sw3_dataset_url
from sw3_api_client import load_or_fetch_datasets
from matcher import normalize_title


def _load_review_candidates() -> list[dict]:
    """Load rows from mapping.csv that need review."""
    if not os.path.exists(MAPPING_CSV):
        print(f"Error: {MAPPING_CSV} not found. Run build_mapping.py first.")
        sys.exit(1)

    candidates = []
    with open(MAPPING_CSV, newline="") as f:
        for row in csv.DictReader(f):
            if row["needs_review"] == "True":
                candidates.append(row)
    return candidates


def _load_existing_overrides() -> dict[str, dict]:
    """Load already-reviewed overrides."""
    overrides = {}
    if os.path.exists(OVERRIDES_CSV):
        with open(OVERRIDES_CSV, newline="") as f:
            for row in csv.DictReader(f):
                overrides[row["sw2_path"]] = row
    return overrides


def _save_override(sw2_path: str, sw3_url: str, sw3_title: str) -> None:
    """Append a single override to the overrides file."""
    os.makedirs(DATA_DIR, exist_ok=True)
    file_exists = os.path.exists(OVERRIDES_CSV)
    with open(OVERRIDES_CSV, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["sw2_path", "sw3_url", "sw3_title"])
        if not file_exists:
            writer.writeheader()
        writer.writerow({
            "sw2_path": sw2_path,
            "sw3_url": sw3_url,
            "sw3_title": sw3_title,
        })


def _search_datasets(query: str, datasets: list[dict]) -> list[dict]:
    """Search SW3 datasets by title substring."""
    query_lower = query.lower()
    results = []
    for d in datasets:
        if query_lower in d["title"].lower():
            results.append(d)
    return results[:10]


def main():
    candidates = _load_review_candidates()
    existing = _load_existing_overrides()

    # Filter out already-reviewed
    to_review = [c for c in candidates if c["sw2_path"] not in existing]

    if not to_review:
        print("No matches need review. All done!")
        return

    datasets = load_or_fetch_datasets()
    print(f"\n{len(to_review)} matches need review.\n")
    print("Commands: [a]ccept  [r]eject (use category fallback)  [s]earch  [q]uit\n")

    reviewed = 0
    for i, row in enumerate(to_review, 1):
        print(f"--- [{i}/{len(to_review)}] ---")
        print(f"  SW2 path:  {row['sw2_path']}")
        print(f"  Proposed:  {row['sw3_title']}")
        print(f"  URL:       {row['sw3_url']}")
        print(f"  Confidence: {row['confidence']}")
        print(f"  Match type: {row['match_type']}")

        while True:
            choice = input("\n  [a]ccept / [r]eject / [s]earch / [q]uit > ").strip().lower()

            if choice == "a":
                _save_override(row["sw2_path"], row["sw3_url"], row["sw3_title"])
                print("  ✓ Accepted")
                reviewed += 1
                break

            elif choice == "r":
                # Reject means no override — build_mapping will use category fallback
                # We save a "rejected" entry so we don't ask again
                _save_override(row["sw2_path"], "", "REJECTED")
                print("  ✗ Rejected (will use category fallback)")
                reviewed += 1
                break

            elif choice == "s":
                query = input("  Search SW3 datasets: ").strip()
                if query:
                    results = _search_datasets(query, datasets)
                    if not results:
                        print("  No matches found.")
                    else:
                        for j, d in enumerate(results, 1):
                            print(f"    [{j}] {d['title']}")
                            print(f"        {sw3_dataset_url(d['id'])}")
                        pick = input("  Select number (or Enter to skip): ").strip()
                        if pick.isdigit() and 1 <= int(pick) <= len(results):
                            selected = results[int(pick) - 1]
                            _save_override(
                                row["sw2_path"],
                                sw3_dataset_url(selected["id"]),
                                selected["title"],
                            )
                            print(f"  ✓ Mapped to: {selected['title']}")
                            reviewed += 1
                            break

            elif choice == "q":
                print(f"\nReviewed {reviewed} matches. Exiting.")
                return

            else:
                print("  Invalid choice.")

    print(f"\nReview complete. {reviewed} matches reviewed.")
    print(f"Re-run build_mapping.py to apply overrides.")


if __name__ == "__main__":
    main()
