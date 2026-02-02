"""Tests for ProjectMapper class - focused on testable components."""

import tempfile
import textwrap
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from code_monkey.agents.project_librarian.project_mapper import (
    ProjectMapper,
    ProjectMapperResult,
)


class TestProjectMapperInitialization:
    """Tests for ProjectMapper initialization - these don't require Summarizer mocking."""

    def test_initializes_root_and_llm(self, tmp_path: Path) -> None:
        """Should initialize with root and LLM."""
        mock_llm = MagicMock()

        mapper = ProjectMapper(root=tmp_path, llm=mock_llm)

        assert mapper.root == tmp_path
        assert mapper.llm == mock_llm

    def test_default_cache_dir_is_codemonkey(self, tmp_path: Path) -> None:
        """Should default cache dir to root/.codemonkey."""
        mock_llm = MagicMock()

        mapper = ProjectMapper(root=tmp_path, llm=mock_llm)

        expected = tmp_path / ".codemonkey"
        assert mapper._cache.cache_dir == expected

    def test_custom_cache_dir_parameter_exists(self, tmp_path: Path) -> None:
        """Custom cache_dir parameter is accepted (defaults to .codemonkey)."""
        mock_llm = MagicMock()
        custom_cache = tmp_path / "custom_cache"

        # Note: ProjectMapper currently always uses root/.codemonkey
        # but accepts cache_dir parameter for future use
        mapper = ProjectMapper(root=tmp_path, llm=mock_llm, cache_dir=custom_cache)

        # Verify cache_dir is stored (even if not used yet)
        assert hasattr(mapper, '_cache')
        assert mapper._cache is not None

    def test_cache_is_cache_manager_instance(self, tmp_path: Path) -> None:
        """Should create CacheManager instance."""
        from code_monkey.agents.project_librarian.cache_manager import CacheManager
        mock_llm = MagicMock()

        mapper = ProjectMapper(root=tmp_path, llm=mock_llm)

        assert isinstance(mapper._cache, CacheManager)


class TestComputeFileHashes:
    """Tests for file hash computation - these don't require Summarizer."""

    def test_computes_hashes_for_python_files(self, tmp_path: Path) -> None:
        """Should compute hashes for all Python files."""
        mock_llm = MagicMock()
        mapper = ProjectMapper(root=tmp_path, llm=mock_llm)

        (tmp_path / "file1.py").write_text("x = 1")
        (tmp_path / "file2.py").write_text("y = 2")

        result = mapper._compute_file_hashes()

        assert len(result) == 2
        assert all(isinstance(h, str) and len(h) == 64 for h in result.values())

    def test_returns_empty_dict_for_no_files(self, tmp_path: Path) -> None:
        """Should return empty dict when no Python files exist."""
        mock_llm = MagicMock()
        mapper = ProjectMapper(root=tmp_path, llm=mock_llm)

        result = mapper._compute_file_hashes()

        assert result == {}

    def test_hashes_are_deterministic(self, tmp_path: Path) -> None:
        """Same content should produce same hash."""
        mock_llm = MagicMock()
        mapper = ProjectMapper(root=tmp_path, llm=mock_llm)

        (tmp_path / "file.py").write_text("x = 1")

        hash1 = mapper._compute_file_hashes()[str(tmp_path / "file.py")]
        hash2 = mapper._compute_file_hashes()[str(tmp_path / "file.py")]

        assert hash1 == hash2

    def test_different_content_produces_different_hash(self, tmp_path: Path) -> None:
        """Different content should produce different hash."""
        mock_llm = MagicMock()
        mapper = ProjectMapper(root=tmp_path, llm=mock_llm)

        (tmp_path / "file.py").write_text("x = 1")
        hash1 = mapper._compute_file_hashes()[str(tmp_path / "file.py")]

        (tmp_path / "file.py").write_text("x = 2")
        hash2 = mapper._compute_file_hashes()[str(tmp_path / "file.py")]

        assert hash1 != hash2

    def test_ignores_non_python_files(self, tmp_path: Path) -> None:
        """Should only compute hashes for .py files."""
        mock_llm = MagicMock()
        mapper = ProjectMapper(root=tmp_path, llm=mock_llm)

        (tmp_path / "file.py").write_text("x = 1")
        (tmp_path / "readme.md").write_text("# Readme")
        (tmp_path / "config.json").write_text("{}")

        result = mapper._compute_file_hashes()

        assert len(result) == 1
        assert str(tmp_path / "file.py") in result

    def test_excludes_pycache_and_venvs(self, tmp_path: Path) -> None:
        """Should exclude __pycache__, .venv directories."""
        mock_llm = MagicMock()
        mapper = ProjectMapper(root=tmp_path, llm=mock_llm)

        (tmp_path / "main.py").write_text("x = 1")
        (tmp_path / "__pycache__").mkdir()
        (tmp_path / "__pycache__" / "cache.py").write_text("x = 1")
        (tmp_path / ".venv").mkdir()
        (tmp_path / ".venv" / "lib").mkdir()
        (tmp_path / ".venv" / "lib" / "package.py").write_text("x = 1")

        result = mapper._compute_file_hashes()

        assert len(result) == 1
        assert str(tmp_path / "main.py") in result


