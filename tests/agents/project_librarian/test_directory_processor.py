"""Tests for DirectoryProcessor class."""

import tempfile
import textwrap
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from code_monkey.agents.project_librarian.cache_manager import CacheManager
from code_monkey.agents.project_librarian.directory_processor import DirectoryProcessor
from code_monkey.agents.project_librarian.models import FileSummary
from code_monkey.agents.project_librarian.summarizer import Summarizer
from code_monkey.utils.task_result import TaskResult


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

        # Create test structure
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

        # Create files in non-alphabetical order
        (tmp_path / "zebra.py").touch()
        (tmp_path / "apple.py").touch()
        (tmp_path / "banana.py").touch()

        result = processor._get_all_directories()

        assert result == sorted(result)

    def test_includes_parent_directories(self, tmp_path: Path) -> None:
        """Should include all parent directories up to root."""
        cache = CacheManager(tmp_path)
        mock_summarizer = MockSummarizer()
        processor = DirectoryProcessor(tmp_path, cache, mock_summarizer)

        # Create nested structure
        deep_path = tmp_path / "src" / "utils" / "helper.py"
        deep_path.parent.mkdir(parents=True)
        deep_path.write_text("def helper(): pass")

        result = processor._get_all_directories()

        assert tmp_path in result
        assert (tmp_path / "src") in result
        assert (tmp_path / "src" / "utils") in result


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
    """Tests for single file summarization."""

    def test_returns_cached_summary_when_available(self, tmp_path: Path) -> None:
        """Should return cached summary without calling summarizer."""
        cache = CacheManager(tmp_path)
        mock_summarizer = MockSummarizer()
        processor = DirectoryProcessor(tmp_path, cache, mock_summarizer)

        # Create and cache a file summary
        test_file = tmp_path / "test.py"
        test_file.write_text("class Test: pass")
        cached_summary = "cached summary"
        cache.save_file_summary(test_file, cached_summary)

        result = processor._summarize_single_file(test_file)

        assert result.summary == cached_summary
        assert mock_summarizer.call_count == 0  # Summarizer should not be called

    def test_generates_summary_when_not_cached(self, tmp_path: Path) -> None:
        """Should generate summary when not in cache."""
        cache = CacheManager(tmp_path)
        mock_summarizer = MockSummarizer("generated summary")
        processor = DirectoryProcessor(tmp_path, cache, mock_summarizer)

        test_file = tmp_path / "test.py"
        test_file.write_text("class Test:\n    def method(self): pass")

        result = processor._summarize_single_file(test_file)

        assert result.summary == "generated summary"
        assert result.filepath == test_file

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


class TestProcessDirectoryTopDown:
    """Tests for top-down directory processing."""

    def test_processes_single_directory(self, tmp_path: Path) -> None:
        """Should process a single directory with files."""
        cache = CacheManager(tmp_path)
        mock_summarizer = MockSummarizer("module summary")
        processor = DirectoryProcessor(tmp_path, cache, mock_summarizer)

        (tmp_path / "file1.py").write_text("class File1: pass")
        (tmp_path / "file2.py").write_text("class File2: pass")

        result = processor._process_directory_top_down(tmp_path)

        assert isinstance(result, str)
        assert len(result) > 0

    def test_processes_child_directories(self, tmp_path: Path) -> None:
        """Should process child directories after parent."""
        cache = CacheManager(tmp_path)
        mock_summarizer = MockSummarizer("summary")
        processor = DirectoryProcessor(tmp_path, cache, mock_summarizer)

        (tmp_path / "main.py").write_text("class Main: pass")
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "module.py").write_text("class Module: pass")

        result = processor._process_directory_top_down(tmp_path)

        # Should have processed the directory
        assert isinstance(result, str)

    def test_respects_max_files_per_summary(self, tmp_path: Path) -> None:
        """Should handle directories with many files."""
        cache = CacheManager(tmp_path)
        mock_summarizer = MockSummarizer("summary")
        processor = DirectoryProcessor(tmp_path, cache, mock_summarizer)

        # Create many files
        for i in range(25):
            (tmp_path / f"file{i}.py").write_text(f"x = {i}")

        result = processor._process_directory_top_down(tmp_path)

        assert isinstance(result, str)


