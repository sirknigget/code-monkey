"""Builds an LLM-friendly string representation of a project directory tree."""

from __future__ import annotations

import fnmatch
from pathlib import Path

from code_monkey.agents.project_librarian.utils.constants import IGNORED_DIRS

# Tree drawing characters
_BRANCH = "├── "
_LAST = "└── "
_PIPE = "│   "
_SPACE = "    "


class ProjectStructure:
    """Builds an LLM-friendly string representation of a project directory tree.

    Excludes entries matched by the predefined IGNORED_DIRS list and any
    patterns found in a .gitignore file at the project root.
    """

    def __init__(self, root: Path) -> None:
        self.root = root
        self._gitignore_patterns: list[str] = self._load_gitignore_patterns()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def build(self) -> str:
        """Build and return the LLM-friendly directory tree string.

        Returns:
            Multi-line string representing the project structure.
        """
        lines: list[str] = [f"{self.root.name}/"]
        lines.extend(self._build_tree(self.root, prefix=""))
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _load_gitignore_patterns(self) -> list[str]:
        """Load ignore patterns from .gitignore at the project root."""
        gitignore = self.root / ".gitignore"
        if not gitignore.exists():
            return []

        patterns: list[str] = []
        try:
            for line in gitignore.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                # Skip comments and empty lines; skip negation (!) — too complex
                if not line or line.startswith("#") or line.startswith("!"):
                    continue
                patterns.append(line)
        except OSError:
            pass
        return patterns

    def _is_ignored(self, path: Path) -> bool:
        """Return True if path should be excluded from the structure."""
        name = path.name

        if name in IGNORED_DIRS:
            return True

        if self._gitignore_patterns:
            # Build relative path string from root for matching
            try:
                rel = str(path.relative_to(self.root))
            except ValueError:
                rel = name

            for pattern in self._gitignore_patterns:
                # Strip trailing slash for directory patterns
                clean = pattern.rstrip("/")

                # Match against name alone or relative path
                if fnmatch.fnmatch(name, clean):
                    return True
                if fnmatch.fnmatch(rel, clean):
                    return True
                # Handle ** by also matching trailing portion
                if "**" in clean:
                    glob_pat = clean.replace("**/", "").replace("**", "*")
                    if fnmatch.fnmatch(name, glob_pat):
                        return True

        return False

    def _build_tree(self, directory: Path, prefix: str) -> list[str]:
        """Recursively build tree lines for a directory.

        Args:
            directory: Current directory to list.
            prefix: Indentation prefix string for the current depth.

        Returns:
            List of tree lines.
        """
        try:
            entries = sorted(directory.iterdir(), key=lambda p: (p.is_file(), p.name))
        except OSError:
            return []

        visible = [e for e in entries if not self._is_ignored(e)]
        lines: list[str] = []

        for i, entry in enumerate(visible):
            is_last = i == len(visible) - 1
            connector = _LAST if is_last else _BRANCH
            child_prefix = prefix + (_SPACE if is_last else _PIPE)

            if entry.is_dir():
                lines.append(f"{prefix}{connector}{entry.name}/")
                lines.extend(self._build_tree(entry, child_prefix))
            else:
                lines.append(f"{prefix}{connector}{entry.name}")

        return lines
