"""Tests for CacheManager and context models."""

import json
import tempfile
from pathlib import Path

import pytest

from code_monkey.agents.project_librarian.cache_manager import (
    CacheManager,
    FileContext,
    ModuleContext,
    module_context_from_dict,
)


@pytest.fixture
def temp_root(tmp_path):
    """Create a temporary root directory for cache operations."""
    return tmp_path


@pytest.fixture
def cache_manager(temp_root):
    """Create a CacheManager instance with a temp directory."""
    return CacheManager(temp_root)


class TestFileContext:
    """Tests for FileContext dataclass."""

    def test_init_with_summary(self):
        """Test FileContext initialization with summary."""
        ctx = FileContext(summary="Test file summary")
        assert ctx.summary == "Test file summary"

    def test_default_values(self):
        """Test FileContext with default values."""
        ctx = FileContext(summary="Minimal")
        assert ctx.summary == "Minimal"


class TestModuleContext:
    """Tests for ModuleContext dataclass."""

    def test_init_with_summary(self):
        """Test ModuleContext initialization with summary."""
        ctx = ModuleContext(summary="Test module summary")
        assert ctx.summary == "Test module summary"
        assert ctx.files == {}
        assert ctx.submodules == {}

    def test_with_files(self):
        """Test ModuleContext with files dict."""
        files = {"file1.py": FileContext(summary="File 1")}
        ctx = ModuleContext(summary="Module", files=files)
        assert len(ctx.files) == 1
        assert "file1.py" in ctx.files

    def test_with_submodules(self):
        """Test ModuleContext with submodules dict."""
        submodules = {
            "subpkg": ModuleContext(summary="Submodule", files={})
        }
        ctx = ModuleContext(summary="Module", submodules=submodules)
        assert "subpkg" in ctx.submodules

    def test_nested_structure(self):
        """Test deeply nested module structure."""
        inner = ModuleContext(summary="Inner", files={})
        outer = ModuleContext(summary="Outer", submodules={"inner": inner})
        root = ModuleContext(summary="Root", submodules={"outer": outer})

        assert root.submodules["outer"].submodules["inner"].summary == "Inner"


class TestModuleContextFromDict:
    """Tests for module_context_from_dict function."""

    def test_empty_dict(self):
        """Test loading from empty dict."""
        ctx = module_context_from_dict({"summary": "Empty"})
        assert ctx.summary == "Empty"
        assert ctx.files == {}
        assert ctx.submodules == {}

    def test_with_files(self):
        """Test loading with files from dict."""
        data = {
            "summary": "Module",
            "files": {
                "test.py": {"summary": "A test file"}
            }
        }
        ctx = module_context_from_dict(data)
        assert ctx.summary == "Module"
        assert "test.py" in ctx.files
        assert ctx.files["test.py"].summary == "A test file"

    def test_nested_submodules(self):
        """Test loading with nested submodules."""
        data = {
            "summary": "Root",
            "submodules": {
                "pkg": {
                    "summary": "Package",
                    "files": {
                        "mod.py": {"summary": "Module file"}
                    }
                }
            }
        }
        ctx = module_context_from_dict(data)
        assert ctx.summary == "Root"
        assert "pkg" in ctx.submodules
        assert ctx.submodules["pkg"].summary == "Package"
        assert "mod.py" in ctx.submodules["pkg"].files


class TestCacheManagerHashes:
    """Tests for CacheManager file hashes operations."""

    def test_load_hashes_empty(self, cache_manager):
        """Test load_hashes returns empty dict when no cache."""
        hashes = cache_manager.load_hashes()
        assert hashes == {}

    def test_save_and_load_hashes(self, cache_manager):
        """Test save_hashes and load_hashes roundtrip."""
        test_hashes = {
            "/path/to/file1.py": "abc123",
            "/path/to/file2.py": "def456"
        }
        cache_manager.save_hashes(test_hashes)
        loaded = cache_manager.load_hashes()
        assert loaded == test_hashes

    def test_hashes_persistence(self, temp_root):
        """Test hashes persist across CacheManager instances."""
        cm1 = CacheManager(temp_root)
        cm1.save_hashes({"file.py": "hash123"})

        cm2 = CacheManager(temp_root)
        loaded = cm2.load_hashes()
        assert loaded == {"file.py": "hash123"}

    def test_load_hashes_corrupted_file(self, cache_manager):
        """Test load_hashes handles corrupted file gracefully."""
        cache_dir = cache_manager.cache_dir
        cache_dir.mkdir(parents=True, exist_ok=True)
        hashes_file = cache_dir / cache_manager.HASHES_FILENAME

        # Write corrupted JSON
        hashes_file.write_text("{ invalid json }")

        with pytest.raises(Exception):
            cache_manager.load_hashes()


