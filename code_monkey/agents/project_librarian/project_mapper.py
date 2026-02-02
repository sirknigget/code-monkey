"""Project Mapper for the Project Librarian agent.

Provides efficient incremental updates to project context by only reprocessing
modified files. Uses hash-based change detection and LLM summarization.

Classes:
- ProjectMapper: Main orchestrator for project mapping
- ProjectMapperResult: Result type containing module summaries and progress info
"""

from pathlib import Path
from typing import Any, Generator

from langchain_core.language_models import BaseChatModel

from code_monkey.agents.project_librarian.cache_manager import CacheManager
from code_monkey.agents.project_librarian.directory_processor import (
    DirectoryProcessor,
)
from code_monkey.agents.project_librarian.summarizer import Summarizer
from code_monkey.agents.project_librarian.utils import (
    compute_file_hash,
    discover_python_files,
)
from code_monkey.utils.task_result import TaskResult


class ProjectMapperResult:
    """Result container for ProjectMapper operations.

    Attributes:
        module_summaries: Dictionary mapping directory paths to their summaries.
        progress: Current progress value (0-based).
        progress_max: Maximum progress value for percentage calculation.
    """

    def __init__(
        self,
        module_summaries: dict[Path, str],
        progress: int = 0,
        progress_max: int = 1,
    ) -> None:
        """Initialize result container.

        Args:
            module_summaries: Dictionary mapping directory paths to their summaries.
            progress: Current progress value.
            progress_max: Maximum progress value.
        """
        self.module_summaries = module_summaries
        self.progress = progress
        self.progress_max = progress_max

    @property
    def progress_percent(self) -> float:
        """Return progress as a percentage of max."""
        if self.progress_max == 0:
            return 0.0
        return (self.progress / self.progress_max) * 100

    def __iter__(self):
        """Allow unpacking as (module_summaries, progress, progress_max)."""
        return iter((self.module_summaries, self.progress, self.progress_max))

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"ProjectMapperResult("
            f"modules={len(self.module_summaries)}, "
            f"progress={self.progress}/{self.progress_max} "
            f"({self.progress_percent:.1f}%)"
            f")"
        )


