"""Cache Manager for atomic cache reads/writes."""

import json
import tempfile
from pathlib import Path


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


__all__ = ["CacheManager"]
