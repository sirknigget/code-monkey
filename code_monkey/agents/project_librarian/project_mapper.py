"""ProjectMapper: builds and incrementally updates the module context tree."""

from __future__ import annotations

import copy
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


class ProjectMapper:
    """Builds an incremental module context tree for a project.

    Uses cached context from a previous run when available, only re-summarizing
    files and modules that have changed since the last run.
    """

    def __init__(self, working_dir: Path, summarizer: Summarizer) -> None:
        self.working_dir = working_dir
        self.summarizer = summarizer

    def map_project(self) -> None:
        """Build (or incrementally update) the full project context and persist it.

        Summarizes changed files and modules bottom-up, then builds a project-level
        structure string and summary, and saves all outputs to the cache.  File
        hashes are saved last so that a partial write never leaves the cache in an
        inconsistent state.
        """
        hashes = ProjectFileHashes(self.working_dir).load()
        cache = CacheManager(self.working_dir)
        cached_context = cache.load_code_context()

        context = self._build_revised_context(hashes.modified_only, cached_context)
        self._summarize_bottom_up(context, self.working_dir)

        project_structure = ProjectStructure(self.working_dir).build()
        project_summary = self.summarizer.summarize_project(
            project_structure=project_structure,
            code_context=context,
            project_name=self.working_dir.name,
        )

        cache.save_code_context(context)
        cache.save_project_context(project_summary)
        cache.save_hashes(hashes.current)

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

        return root

    def _summarize_bottom_up(
        self, module: ModuleContext, current_dir: Path
    ) -> list[Summarizer.FileInfo]:
        """Recursively summarize module tree bottom-up.

        Returns:
            List of FileInfo for all files directly in this module (used by
            parent for module summarization).
        """
        # 1. Recurse into submodules first (bottom-up)
        submodule_infos: list[Summarizer.FileInfo] = []
        for submodule_name, submodule in module.submodules.items():
            sub_dir = current_dir / submodule_name
            self._summarize_bottom_up(submodule, sub_dir)
            submodule_infos.append(
                Summarizer.FileInfo(filepath=sub_dir, summary=submodule.summary)
            )

        # 2. Summarize files that need it
        file_infos: list[Summarizer.FileInfo] = []
        for filename, file_ctx in module.files.items():
            filepath = current_dir / filename
            if file_ctx.summary is None:
                try:
                    code = filepath.read_text(encoding="utf-8")
                except OSError:
                    continue
                file_ctx.summary = self.summarizer.summarize_file(filepath, code)
            file_infos.append(
                Summarizer.FileInfo(filepath=filepath, summary=file_ctx.summary)
            )

        # 3. Summarize module itself if invalidated
        if module.summary is None:
            module.summary = self.summarizer.summarize_module(
                current_dir, file_infos, submodule_infos
            )

        return file_infos