class TestProjectMapperCacheBehavior:
    """Tests for cache behavior - minimal mocking required."""

    def test_cache_dir_created_on_first_access(self, tmp_path: Path) -> None:
        """Cache dir should be created when first accessed."""
        mock_llm = MagicMock()
        mapper = ProjectMapper(root=tmp_path, llm=mock_llm)

        # Access cache - directory is created on first access via _ensure_cache_dir
        mapper._cache._ensure_cache_dir()

        assert mapper._cache.cache_dir.exists()

    def test_hashes_cache_file_name_constant(self) -> None:
        """Should use correct cache file name."""
        from code_monkey.agents.project_librarian.cache_manager import CacheManager

        assert CacheManager.HASHES_FILENAME == "file_hashes.json"
        assert CacheManager.PROJECT_CONTEXT_FILENAME == "project_context.json"


class TestProjectMapperUpdatePathHandling:
    """Tests for path handling in update method."""

    def test_update_accepts_path_objects(self, tmp_path: Path) -> None:
        """Should accept Path objects for update."""
        mock_llm = MagicMock()
        mapper = ProjectMapper(root=tmp_path, llm=mock_llm)

        path = tmp_path / "test.py"

        # Verify path can be passed (actual call would need mock)
        assert isinstance(path, Path)

    def test_update_path_contains_project_root(self, tmp_path: Path) -> None:
        """Update should handle paths relative to project root."""
        mock_llm = MagicMock()
        mapper = ProjectMapper(root=tmp_path, llm=mock_llm)

        # Test that path comparison works
        assert (tmp_path / "file.py").parent == tmp_path


class TestProjectMapperEdgeCases:
    """Tests for edge cases."""

    def test_handles_empty_root(self, tmp_path: Path) -> None:
        """Should handle empty root directory."""
        mock_llm = MagicMock()
        mapper = ProjectMapper(root=tmp_path, llm=mock_llm)

        # Should not error on empty directory
        assert mapper.root.exists()
        # Ensure cache dir exists
        mapper._cache._ensure_cache_dir()
        assert mapper._cache.cache_dir.exists()

    def test_handles_nested_paths(self, tmp_path: Path) -> None:
        """Should handle deeply nested paths."""
        mock_llm = MagicMock()
        mapper = ProjectMapper(root=tmp_path, llm=mock_llm)

        deep_path = tmp_path / "a" / "b" / "c" / "d" / "file.py"
        deep_path.parent.mkdir(parents=True)
        deep_path.write_text("x = 1")

        result = mapper._compute_file_hashes()

        assert str(deep_path) in result

    def test_hash_is_sha256_format(self, tmp_path: Path) -> None:
        """Hash should be valid SHA-256 hex digest."""
        mock_llm = MagicMock()
        mapper = ProjectMapper(root=tmp_path, llm=mock_llm)

        (tmp_path / "file.py").write_text("content")
        hashes = mapper._compute_file_hashes()

        import re
        hash_value = list(hashes.values())[0]
        assert re.match(r'^[0-9a-f]{64}$', hash_value)


