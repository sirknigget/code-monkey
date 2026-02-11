"""File discovery utilities for the Project Librarian agent."""

from pathlib import Path
from typing import Iterator

from code_monkey.agents.project_librarian.utils.constants import IGNORED_DIRS


def discover_python_files(
    root: Path,
    pattern: str = "**/*.py",
    exclude_dirs: frozenset[str] = IGNORED_DIRS,
) -> list[Path]:
    """Discover Python files matching pattern, excluding specified directories.

    Args:
        root: The root directory to search from.
        pattern: Glob pattern to match files (default: "**/*.py").
        exclude_dirs: Frozenset of directory names to exclude.

    Returns:
        A sorted list of Path objects for matching Python files.
    """
    all_files: Iterator[Path] = root.glob(pattern)
    return sorted(
        f.relative_to(root) for f in all_files
        if f.is_file() and not any(part in exclude_dirs for part in f.parts)
    )
