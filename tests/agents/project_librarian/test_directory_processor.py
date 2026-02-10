"""Tests for DirectoryProcessor class with ModuleContext structure."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from code_monkey.agents.project_librarian.cache_manager import (
    CacheManager,
)
from code_monkey.agents.project_librarian.directory_processor import DirectoryProcessor
from code_monkey.agents.project_librarian.summarizer import Summarizer
from code_monkey.agents.project_librarian.types import FileContext, ModuleContext


class MockSummarizer:
    """Mock summarizer for testing."""

    def __init__(self, return_value: str = "summary"):
        self._return_value = return_value
        self.call_count = 0

    def summarize_file(self, filepath, structure, parent_context=None):
        self.call_count += 1
        return self._return_value

    def summarize_module(self, directory, file_summaries, parent_context=None):
        self.call_count += 1
        return self._return_value


class TestDirectoryProcessorInitialization:
    """Tests for DirectoryProcessor initialization."""

    def test_initializes_with_components(self, tmp_path: Path) -> None:
        """Should initialize with root, cache, and summarizer."""
        cache = CacheManager(tmp_path)
        mock_llm = MagicMock()
        summarizer = Summarizer(mock_llm)

        processor = DirectoryProcessor(tmp_path, cache, summarizer)

        assert processor.root == tmp_path
        assert processor.cache == cache
        assert processor.summarizer == summarizer

    def test_max_files_per_summary_default(self) -> None:
        """Should have correct default MAX_FILES_PER_SUMMARY."""
        assert DirectoryProcessor.MAX_FILES_PER_SUMMARY == 20


class TestGetAllDirectories:
    """Tests for directory discovery."""

    def test_returns_empty_for_no_python_files(self, tmp_path: Path) -> None:
        """Should return empty list when no Python files exist."""
        cache = CacheManager(tmp_path)
        mock_summarizer = MockSummarizer()
        processor = DirectoryProcessor(tmp_path, cache, mock_summarizer)

        result = processor._get_all_directories()

        assert result == []

    def test_returns_directories_with_python_files(self, tmp_path: Path) -> None:
        """Should return directories containing Python files."""
        cache = CacheManager(tmp_path)
        mock_summarizer = MockSummarizer()
        processor = DirectoryProcessor(tmp_path, cache, mock_summarizer)

        (tmp_path / "main.py").write_text("class Main: pass")
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "module.py").write_text("class Module: pass")

        result = processor._get_all_directories()

        assert tmp_path in result
        assert (tmp_path / "src") in result

    def test_returns_sorted_directories(self, tmp_path: Path) -> None:
        """Should return directories in sorted order."""
        cache = CacheManager(tmp_path)
        mock_summarizer = MockSummarizer()
        processor = DirectoryProcessor(tmp_path, cache, mock_summarizer)

        (tmp_path / "zebra.py").touch()
        (tmp_path / "apple.py").touch()
        (tmp_path / "banana.py").touch()

        result = processor._get_all_directories()

        assert result == sorted(result)


class TestGetFilesInDirectory:
    """Tests for file discovery within a directory."""

    def test_returns_python_files_in_directory(self, tmp_path: Path) -> None:
        """Should return only .py files from directory."""
        cache = CacheManager(tmp_path)
        mock_summarizer = MockSummarizer()
        processor = DirectoryProcessor(tmp_path, cache, mock_summarizer)

        (tmp_path / "file1.py").write_text("x = 1")
        (tmp_path / "file2.py").write_text("y = 2")
        (tmp_path / "readme.md").write_text("# Readme")

        result = processor._get_files_in_directory(tmp_path)

        assert len(result) == 2
        assert all(f.suffix == ".py" for f in result)

    def test_returns_sorted_files(self, tmp_path: Path) -> None:
        """Should return files in sorted order."""
        cache = CacheManager(tmp_path)
        mock_summarizer = MockSummarizer()
        processor = DirectoryProcessor(tmp_path, cache, mock_summarizer)

        (tmp_path / "zebra.py").touch()
        (tmp_path / "apple.py").touch()

        result = processor._get_files_in_directory(tmp_path)

        assert result == sorted(result)

    def test_returns_empty_for_no_python_files(self, tmp_path: Path) -> None:
        """Should return empty list for directory without Python files."""
        cache = CacheManager(tmp_path)
        mock_summarizer = MockSummarizer()
        processor = DirectoryProcessor(tmp_path, cache, mock_summarizer)

        (tmp_path / "readme.md").write_text("# No Python here")

        result = processor._get_files_in_directory(tmp_path)

        assert result == []


class TestSummarizeSingleFile:
    """Tests for single file summarization returning FileContext."""

    def test_returns_cached_summary_when_available(self, tmp_path: Path) -> None:
        """Should return cached summary without calling summarizer."""
        cache = CacheManager(tmp_path)
        mock_summarizer = MockSummarizer()
        processor = DirectoryProcessor(tmp_path, cache, mock_summarizer)

        test_file = tmp_path / "test.py"
        test_file.write_text("class Test: pass")
        cached_summary = "cached summary"
        cache.save_file_summary(test_file, cached_summary)

        result = processor._summarize_single_file(test_file)

        assert isinstance(result, FileContext)
        assert result.summary == cached_summary
        assert mock_summarizer.call_count == 0

    def test_generates_summary_when_not_cached(self, tmp_path: Path) -> None:
        """Should generate summary when not in cache."""
        cache = CacheManager(tmp_path)
        mock_summarizer = MockSummarizer("generated summary")
        processor = DirectoryProcessor(tmp_path, cache, mock_summarizer)

        test_file = tmp_path / "test.py"
        test_file.write_text("class Test:\n    def method(self): pass")

        result = processor._summarize_single_file(test_file)

        assert isinstance(result, FileContext)
        assert result.summary == "generated summary"

    def test_saves_summary_to_cache(self, tmp_path: Path) -> None:
        """Should save generated summary to cache."""
        cache = CacheManager(tmp_path)
        mock_summarizer = MockSummarizer("new summary")
        processor = DirectoryProcessor(tmp_path, cache, mock_summarizer)

        test_file = tmp_path / "test.py"
        test_file.write_text("x = 1")

        processor._summarize_single_file(test_file)

        cached = cache.load_file_summary(test_file)
        assert cached == "new summary"


class TestProcessDirectory:
    """Tests for directory processing returning ModuleContext."""

    def test_processes_single_directory(self, tmp_path: Path) -> None:
        """Should process a single directory with files."""
        cache = CacheManager(tmp_path)
        mock_summarizer = MockSummarizer("module summary")
        processor = DirectoryProcessor(tmp_path, cache, mock_summarizer)

        (tmp_path / "file1.py").write_text("class File1: pass")
        (tmp_path / "file2.py").write_text("class File2: pass")

        result, summary = processor._process_directory(tmp_path)

        assert isinstance(result, ModuleContext)
        assert result.summary == "module summary"
        assert len(result.files) == 2

    def test_processes_child_directories(self, tmp_path: Path) -> None:
        """Should process child directories recursively."""
        cache = CacheManager(tmp_path)
        mock_summarizer = MockSummarizer("summary")
        processor = DirectoryProcessor(tmp_path, cache, mock_summarizer)

        (tmp_path / "main.py").write_text("class Main: pass")
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "module.py").write_text("class Module: pass")

        result, _ = processor._process_directory(tmp_path)

        assert isinstance(result, ModuleContext)
        assert "src" in result.submodules

    def test_returns_module_context_structure(self, tmp_path: Path) -> None:
        """Should return proper ModuleContext with files and submodules."""
        cache = CacheManager(tmp_path)
        mock_summarizer = MockSummarizer("summary")
        processor = DirectoryProcessor(tmp_path, cache, mock_summarizer)

        (tmp_path / "file.py").write_text("x = 1")

        result, _ = processor._process_directory(tmp_path)

        assert isinstance(result, ModuleContext)
        assert hasattr(result, 'summary')
        assert hasattr(result, 'files')
        assert hasattr(result, 'submodules')
        assert isinstance(result.files, dict)
        assert isinstance(result.submodules, dict)


class TestBuildModulePath:
    """Tests for module path building."""

    def test_root_directory_returns_empty_tuple(self, tmp_path: Path) -> None:
        """Root directory should return empty tuple."""
        cache = CacheManager(tmp_path)
        mock_summarizer = MockSummarizer()
        processor = DirectoryProcessor(tmp_path, cache, mock_summarizer)

        result = processor._build_module_path(tmp_path)

        assert result == ()

    def test_single_level_module(self, tmp_path: Path) -> None:
        """Single level directory should return single tuple."""
        cache = CacheManager(tmp_path)
        mock_summarizer = MockSummarizer()
        processor = DirectoryProcessor(tmp_path, cache, mock_summarizer)

        pkg_dir = tmp_path / "pkg"
        pkg_dir.mkdir()

        result = processor._build_module_path(pkg_dir)

        assert result == ("pkg",)

    def test_nested_module(self, tmp_path: Path) -> None:
        """Nested directory should return path tuple."""
        cache = CacheManager(tmp_path)
        mock_summarizer = MockSummarizer()
        processor = DirectoryProcessor(tmp_path, cache, mock_summarizer)

        nested = tmp_path / "pkg" / "subpkg" / "deeper"
        nested.mkdir(parents=True)

        result = processor._build_module_path(nested)

        assert result == ("pkg", "subpkg", "deeper")


class TestSetModule:
    """Tests for _set_module method."""

    def test_set_module_creates_new(self, tmp_path: Path) -> None:
        """Should create new module at path."""
        cache = CacheManager(tmp_path)
        mock_summarizer = MockSummarizer()
        processor = DirectoryProcessor(tmp_path, cache, mock_summarizer)

        ctx = ModuleContext(summary="", files={}, submodules={})
        module = ModuleContext(summary="pkg", files={}, submodules={})
        result = processor._set_module(ctx, ("pkg",), module)

        assert "pkg" in result.submodules
        assert result.submodules["pkg"].summary == "pkg"

    def test_set_module_preserves_existing(self, tmp_path: Path) -> None:
        """Should preserve existing modules when setting new one."""
        cache = CacheManager(tmp_path)
        mock_summarizer = MockSummarizer()
        processor = DirectoryProcessor(tmp_path, cache, mock_summarizer)

        existing = ModuleContext(summary="existing", files={}, submodules={})
        ctx = ModuleContext(summary="", files={}, submodules={"existing": existing})
        new_module = ModuleContext(summary="new", files={}, submodules={})
        result = processor._set_module(ctx, ("new",), new_module)

        assert "existing" in result.submodules
        assert "new" in result.submodules

    def test_set_module_at_root(self, tmp_path: Path) -> None:
        """Should set summary when module_path is empty."""
        cache = CacheManager(tmp_path)
        mock_summarizer = MockSummarizer()
        processor = DirectoryProcessor(tmp_path, cache, mock_summarizer)

        ctx = ModuleContext(summary="old", files={}, submodules={})
        module = ModuleContext(summary="new root", files={}, submodules={})
        result = processor._set_module(ctx, (), module)

        assert result.summary == "new root"


class TestProcessDirectories:
    """Tests for process_directories generator."""

    def test_processes_single_directory(self, tmp_path: Path) -> None:
        """Should process a single directory."""
        cache = CacheManager(tmp_path)
        mock_summarizer = MockSummarizer("summary")
        processor = DirectoryProcessor(tmp_path, cache, mock_summarizer)

        (tmp_path / "test.py").write_text("x = 1")

        results = list(processor.process_directories({tmp_path}))

        assert len(results) >= 1
        final = results[-1]
        assert isinstance(final.result, ModuleContext)

    def test_returns_task_result_generator(self, tmp_path: Path) -> None:
        """Should return TaskResult objects via generator."""
        cache = CacheManager(tmp_path)
        mock_summarizer = MockSummarizer()
        processor = DirectoryProcessor(tmp_path, cache, mock_summarizer)

        (tmp_path / "file.py").write_text("x = 1")

        results_gen = processor.process_directories({tmp_path})

        import types
        assert isinstance(results_gen, types.GeneratorType)

        for task_result in results_gen:
            assert isinstance(task_result.result, ModuleContext)
            assert task_result.progress >= 0
            assert task_result.progress_max >= 0

    def test_progress_increases_with_each_directory(self, tmp_path: Path) -> None:
        """Should report progress that increases with each directory."""
        cache = CacheManager(tmp_path)
        mock_summarizer = MockSummarizer("summary")
        processor = DirectoryProcessor(tmp_path, cache, mock_summarizer)

        (tmp_path / "test.py").write_text("x = 1")
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "module.py").write_text("y = 2")

        results = list(processor.process_directories({tmp_path, tmp_path / "src"}))

        progress_values = [r.progress for r in results]
        for i in range(1, len(progress_values)):
            assert progress_values[i] >= progress_values[i - 1]

    def test_handles_empty_directories(self, tmp_path: Path) -> None:
        """Should return TaskResult with empty context for empty set."""
        cache = CacheManager(tmp_path)
        mock_summarizer = MockSummarizer()
        processor = DirectoryProcessor(tmp_path, cache, mock_summarizer)

        results = list(processor.process_directories(set()))

        assert len(results) == 1
        final = results[0]
        assert isinstance(final.result, ModuleContext)
        assert final.result.summary == ""
        assert len(final.result.submodules) == 0
        assert final.progress == 0
        assert final.progress_max == 0

    def test_progress_max_matches_total_directories(self, tmp_path: Path) -> None:
        """Should set progress_max to total directories."""
        cache = CacheManager(tmp_path)
        mock_summarizer = MockSummarizer("summary")
        processor = DirectoryProcessor(tmp_path, cache, mock_summarizer)

        (tmp_path / "test.py").write_text("x = 1")
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "module.py").write_text("y = 2")

        results = list(processor.process_directories({
            tmp_path,
            tmp_path / "src",
        }))

        final_result = results[-1]
        assert final_result.progress_max == 2


class TestDirectoryProcessorEdgeCases:
    """Tests for edge cases."""

    def test_handles_nested_directory_structure(self, tmp_path: Path) -> None:
        """Should handle deeply nested directories."""
        cache = CacheManager(tmp_path)
        mock_summarizer = MockSummarizer("summary")
        processor = DirectoryProcessor(tmp_path, cache, mock_summarizer)

        deep_path = tmp_path / "a" / "b" / "c" / "deep.py"
        deep_path.parent.mkdir(parents=True)
        deep_path.write_text("x = 1")

        result = processor._get_all_directories()

        assert len(result) >= 3  # a, a/b, a/b/c

    def test_excludes_codemonkey_from_child_dirs(self, tmp_path: Path) -> None:
        """Should not process .codemonkey directory."""
        cache = CacheManager(tmp_path)
        mock_summarizer = MockSummarizer("summary")
        processor = DirectoryProcessor(tmp_path, cache, mock_summarizer)

        (tmp_path / "main.py").write_text("x = 1")
        (tmp_path / ".codemonkey").mkdir()
        (tmp_path / ".codemonkey" / "cache.py").write_text("x = 1")

        result, _ = processor._process_directory(tmp_path)

        assert isinstance(result, ModuleContext)
        assert ".codemonkey" not in result.submodules

    def test_handles_directory_without_python_files(self, tmp_path: Path) -> None:
        """Should handle directories with no Python files gracefully."""
        cache = CacheManager(tmp_path)
        mock_summarizer = MockSummarizer("summary")
        processor = DirectoryProcessor(tmp_path, cache, mock_summarizer)

        (tmp_path / "empty_dir").mkdir()

        result, _ = processor._process_directory(tmp_path)

        assert isinstance(result, ModuleContext)
        assert len(result.files) == 0

    def test_includes_parent_directories(self, tmp_path: Path) -> None:
        """Should include all parent directories up to root."""
        cache = CacheManager(tmp_path)
        mock_summarizer = MockSummarizer()
        processor = DirectoryProcessor(tmp_path, cache, mock_summarizer)

        deep_path = tmp_path / "src" / "utils" / "helper.py"
        deep_path.parent.mkdir(parents=True)
        deep_path.write_text("def helper(): pass")

        result = processor._get_all_directories()

        assert tmp_path in result
        assert (tmp_path / "src") in result
        assert (tmp_path / "src" / "utils") in result
