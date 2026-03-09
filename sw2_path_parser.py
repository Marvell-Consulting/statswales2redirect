"""
Parse and classify StatsWales 2 paths from paths.csv.

Uses a prefix tree built from all Catalogue paths to distinguish
datasets (leaf nodes) from category/navigation pages (non-leaf nodes).
"""

import csv
import re
from dataclasses import dataclass
from urllib.parse import parse_qs, urlparse

from config import PATHS_CSV


@dataclass
class ParsedPath:
    """A classified SW2 path."""
    path: str
    path_type: str  # dataset, category, download_file, download_id, export, shortlink, other
    category: str | None = None  # SW2 category name (e.g., "Agriculture")
    slug: str | None = None  # dataset slug for dataset paths
    code_prefix: str | None = None  # e.g., "AGRI" for download_file paths
    file_name: str | None = None  # full fileName for download_file paths


def _build_prefix_tree(catalogue_paths: list[str]) -> set[str]:
    """
    Build a set of paths that have children (i.e., are non-leaf nodes).
    A path is a leaf (dataset) if no other catalogue path starts with it + "/".
    """
    parents = set()
    sorted_paths = sorted(catalogue_paths)
    for i, path in enumerate(sorted_paths):
        # Check if any subsequent path starts with this path + "/"
        prefix = path + "/"
        for j in range(i + 1, len(sorted_paths)):
            if sorted_paths[j].startswith(prefix):
                parents.add(path)
                break
            if sorted_paths[j] > prefix + "\uffff":
                break
    return parents


def _extract_category(path: str) -> str | None:
    """Extract the SW2 category from a Catalogue path."""
    parts = path.split("/")
    # /Catalogue/CategoryName/...
    if len(parts) >= 3 and parts[1] == "Catalogue":
        return parts[2] if parts[2] else None
    return None


def _extract_slug(path: str) -> str | None:
    """Extract the dataset slug (last path segment) from a Catalogue path."""
    parts = path.rstrip("/").split("/")
    return parts[-1] if len(parts) > 1 else None


def _parse_download(path: str) -> tuple[str, str | None, str | None]:
    """
    Parse a Download path.
    Returns (path_type, code_prefix, file_name).
    """
    parsed = urlparse(path)
    params = parse_qs(parsed.query)

    if "fileName" in params:
        file_name = params["fileName"][0]
        # Extract code prefix: letters before the first digit
        match = re.match(r"^([A-Z]+)", file_name)
        code_prefix = match.group(1) if match else None
        return "download_file", code_prefix, file_name

    if "fileId" in params:
        return "download_id", None, None

    return "download_file", None, None


def parse_paths(csv_path: str = PATHS_CSV) -> list[ParsedPath]:
    """
    Read paths.csv and classify each path.
    Returns a list of ParsedPath objects.
    """
    rows = []
    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row["path"])

    # Separate catalogue paths for prefix tree analysis
    catalogue_paths = [
        p for p in rows
        if p.startswith("/Catalogue") and "?" not in p and p != "/Catalogue"
    ]

    # Build prefix tree to identify parents vs leaves
    parent_paths = _build_prefix_tree(catalogue_paths)

    results = []
    for path in rows:
        parsed = _classify_path(path, parent_paths)
        results.append(parsed)

    return results


def _classify_path(path: str, parent_paths: set[str]) -> ParsedPath:
    """Classify a single SW2 path."""
    # Homepage
    if path == "/":
        return ParsedPath(path=path, path_type="other")

    # Export
    if path.startswith("/Export/"):
        return ParsedPath(path=path, path_type="export")

    # ShortLink
    if path.startswith("/ShortLink/"):
        return ParsedPath(path=path, path_type="shortlink")

    # Download
    if path.startswith("/Download/"):
        path_type, code_prefix, file_name = _parse_download(path)
        return ParsedPath(
            path=path,
            path_type=path_type,
            code_prefix=code_prefix,
            file_name=file_name,
        )

    # Catalogue paths (with query params — treat as category navigation)
    if path.startswith("/Catalogue?"):
        return ParsedPath(path=path, path_type="category")

    # Catalogue — the index page itself
    if path == "/Catalogue":
        return ParsedPath(path=path, path_type="category")

    # Catalogue paths
    if path.startswith("/Catalogue/"):
        category = _extract_category(path)

        if path in parent_paths:
            # Non-leaf: this is a category/navigation page
            return ParsedPath(
                path=path, path_type="category", category=category
            )
        else:
            # Leaf: this is a dataset page
            slug = _extract_slug(path)
            return ParsedPath(
                path=path, path_type="dataset", category=category, slug=slug
            )

    # Everything else: Help, Account, Accessibility, etc.
    return ParsedPath(path=path, path_type="other")


def get_type_counts(parsed: list[ParsedPath]) -> dict[str, int]:
    """Count paths by type."""
    counts: dict[str, int] = {}
    for p in parsed:
        counts[p.path_type] = counts.get(p.path_type, 0) + 1
    return counts


if __name__ == "__main__":
    parsed = parse_paths()
    counts = get_type_counts(parsed)
    total = sum(counts.values())

    print(f"Parsed {total} paths:")
    for path_type, count in sorted(counts.items(), key=lambda x: -x[1]):
        print(f"  {path_type:20s} {count:6d}")

    # Show a few examples of each type
    for path_type in sorted(counts.keys()):
        examples = [p for p in parsed if p.path_type == path_type][:3]
        print(f"\n{path_type} examples:")
        for ex in examples:
            print(f"  {ex.path}")
            if ex.slug:
                print(f"    slug: {ex.slug}")
            if ex.category:
                print(f"    category: {ex.category}")
            if ex.code_prefix:
                print(f"    code_prefix: {ex.code_prefix}")
