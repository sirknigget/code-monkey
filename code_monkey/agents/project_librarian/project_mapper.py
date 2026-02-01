"""Project Mapper for the Project Librarian agent.

Provides efficient incremental updates to project context by only reprocessing
modified files. Uses hash-based change detection and LLM summarization.

Classes:
- ProjectMapper: Main orchestrator for project mapping
- CacheManager: Handles atomic cache reads/writes
- Summarizer: LLM-based file and module summarization
- DirectoryProcessor: Top-down directory traversal with parallel processing
"""

import json
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import NamedTuple

from langchain_core.language_models import BaseChatModel
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableSequence

from code_monkey.agents.project_librarian.utilities import (
    compute_file_hash,
    discover_python_files,
    parse_python_code,
)


# =============================================================================
# Pydantic Models (for type safety and serialization)
# =============================================================================


class FileSummary(NamedTuple):
    """Summary of a single Python file.

    Attributes:
        filepath: Absolute path to the file.
        summary: LLM-generated summary of the file's purpose and contents.
    """

    filepath: Path
    summary: str


class ModuleSummary(NamedTuple):
    """Summary of a Python module (directory).

    Attributes:
        directory: Absolute path to the module directory.
        files: List of file summaries in this module.
        module_summary: LLM-generated summary of the module.
        parent_summary: Summary from parent module context (if any).
    """

    directory: Path
    files: list[FileSummary]
    module_summary: str
    parent_summary: str | None = None


# =============================================================================
# Cache Manager - Atomic cache operations
# =============================================================================


