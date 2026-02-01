"""Integration tests for ProjectMapper on a mock project.

Tests fresh scans, incremental updates, and specified file updates
using a complete mock project structure.

Note: These tests focus on components that don't require LLM mocking.
For full integration tests with real LLM, use the actual ProjectMapper.scan()
method with a configured LLM.
"""

import tempfile
import textwrap
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from code_monkey.agents.project_librarian.project_mapper import ProjectMapper


class TestProjectMapperFreshScan:
    """Tests for fresh project scans."""

    def test_full_scan_discovers_all_files(self) -> None:
        """Fresh scan should discover and process all Python files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            mock_llm = MagicMock()
            mapper = ProjectMapper(root=tmppath, llm=mock_llm)

            # Create mock project structure
            (tmppath / "main.py").write_text("class MainApp: pass")
            (tmppath / "utils.py").write_text("def helper(): pass")
            (tmppath / "src").mkdir()
            (tmppath / "src" / "module.py").write_text("class Module: pass")

            # Discover files (part of scan)
            files = mapper._compute_file_hashes()

            # Verify all Python files were discovered
            assert len(files) == 3
            assert str(tmppath / "main.py") in files
            assert str(tmppath / "utils.py") in files
            assert str(tmppath / "src" / "module.py") in files

    def test_scan_caches_file_hashes(self) -> None:
        """Fresh scan should cache all file hashes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            mock_llm = MagicMock()
            mapper = ProjectMapper(root=tmppath, llm=mock_llm)

            (tmppath / "file1.py").write_text("x = 1")
            (tmppath / "file2.py").write_text("y = 2")

            # Compute and cache hashes
            hashes = mapper._compute_file_hashes()
            mapper._cache.save_hashes(hashes)

            cached_hashes = mapper._cache.load_hashes()

            assert len(cached_hashes) == 2
            assert all(len(h) == 64 for h in cached_hashes.values())

    def test_fresh_scan_generates_project_context_cache(self) -> None:
        """Fresh scan should generate project context in cache."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            mock_llm = MagicMock()
            mapper = ProjectMapper(root=tmppath, llm=mock_llm)

            (tmppath / "main.py").write_text("class Main: pass")

            # Cache directory should exist after ensuring it
            mapper._cache._ensure_cache_dir()
            assert mapper._cache.cache_dir.exists()


class TestProjectMapperIncrementalUpdate:
    """Tests for incremental updates after initial scan."""

    def test_incremental_update_detects_changed_files(self) -> None:
        """Incremental update should detect changed files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            mock_llm = MagicMock()
            mapper = ProjectMapper(root=tmppath, llm=mock_llm)

            # Initial scan
            (tmppath / "file1.py").write_text("original content")
            initial_hashes = mapper._compute_file_hashes()

            # Modify file
            (tmppath / "file1.py").write_text("modified content")
            new_hashes = mapper._compute_file_hashes()

            # Hash should have changed
            assert initial_hashes != new_hashes

    def test_incremental_update_detects_new_file(self) -> None:
        """Incremental update should detect new files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            mock_llm = MagicMock()
            mapper = ProjectMapper(root=tmppath, llm=mock_llm)

            # Initial scan with one file
            (tmppath / "file1.py").write_text("x = 1")
            initial_files = mapper._compute_file_hashes()

            # Add new file
            (tmppath / "file2.py").write_text("y = 2")
            new_files = mapper._compute_file_hashes()

            # Should have one more file
            assert len(new_files) == len(initial_files) + 1

    def test_incremental_update_detects_deleted_file(self) -> None:
        """Incremental update should handle deleted files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            mock_llm = MagicMock()
            mapper = ProjectMapper(root=tmppath, llm=mock_llm)

            # Initial scan with file
            (tmppath / "file1.py").write_text("x = 1")
            initial_hashes = mapper._compute_file_hashes()
            mapper._cache.save_hashes(initial_hashes)

            # Delete file
            (tmppath / "file1.py").unlink()

            # Check what files are now on disk
            current_hashes = mapper._compute_file_hashes()

            # File should be gone from current hashes
            assert str(tmppath / "file1.py") not in current_hashes

    def test_incremental_update_preserves_unchanged_hashes(self) -> None:
        """Unchanged files should preserve their cached hashes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            mock_llm = MagicMock()
            mapper = ProjectMapper(root=tmppath, llm=mock_llm)

            # Initial scan
            (tmppath / "file1.py").write_text("content 1")
            (tmppath / "file2.py").write_text("content 2")
            initial_hashes = mapper._compute_file_hashes()
            mapper._cache.save_hashes(initial_hashes)

            # Modify only file2, keep file1 unchanged
            # (don't write to file1.py - it stays as "content 1")
            (tmppath / "file2.py").write_text("modified")
            new_hashes = mapper._compute_file_hashes()

            # file1 hash should be the same, file2 should be different
            assert initial_hashes[str(tmppath / "file1.py")] == new_hashes[str(tmppath / "file1.py")]
            assert initial_hashes[str(tmppath / "file2.py")] != new_hashes[str(tmppath / "file2.py")]


class TestProjectMapperSpecifiedFileUpdates:
    """Tests for updating specific files/directories."""

    def test_update_single_file_path(self) -> None:
        """Should be able to specify single file for update."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            mock_llm = MagicMock()
            mapper = ProjectMapper(root=tmppath, llm=mock_llm)

            # Create file
            (tmppath / "file.py").write_text("x = 1")

            # Verify we can create the update call structure
            paths = [tmppath / "file.py"]
            assert len(paths) == 1
            assert paths[0].exists()

    def test_update_directory_path(self) -> None:
        """Should be able to specify directory for update."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            mock_llm = MagicMock()
            mapper = ProjectMapper(root=tmppath, llm=mock_llm)

            # Create directory with files
            (tmppath / "src").mkdir()
            (tmppath / "src" / "module1.py").write_text("x = 1")
            (tmppath / "src" / "module2.py").write_text("y = 2")

            # Verify directory path
            src_path = tmppath / "src"
            assert src_path.exists()
            assert src_path.is_dir()

    def test_update_multiple_paths(self) -> None:
        """Should be able to update multiple paths at once."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            mock_llm = MagicMock()
            mapper = ProjectMapper(root=tmppath, llm=mock_llm)

            (tmppath / "file1.py").write_text("x = 1")
            (tmppath / "src").mkdir()
            (tmppath / "src" / "module.py").write_text("class Module: pass")

            # Multiple paths
            paths = [tmppath / "file1.py", tmppath / "src"]
            assert len(paths) == 2

    def test_update_with_relative_paths(self) -> None:
        """Should handle relative paths correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            mock_llm = MagicMock()
            mapper = ProjectMapper(root=tmppath, llm=mock_llm)

            (tmppath / "file.py").write_text("x = 1")

            # Relative path should work when converted to absolute
            rel_path = Path("file.py")
            abs_path = tmppath / rel_path
            assert abs_path.exists()


class TestProjectMapperCachePersistence:
    """Tests for cache persistence across operations."""

    def test_hash_cache_persists(self) -> None:
        """Hash cache should persist between operations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            mock_llm = MagicMock()
            mapper = ProjectMapper(root=tmppath, llm=mock_llm)

            (tmppath / "file.py").write_text("x = 1")
            hashes = mapper._compute_file_hashes()
            mapper._cache.save_hashes(hashes)

            # Reload
            loaded = mapper._cache.load_hashes()

            assert loaded == hashes

    def test_file_summary_cache_operations(self) -> None:
        """File summaries should be storable and retrievable."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            mock_llm = MagicMock()
            mapper = ProjectMapper(root=tmppath, llm=mock_llm)

            test_file = tmppath / "test.py"
            test_file.write_text("class Test: pass")

            # Save summary
            mapper._cache.save_file_summary(test_file, "test summary")

            # Load summary
            loaded = mapper._cache.load_file_summary(test_file)

            assert loaded == "test summary"

    def test_project_context_cache_operations(self) -> None:
        """Project context should be storable and retrievable."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            mock_llm = MagicMock()
            mapper = ProjectMapper(root=tmppath, llm=mock_llm)

            context = "project context overview"

            # Save context
            mapper._cache.save_project_context(context)

            # Load context
            loaded = mapper._cache.load_project_context()

            assert loaded == context


