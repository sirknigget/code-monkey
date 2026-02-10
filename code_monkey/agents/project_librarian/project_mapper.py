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

from code_monkey.agents.project_librarian.cache_manager import (
    CacheManager,
    FileContext,
    ModuleContext,
)
from code_monkey.agents.project_librarian.summarizer import Summarizer
from code_monkey.agents.project_librarian.utils.file_discovery import discover_python_files
from code_monkey.agents.project_librarian.utils.hash_utils import compute_file_hash

from code_monkey.utils.task_result import TaskResult


class ProjectMapperResult:
    """Result container for ProjectMapper operations.

    Attributes:
        code_context: The full code context hierarchy.
        project_context: Project-wide context string.
    """

    def __init__(
        self,
        code_context: ModuleContext,
        project_context: str,
    ) -> None:
        """Initialize result container.

        Args:
            code_context: Hierarchical code context.
            project_context: Project-wide context string.
        """
        self.code_context = code_context
        self.project_context = project_context

    def __repr__(self) -> str:
        """String representation."""
        return f"ProjectMapperResult(modules={len(self.code_context.submodules)})"


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
        final = result.result  # Final ProjectMapperResult
        context = final.code_context  # Hierarchical context
        project_ctx = final.project_context  # Project-wide context
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

        # Cache for project context
        self._project_context: str | None = None

    def _compute_file_hashes(self) -> dict[str, str]:
        """Compute hashes for all Python files.

        Returns:
            Dictionary mapping file paths to hashes.
        """
        files = discover_python_files(self.root)
        return {str(f): compute_file_hash(f) for f in files}

    def _build_module_path(self, directory: Path) -> tuple[str, ...]:
        """Build the module path tuple for a directory.

        Args:
            directory: Directory path relative to root.

        Returns:
            Tuple of module names from root to this directory.
        """
        parts = directory.relative_to(self.root).parts
        return tuple(parts) if parts else ()

    def _get_module(
        self,
        ctx: ModuleContext,
        module_path: tuple[str, ...],
    ) -> ModuleContext | None:
        """Get a module from the context by path.

        Args:
            ctx: ModuleContext to search.
            module_path: Tuple of module names from root.

        Returns:
            ModuleContext or None if not found.
        """
        modules = ctx.submodules
        for name in module_path:
            if name not in modules:
                return None
            if name == module_path[-1]:
                return modules[name]
            modules = modules[name].submodules
        return None

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
            # Setting root summary on root ModuleContext
            return ModuleContext(
                summary=module.summary,
                files={},
                submodules=ctx.submodules
            )

        # Clone the submodules dict and create path
        new_submodules: dict[str, ModuleContext] = {}
        for name, mod in ctx.submodules.items():
            new_submodules[name] = ModuleContext(
                summary=mod.summary,
                files=dict(mod.files),
                submodules=dict(mod.submodules),
            )

        current = new_submodules
        for i, name in enumerate(module_path[:-1]):
            if name not in current:
                # Create missing parent
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

        return ModuleContext(
            summary=ctx.summary,
            files={},
            submodules=new_submodules
        )

    def _process_file(
        self,
        filepath: Path,
        existing_context: ModuleContext | None,
    ) -> FileContext:
        """Process a single file and return its context.

        Args:
            filepath: Path to the Python file.
            existing_context: Existing ModuleContext if available.

        Returns:
            FileContext with summary.
        """
        # Try to get existing summary from context
        if existing_context is not None:
            module_path = self._build_module_path(filepath.parent)
            module = self._get_module(existing_context, module_path)
            if module is not None:
                filename = filepath.name
                if filename in module.files:
                    return module.files[filename]

        # Generate new summary
        source = filepath.read_text(encoding="utf-8")
        from code_monkey.agents.project_librarian.utils.code_parser import parse_python_code
        parsed = parse_python_code(source)
        structure = parsed.llm_friendly_string(include_imports=True)
        summary = self._summarizer.summarize_file(filepath, structure, parent_context=None)
        return FileContext(summary=summary)

    def _process_directory(
        self,
        directory: Path,
        code_context: ModuleContext | None,
        changed_files: set[Path],
    ) -> tuple[ModuleContext, bool]:
        """Process a directory and return its module context.

        Args:
            directory: Directory to process.
            code_context: Existing ModuleContext if available.
            changed_files: Set of files that have changed.

        Returns:
            Tuple of (ModuleContext, was_modified).
        """
        module_path = self._build_module_path(directory)
        existing_module = None
        if code_context is not None:
            existing_module = self._get_module(code_context, module_path)

        # Get files in this directory
        files = sorted(directory.glob("*.py"))
        file_contexts: dict[str, FileContext] = {}
        any_changed = False

        for f in files:
            if f in changed_files:
                any_changed = True
            file_contexts[f.name] = self._process_file(f, code_context)
            changed_files.discard(f)

        # Get child directories
        child_dirs = sorted(
            d for d in directory.iterdir() if d.is_dir() and d.name != ".codemonkey"
        )

        # Process child directories
        submodule_contexts: dict[str, ModuleContext] = {}
        for child_dir in child_dirs:
            if any(child_dir.glob("*.py")):
                child_module, child_changed = self._process_directory(
                    child_dir, code_context, changed_files
                )
                submodule_contexts[child_dir.name] = child_module
                if child_changed:
                    any_changed = True

        # Determine if we need to regenerate module summary
        needs_summary_regen = any_changed
        if not needs_summary_regen and existing_module is not None:
            # Check if files structure changed
            if set(existing_module.files.keys()) != set(file_contexts.keys()):
                needs_summary_regen = True

        # Generate module summary
        if needs_summary_regen:
            file_summaries = [fc.summary for fc in file_contexts.values()]
            module_summary = self._summarizer.summarize_module(
                directory, file_summaries, parent_context=None
            )
        elif existing_module is not None:
            module_summary = existing_module.summary
        else:
            module_summary = ""

        return ModuleContext(
            summary=module_summary,
            files=file_contexts,
            submodules=submodule_contexts,
        ), needs_summary_regen

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
        # Load existing code context
        existing_context = self._cache.load_code_context()

        # Progress points: 1 (initial scan) + N (directory processing) + 1 (project context)
        yield TaskResult(
            result=ProjectMapperResult(
                code_context=ModuleContext(summary="", files={}, submodules={}),
                project_context="",
            ),
            progress=0,
            progress_max=1,
        )

        # Load cached hashes
        cached_hashes = self._cache.load_hashes()

        # Initialize changed_files for _process_directory calls
        changed_files: set[Path] = set()

        if changed_dirs is None:
            # Full scan: compute all hashes and find changed files
            current_hashes = self._compute_file_hashes()

            # Find files that have changed or are new
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

        # If no changes, return existing context
        if not changed_dirs:
            project_context = self._cache.load_project_context() or ""
            if existing_context is not None:
                yield TaskResult(
                    result=ProjectMapperResult(
                        code_context=existing_context,
                        project_context=project_context,
                    ),
                    progress=1,
                    progress_max=1,
                )
                return

        # Calculate total progress
        num_dirs = len(changed_dirs)
        total_progress_max = num_dirs + 2  # +1 for scan, +1 for project context

        # Mark initial scan complete
        yield TaskResult(
            result=ProjectMapperResult(
                code_context=ModuleContext(summary="", files={}, submodules={}),
                project_context="",
            ),
            progress=1,
            progress_max=total_progress_max,
        )

        # Process directories top-down
        # Sort by path depth to process parent directories first
        sorted_dirs = sorted(changed_dirs, key=lambda p: len(p.parts))
        all_module_contexts: dict[tuple[str, ...], ModuleContext] = {}

        # Copy existing context for modification
        if existing_context is None:
            current_context = ModuleContext(summary="", files={}, submodules={})
        else:
            current_context = existing_context

        for i, directory in enumerate(sorted_dirs):
            module_path = self._build_module_path(directory)
            module, _ = self._process_directory(
                directory, current_context, changed_files.copy()
            )
            all_module_contexts[module_path] = module
            current_context = self._set_module(current_context, module_path, module)

            yield TaskResult(
                result=ProjectMapperResult(
                    code_context=current_context,
                    project_context="",
                ),
                progress=i + 2,
                progress_max=total_progress_max,
            )

        # Update root summary if any changes
        if all_module_contexts:
            # Generate new root summary
            root_summary = self._summarizer.summarize_project(
                current_context, project_name=self.root.name
            )
            current_context = ModuleContext(
                summary=root_summary,
                files={},
                submodules=current_context.submodules,
            )

        # Save code context
        self._cache.save_code_context(current_context)

        # Generate project context (final 1 point)
        project_context = self._summarizer.generate_project_context(
            current_context, project_name=self.root.name
        )
        self._cache.save_project_context(project_context)
        self._project_context = project_context

        # Final result
        final_result = ProjectMapperResult(
            code_context=current_context,
            project_context=project_context,
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
            Final result contains code_context and project_context.
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
            Final result contains code_context and project_context.
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
        for _ in self.scan():
            pass
        return self._project_context or ""


__all__ = ["ProjectMapper", "ProjectMapperResult"]
