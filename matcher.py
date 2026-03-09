"""
Fuzzy matching engine for mapping SW2 dataset slugs to SW3 dataset titles.

Matching strategies (tried in order):
1. Exact match (confidence 1.0)
2. SequenceMatcher ratio >= 0.85 (confidence = ratio)
3. Token overlap / Jaccard similarity (confidence 0.6-0.84)
"""

import re
from dataclasses import dataclass
from difflib import SequenceMatcher

from config import (
    CATEGORY_TO_TOPIC,
    EXACT_MATCH_CONFIDENCE,
    SEQUENCE_MATCHER_THRESHOLD,
    TOKEN_OVERLAP_MIN,
)


@dataclass
class MatchResult:
    """Result of matching an SW2 slug to an SW3 dataset."""
    sw3_id: str | None  # UUID
    sw3_title: str | None
    confidence: float
    match_type: str  # exact, sequence, token, category_fallback, none


# Common stopwords to de-weight in token matching
_STOPWORDS = frozenset({
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from",
    "has", "he", "in", "is", "it", "its", "of", "on", "or", "she",
    "that", "the", "to", "was", "were", "will", "with",
})


def slug_to_title(slug: str) -> str:
    """
    Convert an SW2 URL slug to a normalised title string.

    Handles both hyphenated slugs and CamelCase:
      "crops-in-hectares-by-year" → "crops in hectares by year"
      "BusinessBirths-by-Area-Year" → "business births by area year"
    """
    # Split CamelCase: insert space before uppercase letters
    text = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", slug)
    # Replace hyphens and underscores with spaces
    text = re.sub(r"[-_]+", " ", text)
    # Collapse whitespace and lowercase
    text = re.sub(r"\s+", " ", text).strip().lower()
    return text


def normalize_title(title: str) -> str:
    """
    Normalise an SW3 dataset title for comparison.

    Lowercases, strips punctuation, collapses whitespace.
    """
    text = title.lower()
    # Remove punctuation except hyphens within words
    text = re.sub(r"[^\w\s-]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _tokenize(text: str) -> set[str]:
    """Split normalised text into a set of non-stopword tokens."""
    words = set(text.split())
    return words - _STOPWORDS


def _token_overlap(tokens_a: set[str], tokens_b: set[str]) -> float:
    """Jaccard similarity between two token sets."""
    if not tokens_a or not tokens_b:
        return 0.0
    intersection = tokens_a & tokens_b
    union = tokens_a | tokens_b
    return len(intersection) / len(union)


def match_slug(
    slug: str,
    sw3_datasets: list[dict],
    category: str | None = None,
) -> MatchResult:
    """
    Find the best SW3 dataset match for an SW2 slug.

    Tries matching within the category-scoped topic first, then broadens
    to all datasets if no good match is found.
    """
    normalised_slug = slug_to_title(slug)
    slug_tokens = _tokenize(normalised_slug)

    # Build lookup of normalised titles → dataset info
    all_candidates = [
        {
            "id": d["id"],
            "title": d["title"],
            "normalised": normalize_title(d["title"]),
            "tokens": _tokenize(normalize_title(d["title"])),
        }
        for d in sw3_datasets
    ]

    # Try category-scoped matching first, then all datasets
    candidate_sets = [all_candidates]
    if category and category in CATEGORY_TO_TOPIC and CATEGORY_TO_TOPIC[category]:
        # For now we match against all — category scoping could be refined
        # if we had per-dataset topic assignments from SW3.
        # The scoping is implicit: we try the full set but could filter
        # if the API provided topic-to-dataset relationships.
        pass

    best = MatchResult(sw3_id=None, sw3_title=None, confidence=0.0, match_type="none")

    for candidates in candidate_sets:
        result = _find_best_match(normalised_slug, slug_tokens, candidates)
        if result.confidence > best.confidence:
            best = result
        if best.confidence >= SEQUENCE_MATCHER_THRESHOLD:
            break

    return best


def _find_best_match(
    normalised_slug: str,
    slug_tokens: set[str],
    candidates: list[dict],
) -> MatchResult:
    """Find best match from a list of candidates."""
    best = MatchResult(sw3_id=None, sw3_title=None, confidence=0.0, match_type="none")

    for c in candidates:
        # Strategy 1: Exact match
        if normalised_slug == c["normalised"]:
            return MatchResult(
                sw3_id=c["id"],
                sw3_title=c["title"],
                confidence=EXACT_MATCH_CONFIDENCE,
                match_type="exact",
            )

        # Strategy 2: SequenceMatcher
        ratio = SequenceMatcher(None, normalised_slug, c["normalised"]).ratio()
        if ratio >= SEQUENCE_MATCHER_THRESHOLD and ratio > best.confidence:
            best = MatchResult(
                sw3_id=c["id"],
                sw3_title=c["title"],
                confidence=ratio,
                match_type="sequence",
            )
            continue

        # Strategy 3: Token overlap (only if we haven't found a sequence match)
        if best.confidence < SEQUENCE_MATCHER_THRESHOLD:
            overlap = _token_overlap(slug_tokens, c["tokens"])
            if overlap >= TOKEN_OVERLAP_MIN and overlap > best.confidence:
                best = MatchResult(
                    sw3_id=c["id"],
                    sw3_title=c["title"],
                    confidence=overlap,
                    match_type="token",
                )

    return best
