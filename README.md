# StatsWales 2 → StatsWales 3 Redirect Service

## Overview

StatsWales 2 is being replaced by StatsWales 3. Rather than letting the old URLs break, this service automatically redirects every request to the most appropriate page on the new site.

StatsWales 2 operates across **two domains** — one English, one Welsh:

| Language | Old domain (SW2)        | New domain (SW3)   |
| -------- | ----------------------- | ------------------ |
| English  | `statswales.gov.wales`  | `stats.gov.wales`  |
| Welsh    | `statscymru.llyw.cymru` | `stats.llyw.cymru` |

Both old domains use **identical URL paths** — the only difference is the domain name. This means a single redirect mapping covers both languages. The service detects which domain the request arrived on and redirects to the correct new domain and locale.

There are **12,798 known URL paths** on StatsWales 2. This service ensures every single one returns a **301 permanent redirect** — no broken links, no 404 errors — in both English and Welsh.

## What happens when someone visits an old URL?

**English example** — visiting `statswales.gov.wales`:

| Old URL pattern                       | Where they go                | Example                                                                       |
| ------------------------------------- | ---------------------------- | ----------------------------------------------------------------------------- |
| A dataset page that exists on SW3     | Directly to that dataset     | `.../crops-in-hectares-by-year` → `stats.gov.wales/en-GB/{dataset-id}`        |
| A dataset page with no SW3 equivalent | The relevant topic page      | `.../old-dataset` → `stats.gov.wales/en-GB/topic/56/housing`                  |
| A category/navigation page            | The corresponding topic page | `/Catalogue/Transport` → `stats.gov.wales/en-GB/topic/92/transport`           |
| A data download link                  | The relevant topic page      | `/Download/File?fileName=AGRI0300.xml` → `stats.gov.wales/en-GB/topic/23/...` |
| Export links, short links, help pages | The SW3 homepage             | `/Export/ShowExportOptions/1234` → `stats.gov.wales/en-GB`                    |
| The homepage                          | The SW3 homepage             | `/` → `stats.gov.wales/en-GB`                                                 |

**Welsh example** — visiting `statscymru.llyw.cymru`:

The same paths produce the same redirects, but to the Welsh domain and locale:

| Old URL pattern                   | Where they go                | Example                                                                 |
| --------------------------------- | ---------------------------- | ----------------------------------------------------------------------- |
| A dataset page that exists on SW3 | Directly to that dataset     | `.../crops-in-hectares-by-year` → `stats.llyw.cymru/cy-GB/{dataset-id}` |
| A category/navigation page        | The corresponding topic page | `/Catalogue/Transport` → `stats.llyw.cymru/cy-GB/topic/92/transport`    |
| Everything else                   | The SW3 Welsh homepage       | `/` → `stats.llyw.cymru/cy-GB`                                          |

All redirects are **permanent (HTTP 301)**, which means:

- Search engines will update their indexes to point to the new URLs
- Browsers cache the redirect so repeat visitors go straight to SW3
- Any bookmarks or links shared in documents will still work

## How the mapping is built

StatsWales 2 and StatsWales 3 have completely different structures — different categories, different URL formats, and different dataset identifiers. There is no shared reference between the two systems, so the mapping is built using a combination of approaches:

1. **Category mapping** — The 19 SW2 categories are manually mapped to the 11 SW3 topics by the service owner (e.g., "Agriculture" → "Environment, energy and agriculture")

2. **Dataset matching** — SW2 dataset names are fuzzy-matched against SW3 dataset titles using text similarity. Of the ~2,872 dataset pages on SW2:
   - **138** match a specific SW3 dataset (6 exact matches, 113 high-confidence, 19 flagged for human review)
   - The remainder redirect to the appropriate topic page

3. **Download codes** — File download URLs contain a code prefix (e.g., `AGRI`, `HLTH`, `EDUC`) that maps to a category, which maps to a topic page

4. **Everything else** — Export links, short links, and account pages redirect to the SW3 homepage

## Coverage summary

| Redirect target              | Paths      | Percentage |
| ---------------------------- | ---------- | ---------- |
| Specific dataset page on SW3 | 138        | 1.1%       |
| Relevant topic page on SW3   | 6,497      | 50.8%      |
| SW3 homepage                 | 6,163      | 48.2%      |
| **Total**                    | **12,798** | **100%**   |

Every path produces a valid redirect. There are no 404s. These numbers apply equally to both the English and Welsh domains.

## Architecture

A single container handles both domains. Azure Front Door inspects the incoming `Host` header and forwards the request to the same container. The service reads the header to determine whether to redirect to `stats.gov.wales/en-GB` or `stats.llyw.cymru/cy-GB`.

```
statswales.gov.wales  ──┐
                        ├───▶ ┌─────────────────────┐
statscymru.llyw.cymru ──┘     │   Azure Front Door  │ ← TLS termination
                              │                     │   Managed certs for
                              └────────┬────────────┘   both domains
                                       │
                                       ▼
                              ┌───────────────────────┐
                              │  Container Apps       │ ← Single redirect
                              │  statswales-redirect  │   service detects
                              └────────┬──────────────┘   language from
                                       │                  Host header
                                 ┌─────┴──────┐
                                 │            │
                                 ▼            ▼
                          English request  Welsh request
                                 │            │
                                 ▼            ▼
                       stats.gov.wales   stats.llyw.cymru
                           /en-GB/...        /cy-GB/...
```

### Key properties

- **Bilingual** — a single service handles both English and Welsh domains using the same mapping table. No duplication.
- **Stateless** — the full redirect mapping is baked into the container image at build time. No database, no external API calls at runtime.
- **Fast** — each request is a dictionary lookup in memory. Sub-millisecond response times.
- **Low resource** — 0.25 vCPU, 0.5 GB RAM. The mapping table is ~1.6 MB.
- **Reliable** — if the mapping file were somehow missing, the service falls back to pattern-based rules (category → topic page, or homepage).

### TLS and DNS

Azure Front Door provides **managed TLS certificates** for both domains, automatically provisioned and renewed — the same approach used for `stats.gov.wales`. Both domains are added as custom domains in a single Front Door profile.

The DNS cutover for each domain involves:

1. Adding the domain as a custom domain in the Front Door profile
2. Adding a DNS validation record to prove ownership
3. Front Door provisions a managed TLS certificate
4. Updating the CNAME to point to Front Door
5. Front Door routes traffic to the redirect container

Both domains can be migrated simultaneously or one at a time.

### Updating the mapping

The mapping is static — it's generated once from the crawled SW2 data and the SW3 API, then baked into the container image. If the mapping needs updating (e.g., after reviewing uncertain matches or if SW3 datasets change):

1. Run `python build_mapping.py` to regenerate `data/mapping.csv`
2. Rebuild and redeploy the container image

This is expected to be infrequent. Once the redirects are in place and search engines have re-indexed, the service requires no ongoing maintenance. Traffic will naturally decrease over time as browsers and search engines cache the permanent redirects.
