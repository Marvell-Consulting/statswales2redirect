#!/usr/bin/env python3
"""
Crawler for statswales.gov.wales
Walks every page under the subdomain and outputs a CSV of paths.
"""

import csv
import sys
import time
from collections import deque
from urllib.parse import urljoin, urlparse, urlunparse

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://statswales.gov.wales"
DOMAIN = "statswales.gov.wales"
DISALLOWED = ["/admin/", "/content/"]  # from robots.txt

# Be polite
REQUEST_DELAY = 0.5  # seconds between requests
TIMEOUT = 30
HEADERS = {
    "User-Agent": "StatsWalesCrawler/1.0 (research purposes)",
    "Accept": "text/html",
}

OUTPUT_FILE = "paths.csv"


def normalise_url(url: str) -> str:
    """Strip fragments and trailing slashes for dedup."""
    parsed = urlparse(url)
    path = parsed.path.rstrip("/") or "/"
    return urlunparse((parsed.scheme, parsed.netloc, path, parsed.params, parsed.query, ""))


def is_allowed(path: str) -> bool:
    for prefix in DISALLOWED:
        if path.startswith(prefix):
            return False
    return True


def is_crawlable(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.netloc and parsed.netloc != DOMAIN:
        return False
    if parsed.scheme and parsed.scheme not in ("http", "https", ""):
        return False
    # Skip non-HTML resources
    skip_extensions = (
        ".pdf", ".xlsx", ".xls", ".csv", ".zip", ".png", ".jpg",
        ".jpeg", ".gif", ".svg", ".ico", ".js", ".css", ".doc",
        ".docx", ".ppt", ".pptx", ".ods", ".odt",
    )
    if any(parsed.path.lower().endswith(ext) for ext in skip_extensions):
        return False
    return is_allowed(parsed.path)


def extract_links(html: str, page_url: str) -> list[str]:
    soup = BeautifulSoup(html, "lxml")
    links = []
    for tag in soup.find_all("a", href=True):
        href = tag["href"].strip()
        if not href or href.startswith(("#", "mailto:", "javascript:", "tel:")):
            continue
        absolute = urljoin(page_url, href)
        if is_crawlable(absolute):
            links.append(normalise_url(absolute))
    return links


def crawl():
    visited: set[str] = set()
    queue: deque[str] = deque()

    start = normalise_url(BASE_URL)
    queue.append(start)
    visited.add(start)

    results: list[dict] = []
    error_count = 0
    max_errors_in_a_row = 20

    print(f"Starting crawl of {BASE_URL}")
    print(f"Output will be written to {OUTPUT_FILE}")
    print()

    while queue:
        url = queue.popleft()
        path = urlparse(url).path or "/"
        query = urlparse(url).query
        full_path = f"{path}?{query}" if query else path

        try:
            resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT, allow_redirects=True)
            status = resp.status_code
            content_type = resp.headers.get("Content-Type", "")

            results.append({
                "path": full_path,
                "status": status,
                "url": url,
            })

            count = len(results)
            queued = len(queue)
            sys.stdout.write(f"\r[{count} crawled | {queued} queued] {full_path[:80]:<80}")
            sys.stdout.flush()

            error_count = 0

            # Only parse HTML responses for further links
            if status == 200 and "text/html" in content_type:
                for link in extract_links(resp.text, url):
                    if link not in visited:
                        visited.add(link)
                        queue.append(link)

        except requests.RequestException as e:
            error_count += 1
            results.append({
                "path": full_path,
                "status": f"ERROR: {e}",
                "url": url,
            })
            if error_count >= max_errors_in_a_row:
                print(f"\n\nStopping: {max_errors_in_a_row} consecutive errors.")
                break

        time.sleep(REQUEST_DELAY)

    print(f"\n\nCrawl complete. {len(results)} pages found.")

    # Write CSV
    with open(OUTPUT_FILE, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["path", "status", "url"])
        writer.writeheader()
        for row in sorted(results, key=lambda r: r["path"]):
            writer.writerow(row)

    print(f"Results written to {OUTPUT_FILE}")


if __name__ == "__main__":
    crawl()
