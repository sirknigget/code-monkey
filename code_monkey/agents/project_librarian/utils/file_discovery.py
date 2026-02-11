"""File discovery utilities for the Project Librarian agent."""

from pathlib import Path
from typing import Iterator


# Directories to exclude when discovering files.
# Includes version control, virtual environments, Python caches, and build artifacts.
EXCLUDED_DIRS: frozenset[str] = frozenset({
    # Version control
    '.git',
    '.svn',
    '.hg',
    # Virtual environments
    'venv',
    '.venv',
    'env',
    '.env',
    # Python caches and tools
    '__pycache__',
    '.pytest_cache',
    '.tox',
    '.nox',
    '.mypy_cache',
    # JavaScript dependencies
    'node_modules',
    'bower_components',
    # Build artifacts
    'dist',
    'build',
    '.egg-info',
})


def discover_python_files(
    root: Path,
    pattern: str = "**/*.py",
    exclude_dirs: frozenset[str] = EXCLUDED_DIRS,
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
