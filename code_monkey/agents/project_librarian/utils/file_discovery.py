"""File discovery utilities for the Project Librarian agent."""

from pathlib import Path

from code_monkey.agents.project_librarian.utils.constants import IGNORED_DIRS
from code_monkey.agents.project_librarian.utils.gitignore import (
    is_path_gitignored,
    load_gitignore_patterns,
)


def discover_python_files(
    root: Path,
    pattern: str = "**/*.py",
    exclude_dirs: frozenset[str] = IGNORED_DIRS,
) -> list[Path]:
    """Discover Python files matching pattern, excluding specified directories and
    any paths covered by a .gitignore file at the project root.

    Args:
        root: The root directory to search from.
        pattern: Glob pattern to match files (default: "**/*.py").
        exclude_dirs: Frozenset of directory names to exclude.

    Returns:
        A sorted list of Path objects for matching Python files.
    """
    gitignore_patterns = load_gitignore_patterns(root)
    result: list[Path] = []
    for f in root.glob(pattern):
        if not f.is_file():
            continue
        if any(part in exclude_dirs for part in f.parts):
            continue
        rel = f.relative_to(root)
        if is_path_gitignored(rel, gitignore_patterns):
            continue
        result.append(rel)
    return sorted(result)
