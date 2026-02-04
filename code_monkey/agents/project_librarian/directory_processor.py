"""Directory processor for top-down traversal with parallel file processing."""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Generator

from code_monkey.agents.project_librarian.cache_manager import CacheManager
from code_monkey.agents.project_librarian.models import FileSummary
from code_monkey.agents.project_librarian.summarizer import Summarizer
from code_monkey.agents.project_librarian.utils.code_parser import parse_python_code
from code_monkey.agents.project_librarian.utils.file_discovery import discover_python_files

from code_monkey.utils.task_result import TaskResult


class DirectoryProcessor:
    """Processes directories top-down with parallel file summarization.

    Propagates parent module context to child modules for hierarchical
    understanding.
    """

    MAX_FILES_PER_SUMMARY = 20

    def __init__(
        self, root: Path, cache: CacheManager, summarizer: Summarizer
    ) -> None:
        """Initialize directory processor.

        Args:
            root: Project root directory.
            cache: Cache manager instance.
            summarizer: Summarizer instance.
        """
        self.root = root
        self.cache = cache
        self.summarizer = summarizer

    def _get_all_directories(self) -> list[Path]:
        """Get all directories containing Python files.

        Returns:
            Sorted list of directory paths, from root to leaves.
        """
        py_files = discover_python_files(self.root)
        dirs: set[Path] = set()
        for f in py_files:
            # Add all parent directories up to root
            parent = f.parent
            while parent >= self.root:
                dirs.add(parent)
                parent = parent.parent
        return sorted(dirs)

    def _get_files_in_directory(self, directory: Path) -> list[Path]:
        """Get all Python files in a directory (not recursive).

        Args:
            directory: Directory to search.

        Returns:
            Sorted list of Python file paths.
        """
        return sorted(directory.glob("*.py"))

    def _summarize_single_file(self, filepath: Path) -> FileSummary:
        """Summarize a single file (for parallel processing).

        Args:
            filepath: Path to the Python file.

        Returns:
            FileSummary with filepath and summary.
        """
        # Try to load from cache first
        cached = self.cache.load_file_summary(filepath)
        if cached is not None:
            return FileSummary(filepath=filepath, summary=cached)

        # Parse the file
        source = filepath.read_text(encoding="utf-8")
        parsed = parse_python_code(source)
        structure = parsed.llm_friendly_string(include_imports=True)

        # Generate summary
        summary = self.summarize_file(filepath, structure, parent_context=None)

        # Save to cache
        self.cache.save_file_summary(filepath, summary)

        return FileSummary(filepath=filepath, summary=summary)

    def summarize_file(
        self, filepath: Path, structure: str, parent_context: str | None = None
    ) -> str:
        """Wrapper to call summarizer with file path.

        Args:
            filepath: Path to the file.
            structure: Parsed code structure.
            parent_context: Optional parent module context.

        Returns:
            Summary string.
        """
        return self.summarizer.summarize_file(filepath, structure, parent_context)

    def _process_directory_top_down(
        self, directory: Path, parent_summary: str | None = None
    ) -> str:
        """Process a directory and all its subdirectories top-down.

        Args:
            directory: Directory to process.
            parent_summary: Summary from parent module context.

        Returns:
            Module summary for this directory.
        """
        # Get files in this directory
        files = self._get_files_in_directory(directory)

        # Parallel file processing
        with ThreadPoolExecutor() as executor:
            file_summaries = list(executor.map(self._summarize_single_file, files))

        # Extract summary strings for module summarization
        file_summary_strings = [fs.summary for fs in file_summaries]

        # Generate module summary with parent context
        module_summary = self.summarizer.summarize_module(
            directory, file_summary_strings, parent_summary
        )

        # Save module summary to cache
        self.cache.save_module_summary(directory, module_summary)

        # Process child directories
        child_dirs = sorted(
            d for d in directory.iterdir() if d.is_dir() and d.name != ".codemonkey"
        )
        for child_dir in child_dirs:
            # Check if child directory has Python files
            if any(child_dir.glob("*.py")):
                self._process_directory_top_down(child_dir, module_summary)

        return module_summary

    def process_changed_directories(
        self, changed_dirs: set[Path]
    ) -> Generator[TaskResult, Any, None]:
        """Process only specified directories and their children.

        Args:
            changed_dirs: Set of directories that have changed.

        Returns:
            TaskResult containing:
                - result: Dictionary mapping directory paths to their summaries
                - progress: Current directory index (0-based)
                - progress_max: Total number of directories to process
        """
        results: dict[Path, str] = {}

        # Sort by path depth to process parent directories first
        sorted_dirs = sorted(changed_dirs, key=lambda p: len(p.parts))
        total_dirs = len(sorted_dirs)

        for index, directory in enumerate(sorted_dirs):
            if directory in results:
                # Yield progress update even for skipped directories
                yield TaskResult(
                    result=results,
                    progress=index,
                    progress_max=total_dirs,
                )
                continue

            # Get parent summary if available
            parent_summary = None
            parent = directory.parent
            if parent >= self.root and parent in results:
                parent_summary = results[parent]

            # Process directory
            summary = self._process_directory_top_down(directory, parent_summary)
            results[directory] = summary

            # Yield progress update after each directory is processed
            yield TaskResult(
                result=results,
                progress=index + 1,
                progress_max=total_dirs,
            )

        # Final result with complete progress
        yield TaskResult(
            result=results,
            progress=total_dirs,
            progress_max=total_dirs,
        )


__all__ = ["DirectoryProcessor"]
