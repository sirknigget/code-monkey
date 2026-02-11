"""Shared constants for the Project Librarian agent utilities."""

# Directories and file patterns to exclude when discovering files or building
# the project structure tree. Covers version control, virtual environments,
# Python caches and tools, JavaScript dependencies, build artifacts, IDE
# metadata, macOS metadata, and the codemonkey cache.
IGNORED_DIRS: frozenset[str] = frozenset(
    {
        # Version control
        ".git",
        ".svn",
        ".hg",
        # Virtual environments
        "venv",
        ".venv",
        "env",
        ".env",
        # Python caches and tools
        "__pycache__",
        ".pytest_cache",
        ".tox",
        ".nox",
        ".mypy_cache",
        ".ruff_cache",
        # JavaScript dependencies
        "node_modules",
        "bower_components",
        # Build artifacts
        "dist",
        "build",
        ".egg-info",
        # IDE / editor
        ".idea",
        ".vscode",
        # macOS metadata
        ".DS_Store",
        # codemonkey cache
        ".codemonkey",
    }
)