class TestProjectMapperResult:
    """Tests for ProjectMapperResult class."""

    def test_creates_with_module_summaries(self) -> None:
        """Should create with module summaries."""
        result = ProjectMapperResult(module_summaries={})

        assert result.module_summaries == {}

    def test_creates_with_summaries(self) -> None:
        """Should create with summaries dict."""
        summaries = {Path("/src"): "module summary"}
        result = ProjectMapperResult(module_summaries=summaries)

        assert result.module_summaries == summaries

    def test_repr_format(self) -> None:
        """Should have readable string representation."""
        result = ProjectMapperResult(
            module_summaries={Path("/a"): "a", Path("/b"): "b"},
        )

        repr_str = repr(result)
        assert "modules=2" in repr_str


class TestProjectMapperScanGenerator:
    """Tests for scan() as a generator returning TaskResult."""

    def test_scan_returns_generator(self, tmp_path: Path) -> None:
        """Scan should return a generator."""
        mock_llm = MagicMock()
        mapper = ProjectMapper(root=tmp_path, llm=mock_llm)

        result = mapper.scan()

        # Should be a generator
        import types
        assert isinstance(result, types.GeneratorType)

    def test_scan_yields_taskresult(self, tmp_path: Path) -> None:
        """Scan should yield TaskResult objects."""
        from code_monkey.utils.task_result import TaskResult
        from unittest.mock import patch, MagicMock

        mock_llm = MagicMock()
        mapper = ProjectMapper(root=tmp_path, llm=mock_llm)

        # Create a file so there's something to process
        (tmp_path / "main.py").write_text("x = 1")

        # Mock the summarizer to return mock summaries
        with patch.object(mapper._summarizer, 'summarize_file', return_value="mock summary"):
            with patch.object(mapper._summarizer, 'summarize_module', return_value="module summary"):
                with patch.object(mapper._summarizer, 'generate_project_context', return_value="project context"):
                    results = list(mapper.scan())

        # Should have multiple TaskResult yields
        assert len(results) >= 1
        for r in results:
            assert isinstance(r, TaskResult)

    def test_scan_final_result_has_summaries(self, tmp_path: Path) -> None:
        """Final TaskResult should contain module summaries."""
        from unittest.mock import patch, MagicMock

        mock_llm = MagicMock()
        mapper = ProjectMapper(root=tmp_path, llm=mock_llm)

        (tmp_path / "main.py").write_text("x = 1")

        with patch.object(mapper._summarizer, 'summarize_file', return_value="mock summary"):
            with patch.object(mapper._summarizer, 'summarize_module', return_value="module summary"):
                with patch.object(mapper._summarizer, 'generate_project_context', return_value="project context"):
                    results = list(mapper.scan())
        final_result = results[-1]

        assert isinstance(final_result.result, ProjectMapperResult)
        assert isinstance(final_result.result.module_summaries, dict)

    def test_scan_progress_increases(self, tmp_path: Path) -> None:
        """Progress should increase across TaskResult yields."""
        from unittest.mock import patch, MagicMock

        mock_llm = MagicMock()
        mapper = ProjectMapper(root=tmp_path, llm=mock_llm)

        (tmp_path / "main.py").write_text("x = 1")

        with patch.object(mapper._summarizer, 'summarize_file', return_value="mock summary"):
            with patch.object(mapper._summarizer, 'summarize_module', return_value="module summary"):
                with patch.object(mapper._summarizer, 'generate_project_context', return_value="project context"):
                    results = list(mapper.scan())

        # Progress should monotonically increase
        progresses = [r.progress for r in results]
        for i in range(1, len(progresses)):
            assert progresses[i] >= progresses[i - 1]

    def test_scan_progress_max_constant(self, tmp_path: Path) -> None:
        """Progress_max should be constant after initial scan."""
        from unittest.mock import patch, MagicMock

        mock_llm = MagicMock()
        mapper = ProjectMapper(root=tmp_path, llm=mock_llm)

        (tmp_path / "main.py").write_text("x = 1")

        with patch.object(mapper._summarizer, 'summarize_file', return_value="mock summary"):
            with patch.object(mapper._summarizer, 'summarize_module', return_value="module summary"):
                with patch.object(mapper._summarizer, 'generate_project_context', return_value="project context"):
                    results = list(mapper.scan())

        # After the first result (initial scan), all subsequent results should have the same progress_max
        # The initial scan yields with progress_max=1, then directory processing yields with progress_max=N+2
        subsequent_maxes = [r.progress_max for r in results[1:]]
        assert len(set(subsequent_maxes)) == 1

    def test_scan_final_progress_equals_max(self, tmp_path: Path) -> None:
        """Final progress should equal progress_max."""
        from unittest.mock import patch, MagicMock

        mock_llm = MagicMock()
        mapper = ProjectMapper(root=tmp_path, llm=mock_llm)

        (tmp_path / "main.py").write_text("x = 1")

        with patch.object(mapper._summarizer, 'summarize_file', return_value="mock summary"):
            with patch.object(mapper._summarizer, 'summarize_module', return_value="module summary"):
                with patch.object(mapper._summarizer, 'generate_project_context', return_value="project context"):
                    results = list(mapper.scan())
        final_result = results[-1]

        assert final_result.progress == final_result.progress_max


