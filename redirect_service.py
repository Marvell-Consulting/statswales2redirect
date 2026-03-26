"""
FastAPI redirect service for StatsWales 2 → StatsWales 3.

Handles both domains:
  statswales.gov.wales  → stats.gov.wales/en-GB/...
  statscymru.llyw.cymru → stats.llyw.cymru/cy-GB/...

The same mapping table is used for both — the paths are identical,
only the target base URL differs.

Run with: uvicorn redirect_service:app --host 0.0.0.0 --port 8080
"""

import csv
import os
import re
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse

from config import (
    CODE_PREFIX_TO_CATEGORY,
    CATEGORY_TO_TOPIC,
    DOMAIN_LOCALE,
    MAPPING_CSV,
    SW3_EN_HOME,
    SW3_CY_HOME,
    SW3_HOME,
)

# Mapping loaded at startup: sw2_path → sw3_url (English base URLs)
_mapping: dict[str, str] = {}


def _load_mapping() -> dict[str, str]:
    """Load the mapping CSV into a dict."""
    mapping = {}
    if not os.path.exists(MAPPING_CSV):
        return mapping
    with open(MAPPING_CSV, newline="") as f:
        for row in csv.DictReader(f):
            sw3_url = row["sw3_url"]
            if sw3_url:  # skip rejected overrides
                mapping[row["sw2_path"]] = sw3_url
    return mapping


def _localise_url(url: str, host: str) -> str:
    """
    Rewrite an English SW3 URL to the correct locale based on the
    incoming request's Host header.

    English mapping is the canonical source. For Welsh requests,
    swap the base URL and locale prefix.
    """
    locale = DOMAIN_LOCALE.get(host)
    if locale and locale["locale"] == "cy-GB":
        # Swap stats.gov.wales/en-GB → stats.llyw.cymru/cy-GB
        return url.replace(SW3_EN_HOME, SW3_CY_HOME)
    return url


def _fallback_redirect(path: str, query: str, host: str) -> str:
    """
    Pattern-based fallback for paths not in the mapping.
    Returns the target SW3 URL in the correct locale.
    """
    locale = DOMAIN_LOCALE.get(host, DOMAIN_LOCALE["statswales.gov.wales"])
    home = locale["home"]

    # Catalogue paths: extract category
    if path.startswith("/Catalogue/"):
        parts = path.split("/")
        if len(parts) >= 3:
            category = parts[2]
            topic = CATEGORY_TO_TOPIC.get(category)
            if topic:
                return f"{home}/topic/{topic['id']}/{topic['slug']}"
            return home

    # Download with fileName: extract code prefix
    if path.startswith("/Download/") and "fileName=" in query:
        match = re.search(r"fileName=([A-Z]+)", query)
        if match:
            prefix = match.group(1)
            if prefix in CODE_PREFIX_TO_CATEGORY:
                category = CODE_PREFIX_TO_CATEGORY[prefix]
                topic = CATEGORY_TO_TOPIC.get(category)
                if topic:
                    return f"{home}/topic/{topic['id']}/{topic['slug']}"

    # Everything else → homepage
    return home


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _mapping
    _mapping = _load_mapping()
    print(f"Loaded {len(_mapping)} redirect mappings")
    yield


app = FastAPI(title="StatsWales 2 Redirect Service", lifespan=lifespan)


@app.get("/healthz")
async def health():
    """Health check for Azure Container Apps probes."""
    return {"status": "healthy", "mappings_loaded": len(_mapping)}


@app.get("/")
async def redirect_root(request: Request):
    """Handle root path."""
    host = request.headers.get("x-forwarded-host", request.headers.get("host", "")).split(":")[0]
    target = _mapping.get("/", SW3_HOME)
    target = _localise_url(target, host)
    return RedirectResponse(url=target, status_code=301)


@app.api_route("/{path:path}", methods=["GET", "HEAD"])
async def redirect(request: Request):
    """Handle all incoming requests with a 301 redirect."""
    host = request.headers.get("x-forwarded-host", request.headers.get("host", "")).split(":")[0]
    path = f"/{request.path_params['path']}" if request.path_params.get("path") else "/"
    query = str(request.query_params)
    full_path = f"{path}?{query}" if query else path

    # Try exact lookup first (mapping uses English URLs)
    target = _mapping.get(full_path)
    if not target:
        target = _mapping.get(path)
    if not target:
        # Pattern-based fallback (locale-aware)
        target = _fallback_redirect(path, query, host)
        return RedirectResponse(url=target, status_code=301)

    # Localise the mapped URL for Welsh requests
    target = _localise_url(target, host)
    return RedirectResponse(url=target, status_code=301)
