"""Cache Manager for atomic cache reads/writes.

Cache structure:
- .codemonkey/file_hashes.json - {"/absolute/path": "hash", ...}
- .codemonkey/code_context.json - hierarchical code context
- .codemonkey/project_context.json - project-wide context
"""

import json
import tempfile
from pathlib import Path
from typing import NamedTuple


class FileContext(NamedTuple):
    """A file in the code hierarchy."""

    summary: str


class ModuleContext(NamedTuple):
    """A module in the code hierarchy."""

    summary: str
    files: dict[str, FileContext]
    submodules: dict[str, "ModuleContext"]


class CodeContext(NamedTuple):
    """Root code context containing the modules hierarchy."""

    root_summary: str
    modules: dict[str, ModuleContext]


class CacheManager:
    """Manages atomic cache reads/writes for project mapping data."""

    HASHES_FILENAME = "file_hashes.json"
    CODE_CONTEXT_FILENAME = "code_context.json"
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
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", dir=self.cache_dir, delete=False
        ) as tmp:
            json.dump(hashes, tmp, indent=2)
            tmp_path = tmp.name
        Path(tmp_path).rename(hashes_file)

    def _context_to_dict(self, ctx: CodeContext) -> dict:
        """Convert CodeContext to serializable dict."""
        def module_to_dict(module: ModuleContext) -> dict:
            return {
                "summary": module.summary,
                "files": {
                    name: {"summary": f.summary}
                    for name, f in module.files.items()
                },
                "submodules": {
                    name: module_to_dict(sub)
                    for name, sub in module.submodules.items()
                }
            }
        return {
            "root_summary": ctx.root_summary,
            "modules": {
                name: module_to_dict(m) for name, m in ctx.modules.items()
            }
        }

    def _dict_to_context(self, data: dict) -> CodeContext:
        """Convert dict to CodeContext."""
        def dict_to_module(data: dict) -> ModuleContext:
            files = {}
            for name, file_data in data.get("files", {}).items():
                files[name] = FileContext(summary=file_data["summary"])
            submodules = {}
            for name, sub_data in data.get("submodules", {}).items():
                submodules[name] = dict_to_module(sub_data)
            return ModuleContext(
                summary=data["summary"],
                files=files,
                submodules=submodules
            )
        modules = {}
        for name, module_data in data.get("modules", {}).items():
            modules[name] = dict_to_module(module_data)
        return CodeContext(
            root_summary=data.get("root_summary", ""),
            modules=modules
        )

    def save_code_context(self, ctx: CodeContext) -> None:
        """Atomically save code context to cache.

        Args:
            ctx: CodeContext containing modules hierarchy.
        """
        self._ensure_cache_dir()
        context_file = self.cache_dir / self.CODE_CONTEXT_FILENAME
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", dir=self.cache_dir, delete=False
        ) as tmp:
            json.dump(self._context_to_dict(ctx), tmp, indent=2)
            tmp_path = tmp.name
        Path(tmp_path).rename(context_file)

    def load_code_context(self) -> CodeContext | None:
        """Load code context from cache.

        Returns:
            CodeContext or None if not cached.
        """
        context_file = self.cache_dir / self.CODE_CONTEXT_FILENAME
        if not context_file.exists():
            return None
        try:
            with open(context_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            return self._dict_to_context(data)
        except (json.JSONDecodeError, OSError, KeyError):
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


__all__ = ["CacheManager", "CodeContext", "ModuleContext", "FileContext"]
