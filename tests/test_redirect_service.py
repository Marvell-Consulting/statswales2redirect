"""Tests for the FastAPI redirect service."""

import csv
import os
import tempfile

import pytest
from fastapi.testclient import TestClient

# Patch MAPPING_CSV before importing the app
import config

_temp_dir = tempfile.mkdtemp()
_temp_mapping = os.path.join(_temp_dir, "mapping.csv")
config.MAPPING_CSV = _temp_mapping

_TEST_ROWS = [
    {
        "sw2_path": "/",
        "sw3_url": "https://stats.gov.wales/en-GB",
        "match_type": "other",
        "confidence": "0.0",
        "sw3_title": "",
        "needs_review": "False",
    },
    {
        "sw2_path": "/Catalogue/Agriculture/Agricultural-Survey/Annual-Survey-Results/crops-in-hectares-by-year",
        "sw3_url": "https://stats.gov.wales/en-GB/test-uuid-1",
        "match_type": "exact",
        "confidence": "1.0",
        "sw3_title": "Crops in hectares by year",
        "needs_review": "False",
    },
    {
        "sw2_path": "/Catalogue/Agriculture",
        "sw3_url": "https://stats.gov.wales/en-GB/topic/23/environment-energy-agriculture",
        "match_type": "category",
        "confidence": "1.0",
        "sw3_title": "",
        "needs_review": "False",
    },
    {
        "sw2_path": "/Download/File?fileName=AGRI0300.xml",
        "sw3_url": "https://stats.gov.wales/en-GB/topic/23/environment-energy-agriculture",
        "match_type": "download_prefix",
        "confidence": "0.5",
        "sw3_title": "",
        "needs_review": "False",
    },
    {
        "sw2_path": "/Export/ShowExportOptions/1234",
        "sw3_url": "https://stats.gov.wales/en-GB",
        "match_type": "export",
        "confidence": "0.0",
        "sw3_title": "",
        "needs_review": "False",
    },
    {
        "sw2_path": "/ShortLink/5678/SaveShortLink",
        "sw3_url": "https://stats.gov.wales/en-GB",
        "match_type": "shortlink",
        "confidence": "0.0",
        "sw3_title": "",
        "needs_review": "False",
    },
]


def _write_test_mapping():
    """Write a test mapping CSV."""
    fieldnames = ["sw2_path", "sw3_url", "match_type", "confidence", "sw3_title", "needs_review"]
    with open(_temp_mapping, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in _TEST_ROWS:
            writer.writerow(row)


# Write test data before importing the app
_write_test_mapping()

from redirect_service import app  # noqa: E402


@pytest.fixture()
def client():
    """Create a TestClient with lifespan context so mapping is loaded."""
    with TestClient(app, follow_redirects=False) as c:
        yield c


class TestRedirects:
    def test_root_redirects_to_homepage(self, client):
        resp = client.get("/")
        assert resp.status_code == 301
        assert resp.headers["location"] == "https://stats.gov.wales/en-GB"

    def test_dataset_redirects_to_sw3_dataset(self, client):
        resp = client.get(
            "/Catalogue/Agriculture/Agricultural-Survey/Annual-Survey-Results/crops-in-hectares-by-year"
        )
        assert resp.status_code == 301
        assert resp.headers["location"] == "https://stats.gov.wales/en-GB/test-uuid-1"

    def test_category_redirects_to_topic(self, client):
        resp = client.get("/Catalogue/Agriculture")
        assert resp.status_code == 301
        assert "topic/23/environment-energy-agriculture" in resp.headers["location"]

    def test_download_redirects(self, client):
        resp = client.get("/Download/File", params={"fileName": "AGRI0300.xml"})
        assert resp.status_code == 301
        assert "topic/23" in resp.headers["location"]

    def test_export_redirects_to_homepage(self, client):
        resp = client.get("/Export/ShowExportOptions/1234")
        assert resp.status_code == 301
        assert resp.headers["location"] == "https://stats.gov.wales/en-GB"

    def test_shortlink_redirects_to_homepage(self, client):
        resp = client.get("/ShortLink/5678/SaveShortLink")
        assert resp.status_code == 301
        assert resp.headers["location"] == "https://stats.gov.wales/en-GB"

    def test_unknown_path_redirects_to_homepage(self, client):
        resp = client.get("/SomeUnknownPath")
        assert resp.status_code == 301
        assert resp.headers["location"] == "https://stats.gov.wales/en-GB"

    def test_fallback_catalogue_uses_category(self, client):
        """A catalogue path not in mapping should fall back to category-based redirect."""
        resp = client.get("/Catalogue/Transport/SomeSubPage/dataset")
        assert resp.status_code == 301
        assert "topic/92/transport" in resp.headers["location"]

    def test_fallback_download_uses_prefix(self, client):
        """A download path not in mapping should use code prefix fallback."""
        resp = client.get("/Download/File", params={"fileName": "HLTH9999.xml"})
        assert resp.status_code == 301
        assert "topic/40/health-social-care" in resp.headers["location"]

    def test_healthz_returns_200(self, client):
        resp = client.get("/healthz")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "healthy"
        assert body["mappings_loaded"] > 0

    # --- Welsh locale tests ---

    def test_welsh_root_redirects_to_cy_homepage(self, client):
        resp = client.get("/", headers={"host": "statscymru.llyw.cymru"})
        assert resp.status_code == 301
        assert resp.headers["location"] == "https://stats.llyw.cymru/cy-GB"

    def test_welsh_dataset_redirects_to_cy_dataset(self, client):
        resp = client.get(
            "/Catalogue/Agriculture/Agricultural-Survey/Annual-Survey-Results/crops-in-hectares-by-year",
            headers={"host": "statscymru.llyw.cymru"},
        )
        assert resp.status_code == 301
        assert resp.headers["location"] == "https://stats.llyw.cymru/cy-GB/test-uuid-1"

    def test_welsh_category_redirects_to_cy_topic(self, client):
        resp = client.get(
            "/Catalogue/Agriculture",
            headers={"host": "statscymru.llyw.cymru"},
        )
        assert resp.status_code == 301
        assert "stats.llyw.cymru/cy-GB/topic/23" in resp.headers["location"]

    def test_welsh_fallback_uses_cy_homepage(self, client):
        resp = client.get(
            "/Export/ShowExportOptions/1234",
            headers={"host": "statscymru.llyw.cymru"},
        )
        assert resp.status_code == 301
        assert resp.headers["location"] == "https://stats.llyw.cymru/cy-GB"

    def test_welsh_fallback_catalogue_uses_cy_topic(self, client):
        resp = client.get(
            "/Catalogue/Transport/SomeSubPage/dataset",
            headers={"host": "statscymru.llyw.cymru"},
        )
        assert resp.status_code == 301
        assert "stats.llyw.cymru/cy-GB/topic/92/transport" in resp.headers["location"]

    def test_welsh_fallback_download_uses_cy_topic(self, client):
        resp = client.get(
            "/Download/File",
            params={"fileName": "HLTH9999.xml"},
            headers={"host": "statscymru.llyw.cymru"},
        )
        assert resp.status_code == 301
        assert "stats.llyw.cymru/cy-GB/topic/40/health-social-care" in resp.headers["location"]

    # --- General tests ---

    def test_all_redirects_are_301(self, client):
        """Every response should be a 301 permanent redirect."""
        paths = [
            "/",
            "/Help/Index",
            "/Account/Logon",
            "/Catalogue/Housing",
        ]
        for path in paths:
            resp = client.get(path)
            assert resp.status_code == 301, f"Expected 301 for {path}, got {resp.status_code}"
