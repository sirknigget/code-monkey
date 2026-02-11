"""Utilities for loading and applying .gitignore filter patterns."""

from __future__ import annotations

import fnmatch
from pathlib import Path


def load_gitignore_patterns(root: Path) -> list[str]:
    """Load ignore patterns from a .gitignore file at the project root.

    Blank lines, comments (#), and negation patterns (!) are skipped.

    Args:
        root: Directory that may contain a .gitignore file.

    Returns:
        List of raw pattern strings, ready for use with is_gitignore_match.
    """
    gitignore = root / ".gitignore"
    if not gitignore.exists():
        return []

    patterns: list[str] = []
    try:
        for line in gitignore.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("!"):
                continue
            patterns.append(line)
    except OSError:
        pass
    return patterns


def is_gitignore_match(name: str, rel: str, patterns: list[str]) -> bool:
    """Return True if a path component matches any of the given gitignore patterns.

    Args:
        name: Basename of the entry (e.g. "secret.cfg").
        rel:  Path of the entry relative to the project root (e.g. "configs/secret.cfg").
        patterns: Patterns loaded by load_gitignore_patterns.

    Returns:
        True if the entry should be excluded, False otherwise.
    """
    for pattern in patterns:
        clean = pattern.rstrip("/")

        if fnmatch.fnmatch(name, clean):
            return True
        if fnmatch.fnmatch(rel, clean):
            return True
        if "**" in clean:
            glob_pat = clean.replace("**/", "").replace("**", "*")
            if fnmatch.fnmatch(name, glob_pat):
                return True

    return False


def is_path_gitignored(rel_path: Path, patterns: list[str]) -> bool:
    """Return True if a relative path or any of its ancestor directories is gitignored.

    Unlike is_gitignore_match — which checks a single path component — this function
    walks every segment of ``rel_path`` so that a file inside a gitignored directory
    is correctly excluded even when files are discovered via a flat glob.

    Args:
        rel_path: Path relative to the project root (e.g. Path("secrets/key.txt")).
        patterns: Patterns loaded by load_gitignore_patterns.

    Returns:
        True if the path or any ancestor matches a gitignore pattern.
    """
    if not patterns:
        return False

    parts = rel_path.parts
    for i, part in enumerate(parts):
        sub_rel = str(Path(*parts[: i + 1]))
        if is_gitignore_match(part, sub_rel, patterns):
            return True

    return False
