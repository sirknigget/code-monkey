"""Cache Manager for atomic cache reads/writes.

Cache structure:
- .codemonkey/file_hashes.json      - {"/absolute/path": "hash", ...}
- .codemonkey/code_context.json     - hierarchical code context
- .codemonkey/project_context.json  - project-wide context
"""

from __future__ import annotations

import json
import logging
import tempfile
from dataclasses import asdict
from pathlib import Path

from code_monkey.agents.project_librarian.types import FileContext, ModuleContext

logger = logging.getLogger(__name__)

# =========================
# Context models
# =========================


def module_context_from_dict(data: dict) -> ModuleContext:
    """Recursively load ModuleContext from a dict."""
    return ModuleContext(
        summary=data["summary"],
        files={
            name: FileContext(**file_data)
            for name, file_data in data.get("files", {}).items()
        },
        submodules={
            name: module_context_from_dict(sub_data)
            for name, sub_data in data.get("submodules", {}).items()
        },
    )


# =========================
# Cache manager
# =========================


class CacheManager:
    """Manages atomic cache reads/writes for project mapping data."""

    HASHES_FILENAME = "file_hashes.json"
    CODE_CONTEXT_FILENAME = "code_context.json"
    PROJECT_CONTEXT_FILENAME = "project_context.md"
    CACHE_DIRNAME = ".codemonkey"

    def __init__(self, root: Path) -> None:
        self.root = root
        self.cache_dir = root / self.CACHE_DIRNAME

    # -------- internals --------

    def _ensure_cache_dir(self) -> None:
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _atomic_json_write(self, path: Path, data: object) -> None:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", dir=self.cache_dir, delete=False
        ) as tmp:
            json.dump(data, tmp, indent=2)
            tmp_path = Path(tmp.name)
        tmp_path.replace(path)

    # -------- file hashes --------

    def load_hashes(self) -> dict[str, str]:
        hashes_file = self.cache_dir / self.HASHES_FILENAME
        if not hashes_file.exists():
            return {}

        try:
            with open(hashes_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            raise Exception("Failed to read file hashes cache file.")

    def save_hashes(self, hashes: dict[str, str]) -> None:
        self._ensure_cache_dir()
        try:
            self._atomic_json_write(
                self.cache_dir / self.HASHES_FILENAME,
                hashes,
            )
        except OSError:
            raise Exception("Failed to write file hashes cache file.")

    # -------- code context --------

    def save_code_context(self, ctx: ModuleContext) -> None:
        """Atomically save code context to cache."""
        self._ensure_cache_dir()
        self._atomic_json_write(
            self.cache_dir / self.CODE_CONTEXT_FILENAME,
            asdict(ctx),
        )

    def load_code_context(self) -> ModuleContext | None:
        context_file = self.cache_dir / self.CODE_CONTEXT_FILENAME
        if not context_file.exists():
            return None

        try:
            with open(context_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            return module_context_from_dict(data)
        except (json.JSONDecodeError, OSError, KeyError) as e:
            logger.warning("Code context cache unreadable, will re-summarize: %s", e)
            return None

    # -------- project context --------

    def save_project_context(self, context: str) -> None:
        self._ensure_cache_dir()
        context_file = self.cache_dir / self.PROJECT_CONTEXT_FILENAME
        try:
            with open(context_file, "w", encoding="utf-8") as f:
                f.write(context)
        except OSError:
            raise Exception("Failed to write project context cache file.")

    def load_project_context(self) -> str | None:
        context_file = self.cache_dir / self.PROJECT_CONTEXT_FILENAME
        if not context_file.exists():
            return None

        try:
            with open(context_file, "r", encoding="utf-8") as f:
                return f.read()
        except OSError:
            raise Exception("Failed to read project context cache file.")
