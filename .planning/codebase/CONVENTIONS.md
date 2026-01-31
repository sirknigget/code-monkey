# Coding Conventions

**Analysis Date:** 2026-01-31

## Naming Patterns

**Files:**
- Snake_case: `file_discovery.py`, `hash_utils.py`
- Descriptive names reflecting functionality

**Functions:**
- Snake_case: `discover_python_files()`, `compute_file_hash()`, `parse_python_code()`
- Verb-noun pattern for action functions: `discover_*`, `compute_*`, `parse_*`, `dump_*`
- Prefix `_` for private/internal methods: `_playwright`, `_browser`, `_tools`

**Variables:**
- Snake_case: `root`, `pattern`, `exclude_dirs`, `all_files`
- Underscore suffix to avoid shadowing builtins: `class_` (if needed)
- Constants: UPPER_SCREAMING_CASE for true constants

**Types:**
- PascalCase for classes: `ParsedCode`, `CodeExtractor`, `SearchResult`, `PlaywrightTools`
- NamedTuple for simple data structures: `ParsedCode`
- BaseModel for Pydantic models: `SearchResult`

## Code Style

**Formatting:**
- No explicit formatter configured (pyproject.toml shows minimal config)
- Follows PEP 8 conventions (4 spaces indentation, line length ~88 typical)

**Linting:**
- No explicit linter configured
- Python 3.12+ required with strict typing

**Type Hints:**
- Used throughout codebase
- Union types with `|` operator: `Path | str`
- Generics: `list[Path]`, `Iterator[Path]`, `frozenset[str]`
- Optional types: `str = None` for nullable parameters

## Import Organization

**Standard Library First:**
```python
from pathlib import Path
from typing import Iterator, NamedTuple
import hashlib
import ast
```

**Third-Party Imports:**
```python
from langchain_community.agent_toolkits import PlayWrightBrowserToolkit
from langchain_community.utilities import GoogleSerperAPIWrapper
from langchain_core.tools import tool
from playwright.async_api import async_playwright
```

**Local Application Imports:**
```python
from code_monkey.agents.project_librarian.utilities.file_discovery import (
    discover_python_files,
)
from code_monkey.utils.langchain_utils import last_message_content
```

**Path Aliases:**
- No path aliases configured
- Use relative imports within modules where appropriate

## Error Handling

**Pattern: Try-Except with Cleanup:**
```python
def compute_file_hash(filepath: Path | str) -> str:
    try:
        path = Path(filepath)
        with open(path, "rb") as f:
            digest = hashlib.file_digest(f, "sha256")
        return digest.hexdigest()
    except OSError:
        # Re-raise or handle
        raise
```

**Exception Propagation:**
- Errors propagate to caller (OSError from file operations)
- Syntax errors caught and return empty result: `except SyntaxError: return ParsedCode(...)`

**Assertions:**
- Used for invariants in tests: `assert len(result) == 2`
- Not used for runtime error handling in production code

## Logging

**Framework:** `print()` statements or `None`

**Patterns:**
- No structured logging framework detected
- Simple print for output in tools: `print(f"\n=== Google Search Results for '{query}' ===\n")`

## Comments

**When to Comment:**
- Explain complex logic or non-obvious behavior
- Document module purpose at top of file

**JSDoc/TSDoc:**
- Python docstrings following Google style:
```python
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
```

**Module-Level Docstrings:**
```python
"""File discovery utilities for the Project Librarian agent."""
"""Hash computation utilities for file change detection."""
```

## Function Design

**Size:** Functions are focused and single-purpose (10-50 lines typical)

**Parameters:**
- Default values for optional parameters
- Type hints required
- Named parameters for clarity

**Return Values:**
- Explicit return types in type hints
- Empty collections instead of null where appropriate
- NamedTuple for structured returns

## Module Design

**Exports:**
- Explicit `__all__` in utility modules:
```python
__all__ = ["discover_python_files", "parse_python_code", "compute_file_hash"]
```

**Barrel Files:**
- `utilities/__init__.py` re-exports public functions
- Single-line imports for public API

**Class Design:**
- Minimal classes, prefer functions where possible
- NamedTuple for simple data containers
- BaseModel for Pydantic models with validation
- Class methods for alternative constructors: `PlaywrightTools.initialize()`

---

*Convention analysis: 2026-01-31*
