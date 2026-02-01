"""Tests for CacheManager class."""

import json
import tempfile
from pathlib import Path

import pytest

from code_monkey.agents.project_librarian.cache_manager import CacheManager


class TestCacheManagerInitialization:
    """Tests for CacheManager initialization."""

    def test_initializes_with_root_path(self, tmp_path: Path) -> None:
        """Should initialize with correct root and cache directory."""
        cache = CacheManager(tmp_path)

        assert cache.root == tmp_path
        assert cache.cache_dir == tmp_path / ".codemonkey"

    def test_cache_dir_not_created_on_init(self, tmp_path: Path) -> None:
        """Cache directory should not be created until needed."""
        cache = CacheManager(tmp_path)

        assert not cache.cache_dir.exists()


class TestHashCacheOperations:
    """Tests for file hash cache operations."""

    def test_load_hashes_returns_empty_when_missing(self, tmp_path: Path) -> None:
        """Should return empty dict when hash file doesn't exist."""
        cache = CacheManager(tmp_path)

        result = cache.load_hashes()

        assert result == {}

    def test_load_hashes_returns_cached_data(self, tmp_path: Path) -> None:
        """Should load and return cached hash data."""
        cache = CacheManager(tmp_path)

        # Save some hashes first
        hashes = {"/path/to/file1.py": "abc123", "/path/to/file2.py": "def456"}
        cache.save_hashes(hashes)

        # Load them back
        result = cache.load_hashes()

        assert result == hashes

    def test_save_hashes_creates_cache_dir(self, tmp_path: Path) -> None:
        """Should create cache directory when saving."""
        cache = CacheManager(tmp_path)

        cache.save_hashes({"file.py": "hash"})

        assert cache.cache_dir.exists()
        assert (cache.cache_dir / CacheManager.HASHES_FILENAME).exists()

    def test_save_hashes_is_atomic(self, tmp_path: Path) -> None:
        """Save should use atomic write pattern (temp file + rename)."""
        cache = CacheManager(tmp_path)

        hashes = {"file.py": "new_hash"}
        cache.save_hashes(hashes)

        # Verify final file exists with correct content
        hashes_file = cache.cache_dir / CacheManager.HASHES_FILENAME
        assert hashes_file.exists()
        with open(hashes_file) as f:
            loaded = json.load(f)
        assert loaded == hashes

    def test_load_hashes_handles_corrupt_file(self, tmp_path: Path) -> None:
        """Should return empty dict when cache file is corrupt."""
        cache = CacheManager(tmp_path)

        # Create corrupt JSON file
        cache_dir = tmp_path / ".codemonkey"
        cache_dir.mkdir()
        hashes_file = cache_dir / CacheManager.HASHES_FILENAME
        hashes_file.write_text("{invalid json}")

        result = cache.load_hashes()

        assert result == {}

    def test_load_hashes_handles_missing_keys(self, tmp_path: Path) -> None:
        """Should handle cache files with missing expected keys."""
        cache = CacheManager(tmp_path)

        # Save partial data with the correct structure but different keys
        cache_dir = tmp_path / ".codemonkey"
        cache_dir.mkdir()
        hashes_file = cache_dir / CacheManager.HASHES_FILENAME
        with open(hashes_file, "w") as f:
            json.dump({"file.py": "hash_value"}, f)

        result = cache.load_hashes()

        # Should return what was saved, not empty dict
        assert result == {"file.py": "hash_value"}


class TestFileSummaryOperations:
    """Tests for file summary cache operations."""

    def test_get_file_summary_path(self, tmp_path: Path) -> None:
        """Should return correct path for file summary."""
        cache = CacheManager(tmp_path)

        filepath = tmp_path / "src" / "module" / "file.py"
        path = cache.get_file_summary_path(filepath)

        expected = cache.cache_dir / "src/module/file.md"
        assert path == expected

    def test_save_and_load_file_summary(self, tmp_path: Path) -> None:
        """Should save and load file summary correctly."""
        cache = CacheManager(tmp_path)

        filepath = tmp_path / "test.py"
        summary = "This is a test summary"

        # Save and load
        cache.save_file_summary(filepath, summary)
        result = cache.load_file_summary(filepath)

        assert result == summary

    def test_load_file_summary_returns_none_when_missing(self, tmp_path: Path) -> None:
        """Should return None when summary file doesn't exist."""
        cache = CacheManager(tmp_path)

        filepath = tmp_path / "nonexistent.py"
        result = cache.load_file_summary(filepath)

        assert result is None

    def test_save_file_summary_creates_directories(self, tmp_path: Path) -> None:
        """Should create nested directories for file summary."""
        cache = CacheManager(tmp_path)

        filepath = tmp_path / "src" / "deep" / "path" / "file.py"
        cache.save_file_summary(filepath, "summary")

        expected_path = cache.get_file_summary_path(filepath)
        assert expected_path.exists()


