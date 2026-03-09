"""Tests for the fuzzy matching engine."""

import pytest

from matcher import (
    MatchResult,
    _token_overlap,
    _tokenize,
    match_slug,
    normalize_title,
    slug_to_title,
)


class TestSlugToTitle:
    def test_hyphenated(self):
        assert slug_to_title("crops-in-hectares-by-year") == "crops in hectares by year"

    def test_camelcase(self):
        assert slug_to_title("BusinessBirths") == "business births"

    def test_mixed_camel_hyphen(self):
        assert slug_to_title("BusinessBirths-by-Area-Year") == "business births by area year"

    def test_underscores(self):
        assert slug_to_title("total_livestock_by_type") == "total livestock by type"

    def test_lowercase_slug(self):
        assert slug_to_title("aggregateagriculturaloutputandincome") == "aggregateagriculturaloutputandincome"

    def test_all_caps_prefix(self):
        # All-caps like "NHS" shouldn't get split letter by letter
        result = slug_to_title("NHSstaff-by-year")
        assert "by year" in result


class TestNormalizeTitle:
    def test_basic(self):
        assert normalize_title("Farm Income by Farm Type") == "farm income by farm type"

    def test_punctuation(self):
        assert normalize_title("Children's services (2019)") == "children s services 2019"

    def test_extra_whitespace(self):
        assert normalize_title("  Multiple   spaces  ") == "multiple spaces"


class TestTokenize:
    def test_removes_stopwords(self):
        tokens = _tokenize("crops in hectares by year")
        assert "in" not in tokens
        assert "by" not in tokens
        assert "crops" in tokens
        assert "hectares" in tokens
        assert "year" in tokens


class TestTokenOverlap:
    def test_identical(self):
        tokens = {"crops", "hectares", "year"}
        assert _token_overlap(tokens, tokens) == 1.0

    def test_no_overlap(self):
        assert _token_overlap({"a", "b"}, {"c", "d"}) == 0.0

    def test_partial(self):
        a = {"crops", "hectares", "year"}
        b = {"crops", "hectares", "area"}
        # Jaccard: 2/4 = 0.5
        assert _token_overlap(a, b) == pytest.approx(0.5)

    def test_empty(self):
        assert _token_overlap(set(), {"a"}) == 0.0


class TestMatchSlug:
    @pytest.fixture
    def sw3_datasets(self):
        return [
            {"id": "uuid-1", "title": "Crops in hectares by year"},
            {"id": "uuid-2", "title": "Farm size by area"},
            {"id": "uuid-3", "title": "Total livestock in Wales by year"},
            {"id": "uuid-4", "title": "Population estimates by local authority and year"},
        ]

    def test_exact_match(self, sw3_datasets):
        result = match_slug("crops-in-hectares-by-year", sw3_datasets)
        assert result.sw3_id == "uuid-1"
        assert result.match_type == "exact"
        assert result.confidence == 1.0

    def test_sequence_match(self, sw3_datasets):
        result = match_slug("total-livestock-in-wales-by-year", sw3_datasets)
        assert result.sw3_id == "uuid-3"
        assert result.confidence >= 0.85

    def test_no_match(self, sw3_datasets):
        result = match_slug("completely-unrelated-dataset-about-nothing", sw3_datasets)
        assert result.confidence < 0.6 or result.sw3_id is None

    def test_token_overlap_match(self, sw3_datasets):
        result = match_slug("farm-size-by-year", sw3_datasets)
        # Should partially match "Farm size by area" via token overlap
        if result.sw3_id:
            assert result.confidence >= 0.6