class ProjectMapper:
    """Main orchestrator for project mapping.

    Provides efficient incremental updates to project context by:
    1. Using hash-based change detection
    2. Only reprocessing modified files
    3. Generating hierarchical module summaries
    4. Producing project-wide context

    Usage:
        mapper = ProjectMapper(root=Path("."), llm=llm)
        for result in mapper.scan():  # Generator of TaskResult
            print(f"Progress: {result.progress_percent:.1f}%")
        summaries = result.result.module_summaries  # Final result
        context = mapper.get_project_context()  # Get cached/generated context
    """

    def __init__(
        self,
        root: Path,
        llm: BaseChatModel,
        cache_dir: Path | None = None,
    ) -> None:
        """Initialize project mapper.

        Args:
            root: Project root directory.
            llm: LangChain BaseChatModel instance.
            cache_dir: Optional custom cache directory (defaults to root/.codemonkey).
        """
        self.root = root
        self.llm = llm

        # Initialize cache manager
        if cache_dir is None:
            cache_dir = root / ".codemonkey"
        self._cache = CacheManager(root)

        # Initialize summarizer
        self._summarizer = Summarizer(llm)

        # Initialize directory processor
        self._processor = DirectoryProcessor(root, self._cache, self._summarizer)

        # Cache for project context
        self._project_context: str | None = None

    def _compute_file_hashes(self) -> dict[str, str]:
        """Compute hashes for all Python files.

        Returns:
            Dictionary mapping file paths to hashes.
        """
        files = discover_python_files(self.root)
        return {str(f): compute_file_hash(f) for f in files}

    def _run(
        self, changed_dirs: set[Path] | None = None
    ) -> Generator[TaskResult[ProjectMapperResult], Any, None]:
        """Internal method for scanning/updating.

        Args:
            changed_dirs: If provided, only process these directories.
                         If None, compute changed files via hash comparison.

        Yields:
            TaskResult containing ProjectMapperResult with progress tracking.
        """
        # Progress points: 1 (initial scan) + N (directory processing) + 1 (project context)
        # For the initial scan phase, we use progress_max = 1 (just the scan operation)
        yield TaskResult(
            result=ProjectMapperResult(module_summaries={}, progress=0, progress_max=1),
            progress=0,
            progress_max=1,
        )

        # Load cached hashes
        cached_hashes = self._cache.load_hashes()

        if changed_dirs is None:
            # Full scan: compute all hashes and find changed files
            current_hashes = self._compute_file_hashes()

            # Find files that have changed or are new
            changed_files: set[Path] = set()
            for filepath, current_hash in current_hashes.items():
                abs_path = Path(filepath)
                cached_hash = cached_hashes.get(filepath)
                if cached_hash != current_hash:
                    changed_files.add(abs_path)

            # Also detect deleted files (in cache but not in current)
            for filepath in cached_hashes:
                if filepath not in current_hashes:
                    abs_path = Path(filepath)
                    changed_files.add(abs_path)

            # Derive changed directories from changed files
            changed_dirs = set()
            for f in changed_files:
                dir_path = f.parent
                while dir_path >= self.root:
                    changed_dirs.add(dir_path)
                    dir_path = dir_path.parent

            # Save new hashes
            self._cache.save_hashes(current_hashes)

        # Calculate total progress: 1 (scan) + N (dirs) + 1 (project context)
        num_dirs = len(changed_dirs)
        total_progress_max = num_dirs + 2  # +1 for scan, +1 for project context

        # Mark initial scan complete (1 point used)
        yield TaskResult(
            result=ProjectMapperResult(module_summaries={}, progress=1, progress_max=total_progress_max),
            progress=1,
            progress_max=total_progress_max,
        )

        # Process changed directories (generator of TaskResult)
        task_results = self._processor.process_changed_directories(changed_dirs)

        # Consume generator and get final result
        # Directory progress starts at 1 (after initial scan)
        module_summaries: dict[Path, str] = {}
        for task_result in task_results:
            # Map directory processor progress to our total progress
            # Directory progress: 0 to N, we map to: 1 to N+1
            dir_progress = task_result.progress
            if dir_progress > 0:
                mapped_progress = dir_progress  # dir_progress already 1-indexed
            else:
                mapped_progress = 1

            yield TaskResult(
                result=ProjectMapperResult(
                    module_summaries=task_result.result,
                    progress=mapped_progress,
                    progress_max=total_progress_max,
                ),
                progress=mapped_progress,
                progress_max=total_progress_max,
            )
            module_summaries = task_result.result

        # Generate project context (final 1 point)
        project_context = self._summarizer.generate_project_context(
            module_summaries, project_name=self.root.name
        )
        self._cache.save_project_context(project_context)
        self._project_context = project_context

        # Final result with complete progress
        final_result = ProjectMapperResult(
            module_summaries=module_summaries,
            progress=total_progress_max,
            progress_max=total_progress_max,
        )
        yield TaskResult(
            result=final_result,
            progress=total_progress_max,
            progress_max=total_progress_max,
        )

    def scan(self) -> Generator[TaskResult[ProjectMapperResult], Any, None]:
        """Perform a full project scan.

        Yields:
            TaskResult containing ProjectMapperResult with progress tracking.
            Final result contains module_summaries dictionary.
        """
        yield from self._run(changed_dirs=None)

    def update(
        self, paths: list[Path]
    ) -> Generator[TaskResult[ProjectMapperResult], Any, None]:
        """Update specific paths and their parent directories.

        Args:
            paths: List of file or directory paths to update.

        Yields:
            TaskResult containing ProjectMapperResult with progress tracking.
            Final result contains module_summaries dictionary.
        """
        # Compute changed directories from paths
        changed_dirs: set[Path] = set()
        for path in paths:
            abs_path = self.root / path if not path.is_absolute() else path
            if abs_path.is_dir():
                changed_dirs.add(abs_path)
            else:
                # It's a file, add its parent directory
                if abs_path.parent >= self.root:
                    changed_dirs.add(abs_path.parent)

        yield from self._run(changed_dirs=changed_dirs)

    def get_project_context(self) -> str:
        """Get project context.

        Returns:
            Project context string in indentation tree format.
        """
        if self._project_context is not None:
            return self._project_context

        # Try to load from cache
        cached = self._cache.load_project_context()
        if cached is not None:
            self._project_context = cached
            return cached

        # If no cached context, run a scan
        self.scan()
        return self._project_context or ""


__all__ = ["ProjectMapper", "ProjectMapperResult"]