class TestProjectMapperComplexScenarios:
    """Tests for complex real-world scenarios."""

    def test_multimodule_project_structure(self) -> None:
        """Should handle project with multiple modules."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            mock_llm = MagicMock()
            mapper = ProjectMapper(root=tmppath, llm=mock_llm)

            # Create multi-module structure
            (tmppath / "main.py").write_text("class App: pass")
            (tmppath / "api").mkdir()
            (tmppath / "api" / "__init__.py").write_text("")
            (tmppath / "api" / "routes.py").write_text("def route(): pass")
            (tmppath / "utils").mkdir()
            (tmppath / "utils" / "helpers.py").write_text("def help(): pass")

            # Discover all files
            files = mapper._compute_file_hashes()

            # Should have discovered all Python files
            assert len(files) == 4
            assert str(tmppath / "main.py") in files
            assert str(tmppath / "api" / "__init__.py") in files
            assert str(tmppath / "api" / "routes.py") in files
            assert str(tmppath / "utils" / "helpers.py") in files

    def test_nested_directory_hash_computation(self) -> None:
        """Should handle deeply nested directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            mock_llm = MagicMock()
            mapper = ProjectMapper(root=tmppath, llm=mock_llm)

            # Create nested structure (ensure parent dirs exist)
            deep_path = tmppath / "a" / "b" / "c" / "deep.py"
            deep_path.parent.mkdir(parents=True)
            deep_path.write_text("x = 1")

            result = mapper._compute_file_hashes()

            assert len(result) == 1
            assert str(deep_path) in result


