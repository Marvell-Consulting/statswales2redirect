"""
Coverage and quality reporting for the SW2 → SW3 mapping.

Reports:
- Match type distribution
- Confidence score distribution
- Review counts
- Coverage statistics
"""

import csv
import os
import sys

from config import MAPPING_CSV


def load_mapping() -> list[dict]:
    if not os.path.exists(MAPPING_CSV):
        print(f"Error: {MAPPING_CSV} not found. Run build_mapping.py first.")
        sys.exit(1)
    with open(MAPPING_CSV, newline="") as f:
        return list(csv.DictReader(f))


def report():
    rows = load_mapping()
    total = len(rows)

    print(f"StatsWales 2 → 3 Redirect Mapping Report")
    print(f"{'=' * 50}")
    print(f"Total paths: {total}")
    print()

    # Match type distribution
    by_type: dict[str, int] = {}
    for row in rows:
        mt = row["match_type"]
        by_type[mt] = by_type.get(mt, 0) + 1

    print("Match type distribution:")
    for mt, count in sorted(by_type.items(), key=lambda x: -x[1]):
        pct = count / total * 100
        print(f"  {mt:25s} {count:6d}  ({pct:5.1f}%)")
    print()

    # Confidence distribution for dataset matches
    dataset_rows = [
        r for r in rows
        if r["match_type"] in ("exact", "sequence", "token")
    ]
    if dataset_rows:
        print(f"Dataset matches: {len(dataset_rows)}")
        conf_buckets = {"1.0 (exact)": 0, "0.85-0.99": 0, "0.60-0.84": 0}
        for r in dataset_rows:
            conf = float(r["confidence"])
            if conf >= 1.0:
                conf_buckets["1.0 (exact)"] += 1
            elif conf >= 0.85:
                conf_buckets["0.85-0.99"] += 1
            else:
                conf_buckets["0.60-0.84"] += 1

        for bucket, count in conf_buckets.items():
            pct = count / len(dataset_rows) * 100
            print(f"  {bucket:20s} {count:6d}  ({pct:5.1f}%)")
        print()

    # Review counts
    needs_review = sum(1 for r in rows if r["needs_review"] == "True")
    print(f"Needs manual review: {needs_review}")
    print()

    # Redirect targets
    targets = set(r["sw3_url"] for r in rows if r["sw3_url"])
    homepage_count = sum(1 for r in rows if r["sw3_url"].endswith("/en-GB"))
    topic_count = sum(1 for r in rows if "/topic/" in r["sw3_url"])
    dataset_count = total - homepage_count - topic_count

    print("Redirect targets:")
    print(f"  Specific dataset pages: {dataset_count:6d}  ({dataset_count/total*100:.1f}%)")
    print(f"  Topic pages:            {topic_count:6d}  ({topic_count/total*100:.1f}%)")
    print(f"  Homepage:               {homepage_count:6d}  ({homepage_count/total*100:.1f}%)")
    print(f"  Unique target URLs:     {len(targets):6d}")


if __name__ == "__main__":
    report()