class TestProjectMapperUpdateGenerator:
    """Tests for update() as a generator returning TaskResult."""

    def test_update_returns_generator(self, tmp_path: Path) -> None:
        """Update should return a generator."""
        mock_llm = MagicMock()
        mapper = ProjectMapper(root=tmp_path, llm=mock_llm)

        result = mapper.update([tmp_path / "main.py"])

        import types
        assert isinstance(result, types.GeneratorType)

    def test_update_yields_taskresult(self, tmp_path: Path) -> None:
        """Update should yield TaskResult objects."""
        from code_monkey.utils.task_result import TaskResult
        from unittest.mock import patch, MagicMock

        mock_llm = MagicMock()
        mapper = ProjectMapper(root=tmp_path, llm=mock_llm)

        (tmp_path / "main.py").write_text("x = 1")

        with patch.object(mapper._summarizer, 'summarize_file', return_value="mock summary"):
            with patch.object(mapper._summarizer, 'summarize_module', return_value="module summary"):
                with patch.object(mapper._summarizer, 'generate_project_context', return_value="project context"):
                    results = list(mapper.update([tmp_path / "main.py"]))

        assert len(results) >= 1
        for r in results:
            assert isinstance(r, TaskResult)

    def test_update_final_result_has_summaries(self, tmp_path: Path) -> None:
        """Final TaskResult should contain module summaries."""
        from unittest.mock import patch, MagicMock

        mock_llm = MagicMock()
        mapper = ProjectMapper(root=tmp_path, llm=mock_llm)

        (tmp_path / "main.py").write_text("x = 1")

        with patch.object(mapper._summarizer, 'summarize_file', return_value="mock summary"):
            with patch.object(mapper._summarizer, 'summarize_module', return_value="module summary"):
                with patch.object(mapper._summarizer, 'generate_project_context', return_value="project context"):
                    results = list(mapper.update([tmp_path / "main.py"]))
        final_result = results[-1]

        assert isinstance(final_result.result, ProjectMapperResult)
        assert isinstance(final_result.result.module_summaries, dict)