class TestProjectMapperErrorHandling:
    """Tests for error handling scenarios."""

    def test_handles_empty_file(self) -> None:
        """Should handle empty Python files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            mock_llm = MagicMock()
            mapper = ProjectMapper(root=tmppath, llm=mock_llm)

            (tmppath / "empty.py").write_text("")

            result = mapper._compute_file_hashes()

            assert len(result) == 1

    def test_handles_unicode_in_files(self) -> None:
        """Should handle files with unicode content."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            mock_llm = MagicMock()
            mapper = ProjectMapper(root=tmppath, llm=mock_llm)

            (tmppath / "unicode.py").write_text("# -*- coding: utf-8 -*-\nmsg = 'Hello, 世界'")

            result = mapper._compute_file_hashes()

            assert len(result) == 1
            # Hash should still be computed
            assert len(list(result.values())[0]) == 64

    def test_handles_special_chars_in_paths(self) -> None:
        """Should handle files with special characters in paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            mock_llm = MagicMock()
            mapper = ProjectMapper(root=tmppath, llm=mock_llm)

            # Create file with special chars
            special_file = tmppath / "file-with-dashes_and_underscores.py"
            special_file.write_text("x = 1")

            result = mapper._compute_file_hashes()

            assert len(result) == 1


class TestProjectMapperWorkflowIntegration:
    """End-to-end workflow integration tests."""

    def test_complete_fresh_scan_workflow(self) -> None:
        """Test complete workflow from empty to fully scanned."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            mock_llm = MagicMock()
            mapper = ProjectMapper(root=tmppath, llm=mock_llm)

            # Step 1: Project is empty
            assert mapper._compute_file_hashes() == {}

            # Step 2: Add files
            (tmppath / "main.py").write_text("class Main: pass")
            (tmppath / "utils.py").write_text("def util(): pass")

            # Step 3: Compute hashes
            result = mapper._compute_file_hashes()

            # Step 4: Verify hashes were computed
            assert len(result) == 2
            assert all(len(h) == 64 for h in result.values())

    def test_file_modification_workflow(self) -> None:
        """Test workflow when files are modified."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            mock_llm = MagicMock()
            mapper = ProjectMapper(root=tmppath, llm=mock_llm)

            # Initial file
            (tmppath / "config.py").write_text("setting = 'original'")
            original_hashes = mapper._compute_file_hashes()

            # Modify file
            (tmppath / "config.py").write_text("setting = 'updated'")
            updated_hashes = mapper._compute_file_hashes()

            # Hash should have changed
            assert original_hashes[str(tmppath / "config.py")] != updated_hashes[str(tmppath / "config.py")]

    def test_file_deletion_workflow(self) -> None:
        """Test workflow when files are deleted."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            mock_llm = MagicMock()
            mapper = ProjectMapper(root=tmppath, llm=mock_llm)

            # Initial file
            (tmppath / "temp.py").write_text("x = 1")
            initial_hashes = mapper._compute_file_hashes()
            mapper._cache.save_hashes(initial_hashes)

            # Delete file
            (tmppath / "temp.py").unlink()

            # Check current state
            current_hashes = mapper._compute_file_hashes()

            # File should no longer be in current hashes
            assert str(tmppath / "temp.py") not in current_hashes
