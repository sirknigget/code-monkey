"""Project Mapper for the Project Librarian agent.

Provides efficient incremental updates to project context by only reprocessing
modified files. Uses hash-based change detection and LLM summarization.

Classes:
- ProjectMapper: Main orchestrator for project mapping
"""

from pathlib import Path

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


class ProjectMapper:
    """Main orchestrator for project mapping.

    Provides efficient incremental updates to project context by:
    1. Using hash-based change detection
    2. Only reprocessing modified files
    3. Generating hierarchical module summaries
    4. Producing project-wide context

    Usage:
        mapper = ProjectMapper(root=Path("."), llm=llm)
        summaries = mapper.scan()  # Full scan
        summaries = mapper.update([Path("src/new_file.py")])  # Incremental
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
    ) -> dict[Path, str]:
        """Internal method for scanning/updating.

        Args:
            changed_dirs: If provided, only process these directories.
                         If None, compute changed files via hash comparison.

        Returns:
            Dictionary mapping directory paths to module summaries.
        """
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

        # Process changed directories
        module_summaries = self._processor.process_changed_directories(changed_dirs)

        # Generate project context
        project_context = self._summarizer.generate_project_context(
            module_summaries, project_name=self.root.name
        )
        self._cache.save_project_context(project_context)
        self._project_context = project_context

        return module_summaries

    def scan(self) -> dict[Path, str]:
        """Perform a full project scan.

        Returns:
            Dictionary mapping directory paths to module summaries.
        """
        return self._run(changed_dirs=None)

    def update(self, paths: list[Path]) -> dict[Path, str]:
        """Update specific paths and their parent directories.

        Args:
            paths: List of file or directory paths to update.

        Returns:
            Dictionary mapping directory paths to module summaries.
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

        return self._run(changed_dirs=changed_dirs)

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


__all__ = ["ProjectMapper"]