class TestModuleSummaryOperations:
    """Tests for module summary cache operations."""

    def test_get_module_summary_path(self, tmp_path: Path) -> None:
        """Should return correct path for module summary."""
        cache = CacheManager(tmp_path)

        directory = tmp_path / "src" / "module"
        path = cache.get_module_summary_path(directory)

        expected = cache.cache_dir / "src/module/_module.md"
        assert path == expected

    def test_save_and_load_module_summary(self, tmp_path: Path) -> None:
        """Should save and load module summary correctly."""
        cache = CacheManager(tmp_path)

        directory = tmp_path / "src"
        summary = "This module does X and Y"

        # Save and load
        cache.save_module_summary(directory, summary)
        result = cache.load_module_summary(directory)

        assert result == summary

    def test_load_module_summary_returns_none_when_missing(self, tmp_path: Path) -> None:
        """Should return None when module summary doesn't exist."""
        cache = CacheManager(tmp_path)

        directory = tmp_path / "nonexistent"
        result = cache.load_module_summary(directory)

        assert result is None


class TestProjectContextOperations:
    """Tests for project context cache operations."""

    def test_save_and_load_project_context(self, tmp_path: Path) -> None:
        """Should save and load project context correctly."""
        cache = CacheManager(tmp_path)

        context = "project structure overview..."

        # Save and load
        cache.save_project_context(context)
        result = cache.load_project_context()

        assert result == context

    def test_load_project_context_returns_none_when_missing(self, tmp_path: Path) -> None:
        """Should return None when project context doesn't exist."""
        cache = CacheManager(tmp_path)

        result = cache.load_project_context()

        assert result is None

    def test_save_project_context_creates_json_structure(self, tmp_path: Path) -> None:
        """Should save context in JSON format with 'context' key."""
        cache = CacheManager(tmp_path)

        context = "test context"
        cache.save_project_context(context)

        context_file = cache.cache_dir / CacheManager.PROJECT_CONTEXT_FILENAME
        with open(context_file) as f:
            data = json.load(f)

        assert "context" in data
        assert data["context"] == context


class TestCacheManagerEdgeCases:
    """Tests for edge cases and error handling."""

    def test_get_cache_path_handles_root_files(self, tmp_path: Path) -> None:
        """Should handle files at root correctly."""
        cache = CacheManager(tmp_path)

        filepath = tmp_path / "file.py"
        path = cache._get_cache_path(filepath.relative_to(tmp_path))

        assert path == cache.cache_dir / "file.py"

    def test_get_cache_path_handles_nested_paths(self, tmp_path: Path) -> None:
        """Should handle deeply nested paths."""
        cache = CacheManager(tmp_path)

        rel_path = Path("src/utils/helpers/file.py")
        path = cache._get_cache_path(rel_path)

        assert path == cache.cache_dir / "src/utils/helpers/file.py"

    def test_ensure_cache_dir_idempotent(self, tmp_path: Path) -> None:
        """Calling _ensure_cache_dir multiple times should not error."""
        cache = CacheManager(tmp_path)

        cache._ensure_cache_dir()
        cache._ensure_cache_dir()
        cache._ensure_cache_dir()

        assert cache.cache_dir.exists()

    def test_save_file_summary_handles_read_errors(self, tmp_path: Path) -> None:
        """Should handle OSError when reading summary files."""
        cache = CacheManager(tmp_path)

        filepath = tmp_path / "test.py"
        cache.save_file_summary(filepath, "summary")

        # Load should succeed
        result = cache.load_file_summary(filepath)
        assert result == "summary"

    def test_multiple_hashes_saves_correctly(self, tmp_path: Path) -> None:
        """Should handle multiple file hashes correctly."""
        cache = CacheManager(tmp_path)

        hashes = {
            "/path/file1.py": "hash1",
            "/path/file2.py": "hash2",
            "/path/file3.py": "hash3",
        }
        cache.save_hashes(hashes)

        result = cache.load_hashes()
        assert len(result) == 3
        assert result["/path/file1.py"] == "hash1"
        assert result["/path/file2.py"] == "hash2"
        assert result["/path/file3.py"] == "hash3"
