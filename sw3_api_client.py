"""
Fetch and cache StatsWales 3 topics and datasets from the API.

Caches responses to data/sw3_topics.json and data/sw3_datasets.json
so subsequent runs don't re-fetch.
"""

import json
import math
import os

import requests

from config import SW3_API_BASE, SW3_TOPICS_CACHE, SW3_DATASETS_CACHE, DATA_DIR

TIMEOUT = 30
PAGE_SIZE = 100


def fetch_topics() -> list[dict]:
    """Fetch all topics and their subtopics from the SW3 API."""
    resp = requests.get(f"{SW3_API_BASE}/topic", timeout=TIMEOUT)
    resp.raise_for_status()
    topics_data = resp.json()

    topics = []
    for topic in topics_data.get("children", []):
        topic_id = topic["id"]
        # Fetch individual topic to get subtopics (children)
        detail_resp = requests.get(
            f"{SW3_API_BASE}/topic/{topic_id}", timeout=TIMEOUT
        )
        detail_resp.raise_for_status()
        detail = detail_resp.json()

        topic_entry = {
            "id": topic_id,
            "name": topic.get("name_en", topic.get("name", "")),
            "name_cy": topic.get("name_cy", ""),
            "subtopics": [
                {
                    "id": child["id"],
                    "path": child.get("path", ""),
                    "name": child.get("name_en", child.get("name", "")),
                    "name_cy": child.get("name_cy", ""),
                }
                for child in detail.get("children", [])
            ],
        }
        topics.append(topic_entry)

    return topics


def fetch_datasets() -> list[dict]:
    """Fetch all datasets from the SW3 API with pagination."""
    # First request to get total count
    resp = requests.get(
        f"{SW3_API_BASE}/",
        params={"page_size": PAGE_SIZE, "page_number": 1},
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    data = resp.json()

    total_count = data["count"]
    total_pages = math.ceil(total_count / PAGE_SIZE)
    datasets = list(data["data"])

    for page in range(2, total_pages + 1):
        resp = requests.get(
            f"{SW3_API_BASE}/",
            params={"page_size": PAGE_SIZE, "page_number": page},
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        page_data = resp.json()
        datasets.extend(page_data["data"])

    return datasets


def load_or_fetch_topics(force_refresh: bool = False) -> list[dict]:
    """Load topics from cache or fetch from API."""
    if not force_refresh and os.path.exists(SW3_TOPICS_CACHE):
        with open(SW3_TOPICS_CACHE) as f:
            return json.load(f)

    os.makedirs(DATA_DIR, exist_ok=True)
    topics = fetch_topics()
    with open(SW3_TOPICS_CACHE, "w") as f:
        json.dump(topics, f, indent=2)
    print(f"Cached {len(topics)} topics to {SW3_TOPICS_CACHE}")
    return topics


def load_or_fetch_datasets(force_refresh: bool = False) -> list[dict]:
    """Load datasets from cache or fetch from API."""
    if not force_refresh and os.path.exists(SW3_DATASETS_CACHE):
        with open(SW3_DATASETS_CACHE) as f:
            return json.load(f)

    os.makedirs(DATA_DIR, exist_ok=True)
    datasets = fetch_datasets()
    with open(SW3_DATASETS_CACHE, "w") as f:
        json.dump(datasets, f, indent=2)
    print(f"Cached {len(datasets)} datasets to {SW3_DATASETS_CACHE}")
    return datasets


if __name__ == "__main__":
    print("Fetching SW3 topics...")
    topics = load_or_fetch_topics(force_refresh=True)
    print(f"  {len(topics)} topics loaded")
    for t in topics:
        print(f"    [{t['id']}] {t['name']} ({len(t['subtopics'])} subtopics)")

    print("\nFetching SW3 datasets...")
    datasets = load_or_fetch_datasets(force_refresh=True)
    print(f"  {len(datasets)} datasets loaded")
