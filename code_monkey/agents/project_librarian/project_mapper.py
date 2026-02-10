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


class ProjectMapper:
    """Builds an incremental module context tree for a project.

    Uses cached context from a previous run when available, only re-summarizing
    files and modules that have changed since the last run.
    """

    def __init__(self, working_dir: Path, summarizer: Summarizer) -> None:
        self.working_dir = working_dir
        self.summarizer = summarizer

    def map_modules(self) -> ModuleContext:
        """Build (or incrementally update) the module context tree.

        Returns:
            A fully-summarized ModuleContext tree rooted at working_dir.
        """
        modified_files = ProjectFileHashes(self.working_dir).load()
        cached_context = CacheManager(self.working_dir).load_code_context()

        context = self._build_revised_context(modified_files, cached_context)
        self._summarize_bottom_up(context, self.working_dir)
        return context

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

        for abs_path_str, hash_val in modified_files.items():
            abs_path = Path(abs_path_str)
            try:
                rel = abs_path.relative_to(self.working_dir)
            except ValueError:
                # File is outside working_dir — skip
                continue

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
            if submodule.summary is not None:
                submodule_infos.append(
                    Summarizer.FileInfo(filepath=sub_dir, summary=submodule.summary)
                )

        # 2. Summarize files that need it
        file_infos: list[Summarizer.FileInfo] = []
        for filename, file_ctx in module.files.items():
            filepath = current_dir / filename
            if file_ctx.summary is None:
                code = filepath.read_text(encoding="utf-8")
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
