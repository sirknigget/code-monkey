"""ProjectMapper: builds and incrementally updates the module context tree."""

from __future__ import annotations

import asyncio
import copy
import functools
from pathlib import Path

from code_monkey.agents.project_librarian.cache_manager import CacheManager
from code_monkey.agents.project_librarian.summarizer import Summarizer
from code_monkey.agents.project_librarian.types import FileContext, ModuleContext
from code_monkey.agents.project_librarian.utils.project_file_hashes import (
    ProjectFileHashes,
)
from code_monkey.agents.project_librarian.utils.project_structure import (
    ProjectStructure,
)
from code_monkey.utils.log_utils import get_formatted_logger

logger = get_formatted_logger(__name__)


class ProjectMapper:
    """Builds an incremental module context tree for a project.

    Uses cached context from a previous run when available, only re-summarizing
    files and modules that have changed since the last run.
    """

    def __init__(self, working_dir: Path, summarizer: Summarizer) -> None:
        self.working_dir = working_dir
        self.summarizer = summarizer
        self._cache = CacheManager(working_dir)

    def get_code_context(self):
        """Return the cached code context, or None if not yet available."""
        return self._cache.load_code_context()

    def get_project_context(self) -> str | None:
        """Return the cached project context summary, or None if not yet available."""
        return self._cache.load_project_context()

    async def map_project(self) -> None:
        """Build (or incrementally update) the full project context and persist it.

        Summarizes changed files and modules bottom-up, then builds a project-level
        structure string and summary, and saves all outputs to the cache.  File
        hashes are saved last so that a partial write never leaves the cache in an
        inconsistent state.
        """
        hashes = ProjectFileHashes(self.working_dir).load()
        cache = self._cache
        cached_context = cache.load_code_context()

        modified_count = len(hashes.modified_only)
        logger.debug(
            "ProjectMapper: %d file(s) changed in %s (cache=%s)",
            modified_count,
            self.working_dir,
            "hit" if cached_context is not None else "miss",
        )

        context = self._build_revised_context(hashes.modified_only, cached_context)
        await self._summarize_bottom_up(context, self.working_dir)

        project_structure = ProjectStructure(self.working_dir).build()
        project_summary = self.summarizer.summarize_project(
            project_structure=project_structure,
            code_context=context,
            project_name=self.working_dir.name,
        )

        cache.save_code_context(context)
        cache.save_project_context(project_summary)
        cache.save_hashes(hashes.current)
        logger.debug("ProjectMapper: cache saved successfully")

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _build_revised_context(
        self,
        modified_files: dict[str, str | None],
        cached_context: ModuleContext | None,
    ) -> ModuleContext:
        """Deep-copy cached context (or create fresh) and apply file changes."""
        if cached_context is not None:
            root = copy.deepcopy(cached_context)
        else:
            root = ModuleContext(summary=None)

        for rel_path_str, hash_val in modified_files.items():
            rel = Path(rel_path_str)
            parts = rel.parts  # e.g. ("pkg", "sub", "mod.py")
            if not parts:
                continue

            # Invalidate root summary whenever any file changes
            root.summary = None

            # Navigate / create intermediate ModuleContext nodes
            module = root
            for part in parts[:-1]:
                if part not in module.submodules:
                    module.submodules[part] = ModuleContext(summary=None)
                else:
                    module.submodules[part].summary = None
                module = module.submodules[part]

            filename = parts[-1]
            if hash_val is None:
                # Deleted file
                module.files.pop(filename, None)
            else:
                # Added or modified file
                module.files[filename] = FileContext(summary=None)

        self._prune_empty_submodules(root)
        return root

    def _prune_empty_submodules(self, module: ModuleContext) -> bool:
        """Prune empty submodules from a module tree.

        Returns:
            True if any submodule was pruned anywhere in this subtree.
        """
        changed = False

        for name, child in list(module.submodules.items()):
            child_changed = self._prune_empty_submodules(child)

            if not child.files and not child.submodules:
                module.submodules.pop(name)
                changed = True
                continue

            if child_changed:
                changed = True

        if changed:
            module.summary = None

        return changed

    async def _summarize_bottom_up(
        self, module: ModuleContext, current_dir: Path
    ) -> None:
        """Recursively summarize module tree bottom-up with parallelism.

        Submodules within a module and files within a module are summarized
        in parallel. A module's own summary is computed only after all its
        files and submodules have been summarized.
        """
        loop = asyncio.get_running_loop()
        submodule_items = list(module.submodules.items())

        async def _summarize_file(filename: str, file_ctx: FileContext) -> None:
            if file_ctx.summary is not None:
                return
            filepath = current_dir / filename
            try:
                code = await loop.run_in_executor(
                    None, functools.partial(filepath.read_text, encoding="utf-8")
                )
            except OSError as e:
                logger.warning(
                    "Cannot read %s, skipping file summarization: %s", filepath, e
                )
                return
            file_ctx.summary = await loop.run_in_executor(
                None, self.summarizer.summarize_file, filepath, code
            )

        # Recurse into submodules and summarize files in parallel.
        # A module's own summary depends on both, so it is computed after this gather.
        await asyncio.gather(
            *[
                self._summarize_bottom_up(submodule, current_dir / name)
                for name, submodule in submodule_items
            ],
            *[
                _summarize_file(filename, file_ctx)
                for filename, file_ctx in module.files.items()
            ],
        )

        submodule_infos = [
            Summarizer.FileInfo(filepath=current_dir / name, summary=submodule.summary)
            for name, submodule in submodule_items
            if submodule.summary is not None
        ]

        file_infos = [
            Summarizer.FileInfo(
                filepath=current_dir / filename, summary=file_ctx.summary
            )
            for filename, file_ctx in module.files.items()
            if file_ctx.summary is not None
        ]

        # 3. Summarize module itself if invalidated
        if module.summary is None:
            module.summary = await loop.run_in_executor(
                None,
                self.summarizer.summarize_module,
                current_dir,
                file_infos,
                submodule_infos,
            )
