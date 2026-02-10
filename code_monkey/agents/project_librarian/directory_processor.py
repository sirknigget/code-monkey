"""Directory processor for top-down traversal with ModuleContext structure.

Processes directories to build a hierarchical ModuleContext with
FileContext NamedTuples (root ModuleContext uses summary as root_summary).
"""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Generator

from code_monkey.agents.project_librarian.cache_manager import (
    CacheManager,
)
from code_monkey.agents.project_librarian.summarizer import Summarizer
from code_monkey.agents.project_librarian.types import FileContext, ModuleContext
from code_monkey.agents.project_librarian.utils.code_parser import parse_python_code
from code_monkey.agents.project_librarian.utils.file_discovery import (
    discover_python_files,
)
from code_monkey.utils.task_result import TaskResult


class DirectoryProcessor:
    """Processes directories to build ModuleContext hierarchy.

    Provides top-down traversal with parallel file processing,
    building ModuleContext and FileContext structures.
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

    def _summarize_single_file(
        self, filepath: Path, parent_context: str | None = None
    ) -> FileContext:
        """Summarize a single file and return FileContext.

        Args:
            filepath: Path to the Python file.
            parent_context: Optional parent module context.

        Returns:
            FileContext with filepath and summary.
        """
        # Try to load from cache
        cached = self.cache.load_file_summary(filepath)
        if cached is not None:
            return FileContext(summary=cached)

        # Parse and summarize
        source = filepath.read_text(encoding="utf-8")
        parsed = parse_python_code(source)
        structure = parsed.llm_friendly_string(include_imports=True)
        summary = self.summarizer.summarize_file(
            filepath, structure, parent_context
        )

        # Save to cache
        self.cache.save_file_summary(filepath, summary)

        return FileContext(summary=summary)

    def _process_directory(
        self,
        directory: Path,
        parent_context: str | None = None,
    ) -> tuple[ModuleContext, str]:
        """Process a directory and return ModuleContext.

        Args:
            directory: Directory to process.
            parent_context: Summary from parent module context.

        Returns:
            Tuple of (ModuleContext, module_summary).
        """
        files = self._get_files_in_directory(directory)

        # Parallel file processing
        file_contexts: dict[str, FileContext] = {}
        with ThreadPoolExecutor() as executor:
            # Map files to their contexts
            for filename, fc in zip(
                [f.name for f in files],
                executor.map(self._summarize_single_file, files),
            ):
                file_contexts[filename] = fc

        # Extract summary strings for module summarization
        file_summary_strings = [fc.summary for fc in file_contexts.values()]

        # Generate module summary
        module_summary = self.summarizer.summarize_module(
            directory, file_summary_strings, parent_context
        )

        # Save module summary to cache
        self.cache.save_module_summary(directory, module_summary)

        # Process child directories
        submodule_contexts: dict[str, ModuleContext] = {}
        child_dirs = sorted(
            d for d in directory.iterdir()
            if d.is_dir() and d.name != ".codemonkey"
        )
        for child_dir in child_dirs:
            if any(child_dir.glob("*.py")):
                child_module, _ = self._process_directory(
                    child_dir, module_summary
                )
                submodule_contexts[child_dir.name] = child_module

        return (
            ModuleContext(
                summary=module_summary,
                files=file_contexts,
                submodules=submodule_contexts,
            ),
            module_summary,
        )

    def _build_module_path(self, directory: Path) -> tuple[str, ...]:
        """Build the module path tuple for a directory.

        Args:
            directory: Directory path relative to root.

        Returns:
            Tuple of module names from root to this directory.
        """
        parts = directory.relative_to(self.root).parts
        return tuple(parts) if parts else ()

    def process_directories(
        self, directories: set[Path]
    ) -> Generator[TaskResult[ModuleContext], None, None]:
        """Process specified directories and build ModuleContext.

        Args:
            directories: Set of directories to process.

        Yields:
            TaskResult containing ModuleContext with progress tracking.
        """
        # Sort by path depth to process parent directories first
        sorted_dirs = sorted(directories, key=lambda p: len(p.parts))
        total_dirs = len(sorted_dirs)

        # Build the context incrementally (root ModuleContext)
        code_context = ModuleContext(summary="", files={}, submodules={})

        for index, directory in enumerate(sorted_dirs):
            module_path = self._build_module_path(directory)

            # Get parent context if available
            parent_context: str | None = None
            if module_path:
                parent_parts = module_path[:-1]
                if parent_parts:
                    parent_path = self.root / "/".join(parent_parts)
                    parent_context = self.cache.load_module_summary(parent_path)

            # Process directory
            module, _ = self._process_directory(directory, parent_context)

            # Set module in context (creating parents as needed)
            code_context = self._set_module(code_context, module_path, module)

            yield TaskResult(
                result=code_context,
                progress=index + 1,
                progress_max=total_dirs,
            )

        # Final result
        yield TaskResult(
            result=code_context,
            progress=total_dirs,
            progress_max=total_dirs,
        )

    def _set_module(
        self,
        ctx: ModuleContext,
        module_path: tuple[str, ...],
        module: ModuleContext,
    ) -> ModuleContext:
        """Set a module in the context, creating parents as needed.

        Args:
            ctx: Current ModuleContext.
            module_path: Tuple of module names from root.
            module: ModuleContext to set.

        Returns:
            New ModuleContext with module set.
        """
        if not module_path:
            return ModuleContext(summary=module.summary, files={}, submodules=ctx.submodules)

        # Clone the submodules dict and create path
        new_submodules: dict[str, ModuleContext] = {}
        for name, mod in ctx.submodules.items():
            new_submodules[name] = ModuleContext(
                summary=mod.summary,
                files=dict(mod.files),
                submodules=dict(mod.submodules),
            )

        current = new_submodules
        for name in module_path[:-1]:
            if name not in current:
                current[name] = ModuleContext(
                    summary="",
                    files={},
                    submodules={},
                )
            parent = current[name]
            new_inner_submodules: dict[str, ModuleContext] = {}
            for subname, submod in parent.submodules.items():
                new_inner_submodules[subname] = ModuleContext(
                    summary=submod.summary,
                    files=dict(submod.files),
                    submodules=dict(submod.submodules),
                )
            current = new_inner_submodules

        # Set the final module
        final_name = module_path[-1]
        current[final_name] = module

        return ModuleContext(summary=ctx.summary, files={}, submodules=new_submodules)


__all__ = ["DirectoryProcessor"]