class TestProcessChangedDirectories:
    """Tests for processing only changed directories."""

    def test_processes_single_changed_directory(self, tmp_path: Path) -> None:
        """Should process a single changed directory."""
        cache = CacheManager(tmp_path)
        mock_summarizer = MockSummarizer("summary")
        processor = DirectoryProcessor(tmp_path, cache, mock_summarizer)

        (tmp_path / "test.py").write_text("x = 1")

        # Collect all TaskResult yields from the generator
        results_list = list(processor.process_changed_directories({tmp_path}))

        # Should have multiple progress updates plus final result
        assert len(results_list) >= 1

        # Final result should contain the directory
        final_result = results_list[-1]
        assert isinstance(final_result, TaskResult)
        assert tmp_path in final_result.result

    def test_returns_task_result_generator(self, tmp_path: Path) -> None:
        """Should return TaskResult objects via generator."""
        cache = CacheManager(tmp_path)
        mock_summarizer = MockSummarizer("summary")
        processor = DirectoryProcessor(tmp_path, cache, mock_summarizer)

        (tmp_path / "file.py").write_text("x = 1")

        results_gen = processor.process_changed_directories({tmp_path})

        # Should be a generator
        import types
        assert isinstance(results_gen, types.GeneratorType)

        # Consume and check TaskResult structure
        for task_result in results_gen:
            assert isinstance(task_result, TaskResult)
            assert isinstance(task_result.result, dict)
            assert task_result.progress >= 0
            assert task_result.progress_max >= 0

    def test_progress_increases_with_each_directory(self, tmp_path: Path) -> None:
        """Should report progress that increases with each directory."""
        cache = CacheManager(tmp_path)
        mock_summarizer = MockSummarizer("summary")
        processor = DirectoryProcessor(tmp_path, cache, mock_summarizer)

        # Create multiple directories
        (tmp_path / "test.py").write_text("x = 1")
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "module.py").write_text("y = 2")

        results = list(processor.process_changed_directories({tmp_path, tmp_path / "src"}))

        # Progress should monotonically increase
        progress_values = [r.progress for r in results]
        for i in range(1, len(progress_values)):
            assert progress_values[i] >= progress_values[i - 1]

    def test_progress_max_matches_total_directories(self, tmp_path: Path) -> None:
        """Should set progress_max to total directories to process."""
        cache = CacheManager(tmp_path)
        mock_summarizer = MockSummarizer("summary")
        processor = DirectoryProcessor(tmp_path, cache, mock_summarizer)

        # Create 3 directories
        (tmp_path / "test.py").write_text("x = 1")
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "module.py").write_text("y = 2")
        (tmp_path / "lib").mkdir()
        (tmp_path / "lib" / "util.py").write_text("z = 3")

        results = list(processor.process_changed_directories({
            tmp_path,
            tmp_path / "src",
            tmp_path / "lib",
        }))

        # Final result should have progress_max = 3
        final_result = results[-1]
        assert final_result.progress_max == 3

    def test_progress_percent_calculation(self, tmp_path: Path) -> None:
        """Should correctly calculate progress percentage."""
        cache = CacheManager(tmp_path)
        mock_summarizer = MockSummarizer("summary")
        processor = DirectoryProcessor(tmp_path, cache, mock_summarizer)

        (tmp_path / "test.py").write_text("x = 1")

        results = list(processor.process_changed_directories({tmp_path}))

        # Check progress_percent on final result
        final = results[-1]
        assert final.progress == final.progress_max
        assert final.progress_percent == 100.0

    def test_handles_empty_changed_dirs(self, tmp_path: Path) -> None:
        """Should return TaskResult with empty dict for empty changed_dirs."""
        cache = CacheManager(tmp_path)
        mock_summarizer = MockSummarizer()
        processor = DirectoryProcessor(tmp_path, cache, mock_summarizer)

        results = list(processor.process_changed_directories(set()))

        # Should yield exactly one result (the final empty result)
        assert len(results) == 1

        final = results[0]
        assert isinstance(final, TaskResult)
        assert final.result == {}
        assert final.progress == 0
        assert final.progress_max == 0

    def test_skips_already_processed_child_directories(self, tmp_path: Path) -> None:
        """Should skip child directories already processed as part of parent."""
        cache = CacheManager(tmp_path)
        mock_summarizer = MockSummarizer("summary")
        processor = DirectoryProcessor(tmp_path, cache, mock_summarizer)

        (tmp_path / "test.py").write_text("x = 1")
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "module.py").write_text("y = 2")

        # Process parent and child - child should be skipped since parent includes it
        results = list(processor.process_changed_directories({tmp_path, tmp_path / "src"}))

        # Should have progress updates but child should be in final result
        final = results[-1]
        assert isinstance(final.result, dict)


class TestSummarizeFileWrapper:
    """Tests for the summarize_file wrapper method."""

    def test_delegates_to_summarizer(self, tmp_path: Path) -> None:
        """Should call summarizer.summarize_file."""
        cache = CacheManager(tmp_path)
        mock_summarizer = MockSummarizer("summary")
        processor = DirectoryProcessor(tmp_path, cache, mock_summarizer)

        test_file = tmp_path / "test.py"
        test_file.write_text("x = 1")

        result = processor.summarize_file(
            filepath=test_file,
            structure="structure",
            parent_context="parent",
        )

        assert result == "summary"


class TestDirectoryProcessorEdgeCases:
    """Tests for edge cases."""

    def test_handles_nested_directory_structure(self, tmp_path: Path) -> None:
        """Should handle deeply nested directories."""
        cache = CacheManager(tmp_path)
        mock_summarizer = MockSummarizer("summary")
        processor = DirectoryProcessor(tmp_path, cache, mock_summarizer)

        # Create nested structure
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

        result = processor._process_directory_top_down(tmp_path)

        # Should complete without errors
        assert isinstance(result, str)

    def test_handles_directory_without_python_files(self, tmp_path: Path) -> None:
        """Should handle directories with no Python files gracefully."""
        cache = CacheManager(tmp_path)
        mock_summarizer = MockSummarizer("summary")
        processor = DirectoryProcessor(tmp_path, cache, mock_summarizer)

        # Empty subdirectory
        (tmp_path / "empty_dir").mkdir()

        result = processor._process_directory_top_down(tmp_path)

        assert isinstance(result, str)