class CacheManager:
    """Manages atomic cache reads/writes for project mapping data.

    Cache structure:
    - .codemonkey/file_hashes.json - {"/absolute/path": "hash", ...}
    - .codemonkey/code_context/{rel_path}.md - per-file summaries
    - .codemonkey/project_context.json - project-wide context
    """

    HASHES_FILENAME = "file_hashes.json"
    CODE_CONTEXT_DIR = "code_context"
    PROJECT_CONTEXT_FILENAME = "project_context.json"

    def __init__(self, root: Path) -> None:
        """Initialize cache manager for the given root directory.

        Args:
            root: The project root directory.
        """
        self.root = root
        self.cache_dir = root / ".codemonkey"

    def _ensure_cache_dir(self) -> None:
        """Ensure the cache directory exists."""
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def load_hashes(self) -> dict[str, str]:
        """Load cached file hashes from disk.

        Returns:
            Dictionary mapping file paths to their hashes.
            Returns empty dict if cache file is missing.
        """
        hashes_file = self.cache_dir / self.HASHES_FILENAME
        if not hashes_file.exists():
            return {}
        try:
            with open(hashes_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}

    def save_hashes(self, hashes: dict[str, str]) -> None:
        """Atomically save file hashes to cache.

        Uses temp file + rename for atomicity.

        Args:
            hashes: Dictionary mapping file paths to their hashes.
        """
        self._ensure_cache_dir()
        hashes_file = self.cache_dir / self.HASHES_FILENAME
        # Write to temp file first, then rename for atomicity
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", dir=self.cache_dir, delete=False
        ) as tmp:
            json.dump(hashes, tmp, indent=2)
            tmp_path = tmp.name
        # Atomic rename
        Path(tmp_path).rename(hashes_file)

    def _get_cache_path(self, relative_path: Path) -> Path:
        """Get cache path for a file or directory.

        Args:
            relative_path: Relative path from project root.

        Returns:
            Cache path within .codemonkey directory.
        """
        return self.cache_dir / relative_path.as_posix().lstrip("/")

    def get_file_summary_path(self, filepath: Path) -> Path:
        """Get cache path for a file summary.

        Args:
            filepath: Absolute path to the file.

        Returns:
            Path to the .md summary file.
        """
        rel_path = filepath.relative_to(self.root)
        return self._get_cache_path(rel_path).with_suffix(".md")

    def save_file_summary(self, filepath: Path, summary: str) -> None:
        """Atomically save a file summary.

        Args:
            filepath: Absolute path to the source file.
            summary: LLM-generated summary string.
        """
        self._ensure_cache_dir()
        cache_path = self.get_file_summary_path(filepath)
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", dir=cache_path.parent, delete=False
        ) as tmp:
            tmp.write(summary)
            tmp_path = tmp.name
        Path(tmp_path).rename(cache_path)

    def load_file_summary(self, filepath: Path) -> str | None:
        """Load a file summary from cache.

        Args:
            filepath: Absolute path to the source file.

        Returns:
            Summary string or None if not cached.
        """
        cache_path = self.get_file_summary_path(filepath)
        if not cache_path.exists():
            return None
        try:
            return cache_path.read_text(encoding="utf-8")
        except OSError:
            return None

    def get_module_summary_path(self, directory: Path) -> Path:
        """Get cache path for a module summary.

        Args:
            directory: Absolute path to the module directory.

        Returns:
            Path to the _module.md summary file.
        """
        rel_path = directory.relative_to(self.root)
        cache_path = self._get_cache_path(rel_path)
        return cache_path / "_module.md"

    def save_module_summary(self, directory: Path, summary: str) -> None:
        """Atomically save a module summary.

        Args:
            directory: Absolute path to the module directory.
            summary: LLM-generated summary string.
        """
        self._ensure_cache_dir()
        cache_path = self.get_module_summary_path(directory)
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", dir=cache_path.parent, delete=False
        ) as tmp:
            tmp.write(summary)
            tmp_path = tmp.name
        Path(tmp_path).rename(cache_path)

    def load_module_summary(self, directory: Path) -> str | None:
        """Load a module summary from cache.

        Args:
            directory: Absolute path to the module directory.

        Returns:
            Summary string or None if not cached.
        """
        cache_path = self.get_module_summary_path(directory)
        if not cache_path.exists():
            return None
        try:
            return cache_path.read_text(encoding="utf-8")
        except OSError:
            return None

    def save_project_context(self, context: str) -> None:
        """Save project-wide context to cache.

        Args:
            context: Indentation tree format context string.
        """
        self._ensure_cache_dir()
        context_file = self.cache_dir / self.PROJECT_CONTEXT_FILENAME
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", dir=self.cache_dir, delete=False
        ) as tmp:
            json.dump({"context": context}, tmp, indent=2)
            tmp_path = tmp.name
        Path(tmp_path).rename(context_file)

    def load_project_context(self) -> str | None:
        """Load project-wide context from cache.

        Returns:
            Context string or None if not cached.
        """
        context_file = self.cache_dir / self.PROJECT_CONTEXT_FILENAME
        if not context_file.exists():
            return None
        try:
            with open(context_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("context")
        except (json.JSONDecodeError, OSError, KeyError):
            return None


# =============================================================================
# Summarizer - LLM-based summarization with retry logic
# =============================================================================


class Summarizer:
    """LLM-based file, module, and project summarization with retry logic.

    Uses three distinct prompt templates for different summarization levels.
    Implements exponential backoff retry for LLM failures.
    """

    MAX_SUMMARY_LINES = 10
    MAX_RETRIES = 3
    BACKOFF_BASE = 2.0
    INITIAL_DELAY = 1.0

    def __init__(self, llm: BaseChatModel) -> None:
        """Initialize summarizer with LLM.

        Args:
            llm: LangChain BaseChatModel instance.
        """
        self.llm = llm
        self._file_chain = self._create_file_summary_chain()
        self._module_chain = self._create_module_summary_chain()
        self._project_chain = self._create_project_summary_chain()

    def _create_file_summary_chain(self) -> RunnableSequence:
        """Create LangChain chain for file summaries.

        Returns:
            RunnableSequence for file summarization.
        """
        template = """You are a code analyst. Summarize this Python file concisely.

File: {filepath}
Structure:
{structure}

Parent module context (if any):
{parent_context}

Requirements:
- 2-3 sentences maximum
- State the file's primary purpose
- Mention key classes and functions
- Use active voice
- Keep under {max_lines} lines

Summary:"""
        prompt = ChatPromptTemplate.from_template(template)
        return prompt | self.llm | StrOutputParser()

    def _create_module_summary_chain(self) -> RunnableSequence:
        """Create LangChain chain for module summaries.

        Returns:
            RunnableSequence for module summarization.
        """
        template = """You are a code analyst. Summarize this Python module (directory).

Module: {module_path}

File summaries:
{file_summaries}

Parent module context (if any):
{parent_context}

Requirements:
- 3-5 sentences maximum
- Describe the module's purpose and what it provides
- Explain relationships between files
- Mention key exports/APIs
- Keep under {max_lines} lines

Summary:"""
        prompt = ChatPromptTemplate.from_template(template)
        return prompt | self.llm | StrOutputParser()

    def _create_project_summary_chain(self) -> RunnableSequence:
        """Create LangChain chain for project context.

        Returns:
            RunnableSequence for project context generation.
        """
        template = """You are a code analyst. Create a project structure overview.

Module summaries by directory:
{module_summaries}

Requirements:
- Use indentation tree format to show directory hierarchy
- Show module purpose at each level
- Maximum 10 lines total
- Focus on key modules and their responsibilities

Project Structure:
```
{project_name}/
{indented_summary}
```"""
        prompt = ChatPromptTemplate.from_template(template)
        return prompt | self.llm | StrOutputParser()

    def _summarize_with_retry(
        self, chain: RunnableSequence, input: dict, max_lines: int
    ) -> str:
        """Execute summarization with exponential backoff retry.

        Args:
            chain: LangChain chain to execute.
            input: Dictionary of template variables.
            max_lines: Maximum allowed lines in output.

        Returns:
            Summary string (truncated to max_lines if needed).

        Raises:
            RuntimeError: After all retries are exhausted.
        """
        last_error: Exception | None = None
        delay = self.INITIAL_DELAY

        for attempt in range(self.MAX_RETRIES):
            try:
                result = chain.invoke(input).strip()
                # Truncate to max_lines
                lines = result.split("\n")
                if len(lines) > max_lines:
                    result = "\n".join(lines[:max_lines])
                return result
            except Exception as e:
                last_error = e
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(delay)
                    delay *= self.BACKOFF_BASE

        raise RuntimeError(
            f"Summarization failed after {self.MAX_RETRIES} attempts: {last_error}"
        )

    def summarize_file(
        self,
        filepath: Path,
        structure: str,
        parent_context: str | None = None,
    ) -> str:
        """Generate summary for a single file.

        Args:
            filepath: Path to the file.
            structure: Parsed code structure string.
            parent_context: Optional parent module context.

        Returns:
            File summary string.
        """
        input_vars = {
            "filepath": str(filepath),
            "structure": structure,
            "parent_context": parent_context or "(none)",
            "max_lines": self.MAX_SUMMARY_LINES,
        }
        return self._summarize_with_retry(
            self._file_chain, input_vars, self.MAX_SUMMARY_LINES
        )

    def summarize_module(
        self,
        directory: Path,
        file_summaries: list[str],
        parent_context: str | None = None,
    ) -> str:
        """Generate summary for a module (directory).

        Args:
            directory: Path to the module directory.
            file_summaries: List of file summary strings.
            parent_context: Optional parent module context.

        Returns:
            Module summary string.
        """
        combined_summaries = "\n---\n".join(file_summaries)
        input_vars = {
            "module_path": str(directory),
            "file_summaries": combined_summaries,
            "parent_context": parent_context or "(none)",
            "max_lines": self.MAX_SUMMARY_LINES,
        }
        return self._summarize_with_retry(
            self._module_chain, input_vars, self.MAX_SUMMARY_LINES
        )

    def generate_project_context(
        self, module_summaries: dict[Path, str], project_name: str = "project"
    ) -> str:
        """Generate project-wide context using indentation tree format.

        Args:
            module_summaries: Dictionary mapping directory paths to summaries.
            project_name: Name of the project for display.

        Returns:
            Project context string in indentation tree format.
        """
        # Format module summaries for the template
        summary_parts = []
        for dir_path, summary in sorted(module_summaries.items()):
            rel_path = dir_path.relative_to(dir_path.root)
            summary_parts.append(f"{rel_path}: {summary}")

        combined = "\n".join(summary_parts)

        input_vars = {
            "module_summaries": combined,
            "project_name": project_name,
            "indented_summary": combined,  # Will be indented by template
        }
        return self._summarize_with_retry(
            self._project_chain, input_vars, self.MAX_SUMMARY_LINES
        )


# =============================================================================
# Directory Processor - Top-down traversal with parallel file processing
# =============================================================================


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
    ) -> dict[Path, str]:
        """Process only specified directories and their children.

        Args:
            changed_dirs: Set of directories that have changed.

        Returns:
            Dictionary mapping directory paths to their summaries.
        """
        results: dict[Path, str] = {}

        # Sort by path depth to process parent directories first
        sorted_dirs = sorted(changed_dirs, key=lambda p: len(p.parts))

        for directory in sorted_dirs:
            if directory in results:
                continue  # Already processed as child

            # Get parent summary if available
            parent_summary = None
            parent = directory.parent
            if parent >= self.root and parent in results:
                parent_summary = results[parent]

            # Process directory
            summary = self._process_directory_top_down(directory, parent_summary)
            results[directory] = summary

        return results


# =============================================================================
# Project Mapper - Main orchestrator
# =============================================================================


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


__all__ = ["ProjectMapper", "FileSummary", "ModuleSummary"]