class TestCacheManagerCodeContext:
    """Tests for CacheManager code context operations."""

    def test_load_code_context_no_cache(self, cache_manager):
        """Test load_code_context returns None when no cache."""
        ctx = cache_manager.load_code_context()
        assert ctx is None

    def test_save_and_load_code_context(self, cache_manager):
        """Test save_code_context and load_code_context roundtrip."""
        ctx = ModuleContext(
            summary="Root module",
            files={
                "main.py": FileContext(summary="Main entry")
            },
            submodules={
                "utils": ModuleContext(summary="Utilities")
            }
        )
        cache_manager.save_code_context(ctx)
        loaded = cache_manager.load_code_context()

        assert loaded is not None
        assert loaded.summary == "Root module"
        assert "main.py" in loaded.files
        assert loaded.files["main.py"].summary == "Main entry"
        assert "utils" in loaded.submodules

    def test_code_context_persistence(self, temp_root):
        """Test code context persists across CacheManager instances."""
        cm1 = CacheManager(temp_root)
        original = ModuleContext(summary="Persisted module")
        cm1.save_code_context(original)

        cm2 = CacheManager(temp_root)
        loaded = cm2.load_code_context()
        assert loaded is not None
        assert loaded.summary == "Persisted module"

    def test_load_code_context_corrupted_file(self, cache_manager):
        """Test load_code_context handles corrupted file gracefully."""
        cache_dir = cache_manager.cache_dir
        cache_dir.mkdir(parents=True, exist_ok=True)
        ctx_file = cache_dir / cache_manager.CODE_CONTEXT_FILENAME

        # Write corrupted JSON
        ctx_file.write_text('{"summary": "ok", "files": { invalid }')

        loaded = cache_manager.load_code_context()
        assert loaded is None


class TestCacheManagerProjectContext:
    """Tests for CacheManager project context operations."""

    def test_load_project_context_no_cache(self, cache_manager):
        """Test load_project_context returns None when no cache."""
        ctx = cache_manager.load_project_context()
        assert ctx is None

    def test_save_and_load_project_context(self, cache_manager):
        """Test save_project_context and load_project_context roundtrip."""
        content = "# Project Context\n\nThis is a test project."
        cache_manager.save_project_context(content)
        loaded = cache_manager.load_project_context()
        assert loaded == content

    def test_project_context_persistence(self, temp_root):
        """Test project context persists across CacheManager instances."""
        cm1 = CacheManager(temp_root)
        original = "## Project Title\n\nDescription here."
        cm1.save_project_context(original)

        cm2 = CacheManager(temp_root)
        loaded = cm2.load_project_context()
        assert loaded == original


class TestCacheManagerAtomicWrites:
    """Tests for CacheManager atomic write behavior."""

    def test_atomic_json_write_creates_file(self, cache_manager):
        """Test that atomic write creates the target file."""
        test_data = {"key": "value"}
        cache_manager._ensure_cache_dir()

        target_path = cache_manager.cache_dir / "test_atomic.json"
        cache_manager._atomic_json_write(target_path, test_data)

        assert target_path.exists()
        loaded = json.loads(target_path.read_text())
        assert loaded == test_data

    def test_cache_dir_creation(self, cache_manager):
        """Test that cache directory is created on first operation."""
        assert not cache_manager.cache_dir.exists()
        cache_manager._ensure_cache_dir()
        assert cache_manager.cache_dir.exists()


class TestCacheManagerIntegration:
    """Integration tests for CacheManager."""

    def test_all_operations_together(self, temp_root):
        """Test all CacheManager operations in sequence."""
        cm = CacheManager(temp_root)

        # Save hashes
        cm.save_hashes({"file.py": "hash123"})

        # Save code context
        code_ctx = ModuleContext(summary="Module", files={})
        cm.save_code_context(code_ctx)

        # Save project context
        cm.save_project_context("Project context")

        # Load and verify all
        hashes = cm.load_hashes()
        assert hashes == {"file.py": "hash123"}

        loaded_code_ctx = cm.load_code_context()
        assert loaded_code_ctx is not None
        assert loaded_code_ctx.summary == "Module"

        loaded_proj_ctx = cm.load_project_context()
        assert loaded_proj_ctx == "Project context"
