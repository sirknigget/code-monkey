"""Tests for CacheManager and data structures."""

import json
import tempfile
from pathlib import Path

import pytest

from code_monkey.agents.project_librarian.cache_manager import (
    CacheManager,
    CodeContext,
    ModuleContext,
    FileContext,
)


class TestDataStructures:
    """Tests for CodeContext, ModuleContext, FileContext structures."""

    def test_file_context_creation(self) -> None:
        """Should create FileContext with summary."""
        fc = FileContext(summary="test summary")
        assert fc.summary == "test summary"

    def test_module_context_creation(self) -> None:
        """Should create ModuleContext with files and submodules."""
        files = {"file1.py": FileContext(summary="file 1")}
        submodules = {"submod": ModuleContext(summary="submod", files={}, submodules={})}
        mc = ModuleContext(summary="module", files=files, submodules=submodules)
        assert mc.summary == "module"
        assert len(mc.files) == 1
        assert len(mc.submodules) == 1

    def test_code_context_creation(self) -> None:
        """Should create CodeContext with root_summary and modules."""
        modules = {"pkg": ModuleContext(summary="pkg", files={}, submodules={})}
        cc = CodeContext(root_summary="root", modules=modules)
        assert cc.root_summary == "root"
        assert "pkg" in cc.modules

    def test_nested_hierarchy(self) -> None:
        """Should support deeply nested hierarchies."""
        deep = ModuleContext(
            summary="deep",
            files={},
            submodules={
                "level1": ModuleContext(
                    summary="level1",
                    files={},
                    submodules={
                        "level2": ModuleContext(
                            summary="level2",
                            files={},
                            submodules={},
                        )
                    },
                )
            },
        )
        assert deep.submodules["level1"].submodules["level2"].summary == "level2"


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


class TestCodeContextOperations:
    """Tests for CodeContext save/load operations."""

    def test_save_and_load_code_context(self, tmp_path: Path) -> None:
        """Should save and load code context correctly."""
        cache = CacheManager(tmp_path)

        # Create a context
        files = {"main.py": FileContext(summary="main file")}
        modules = {"pkg": ModuleContext(summary="pkg module", files=files, submodules={})}
        ctx = CodeContext(root_summary="root", modules=modules)

        # Save and load
        cache.save_code_context(ctx)
        result = cache.load_code_context()

        assert result is not None
        assert result.root_summary == "root"
        assert "pkg" in result.modules
        assert result.modules["pkg"].summary == "pkg module"
        assert "main.py" in result.modules["pkg"].files
        assert result.modules["pkg"].files["main.py"].summary == "main file"

    def test_load_code_context_returns_none_when_missing(self, tmp_path: Path) -> None:
        """Should return None when context file doesn't exist."""
        cache = CacheManager(tmp_path)

        result = cache.load_code_context()

        assert result is None

    def test_nested_modules_roundtrip(self, tmp_path: Path) -> None:
        """Should preserve nested module structure."""
        cache = CacheManager(tmp_path)

        # Create nested structure
        inner = ModuleContext(summary="inner", files={}, submodules={})
        outer = ModuleContext(summary="outer", files={}, submodules={"inner": inner})
        ctx = CodeContext(root_summary="root", modules={"outer": outer})

        # Roundtrip
        cache.save_code_context(ctx)
        result = cache.load_code_context()

        assert result is not None
        assert "outer" in result.modules
        assert "inner" in result.modules["outer"].submodules
        assert result.modules["outer"].submodules["inner"].summary == "inner"

    def test_empty_context_roundtrip(self, tmp_path: Path) -> None:
        """Should handle empty context."""
        cache = CacheManager(tmp_path)

        ctx = CodeContext(root_summary="", modules={})
        cache.save_code_context(ctx)
        result = cache.load_code_context()

        assert result is not None
        assert result.root_summary == ""
        assert len(result.modules) == 0

    def test_multiple_files_in_module(self, tmp_path: Path) -> None:
        """Should handle multiple files in a module."""
        cache = CacheManager(tmp_path)

        files = {
            "file1.py": FileContext(summary="summary 1"),
            "file2.py": FileContext(summary="summary 2"),
            "file3.py": FileContext(summary="summary 3"),
        }
        modules = {"pkg": ModuleContext(summary="pkg", files=files, submodules={})}
        ctx = CodeContext(root_summary="root", modules=modules)

        cache.save_code_context(ctx)
        result = cache.load_code_context()

        assert result is not None
        pkg_files = result.modules["pkg"].files
        assert len(pkg_files) == 3
        assert pkg_files["file1.py"].summary == "summary 1"
        assert pkg_files["file2.py"].summary == "summary 2"
        assert pkg_files["file3.py"].summary == "summary 3"


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


class TestCacheManagerEdgeCases:
    """Tests for edge cases and error handling."""

    def test_ensure_cache_dir_idempotent(self, tmp_path: Path) -> None:
        """Calling _ensure_cache_dir multiple times should not error."""
        cache = CacheManager(tmp_path)

        cache._ensure_cache_dir()
        cache._ensure_cache_dir()
        cache._ensure_cache_dir()

        assert cache.cache_dir.exists()

    def test_save_code_context_creates_json_structure(self, tmp_path: Path) -> None:
        """Should save context in JSON format."""
        cache = CacheManager(tmp_path)

        files = {"test.py": FileContext(summary="test")}
        modules = {"pkg": ModuleContext(summary="pkg", files=files, submodules={})}
        ctx = CodeContext(root_summary="root", modules=modules)
        cache.save_code_context(ctx)

        context_file = cache.cache_dir / CacheManager.CODE_CONTEXT_FILENAME
        with open(context_file) as f:
            data = json.load(f)

        assert "root_summary" in data
        assert "modules" in data
        assert data["root_summary"] == "root"

    def test_load_code_context_handles_corrupt_file(self, tmp_path: Path) -> None:
        """Should return None when context file is corrupt."""
        cache = CacheManager(tmp_path)

        # Create corrupt JSON file
        cache_dir = tmp_path / ".codemonkey"
        cache_dir.mkdir()
        context_file = cache_dir / CacheManager.CODE_CONTEXT_FILENAME
        context_file.write_text("{invalid json}")

        result = cache.load_code_context()

        assert result is None

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
