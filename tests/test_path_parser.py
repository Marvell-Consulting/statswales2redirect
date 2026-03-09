"""Tests for SW2 path classification."""

import pytest

from sw2_path_parser import ParsedPath, _build_prefix_tree, _classify_path, _extract_category


class TestExtractCategory:
    def test_simple_category(self):
        assert _extract_category("/Catalogue/Agriculture/sub") == "Agriculture"

    def test_deep_path(self):
        assert _extract_category("/Catalogue/Health-and-Social-Care/Sub/Deep/Path") == "Health-and-Social-Care"

    def test_no_category(self):
        assert _extract_category("/Catalogue") is None

    def test_empty_category(self):
        assert _extract_category("/Catalogue/") is None


class TestBuildPrefixTree:
    def test_identifies_parents(self):
        paths = [
            "/Catalogue/Agriculture",
            "/Catalogue/Agriculture/Sub",
            "/Catalogue/Agriculture/Sub/dataset-slug",
        ]
        parents = _build_prefix_tree(paths)
        assert "/Catalogue/Agriculture" in parents
        assert "/Catalogue/Agriculture/Sub" in parents
        assert "/Catalogue/Agriculture/Sub/dataset-slug" not in parents

    def test_leaf_only(self):
        paths = ["/Catalogue/Agriculture/dataset-one"]
        parents = _build_prefix_tree(paths)
        assert len(parents) == 0


class TestClassifyPath:
    """Test path classification logic."""

    @pytest.fixture
    def parent_paths(self):
        return {
            "/Catalogue/Agriculture",
            "/Catalogue/Agriculture/Agricultural-Survey",
            "/Catalogue/Agriculture/Agricultural-Survey/Annual-Survey-Results",
        }

    def test_homepage(self, parent_paths):
        result = _classify_path("/", parent_paths)
        assert result.path_type == "other"

    def test_export(self, parent_paths):
        result = _classify_path("/Export/ShowExportOptions/1234", parent_paths)
        assert result.path_type == "export"

    def test_shortlink(self, parent_paths):
        result = _classify_path("/ShortLink/1234/SaveShortLink", parent_paths)
        assert result.path_type == "shortlink"

    def test_download_filename(self, parent_paths):
        result = _classify_path("/Download/File?fileName=AGRI0300.xml", parent_paths)
        assert result.path_type == "download_file"
        assert result.code_prefix == "AGRI"
        assert result.file_name == "AGRI0300.xml"

    def test_download_fileid(self, parent_paths):
        result = _classify_path("/Download/File?fileId=387", parent_paths)
        assert result.path_type == "download_id"

    def test_catalogue_parent_is_category(self, parent_paths):
        result = _classify_path("/Catalogue/Agriculture", parent_paths)
        assert result.path_type == "category"
        assert result.category == "Agriculture"

    def test_catalogue_leaf_is_dataset(self, parent_paths):
        result = _classify_path(
            "/Catalogue/Agriculture/Agricultural-Survey/Annual-Survey-Results/crops-in-hectares-by-year",
            parent_paths,
        )
        assert result.path_type == "dataset"
        assert result.category == "Agriculture"
        assert result.slug == "crops-in-hectares-by-year"

    def test_catalogue_query_is_category(self, parent_paths):
        result = _classify_path("/Catalogue?path=Education-and-Skills", parent_paths)
        assert result.path_type == "category"

    def test_catalogue_index(self, parent_paths):
        result = _classify_path("/Catalogue", parent_paths)
        assert result.path_type == "category"

    def test_help_is_other(self, parent_paths):
        result = _classify_path("/Help/Index", parent_paths)
        assert result.path_type == "other"

    def test_account_is_other(self, parent_paths):
        result = _classify_path("/Account/Logon", parent_paths)
        assert result.path_type == "other"

    def test_accessibility_is_other(self, parent_paths):
        result = _classify_path("/Accessibility/Index", parent_paths)
        assert result.path_type == "other"

    def test_download_dimensionitems(self, parent_paths):
        result = _classify_path(
            "/Download/File?fileName=HLTH0501_dimensionitems.csv", parent_paths
        )
        assert result.path_type == "download_file"
        assert result.code_prefix == "HLTH"
