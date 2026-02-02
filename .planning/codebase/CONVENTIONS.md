# Coding Conventions

**Analysis Date:** 2026-02-02

## Language

**Primary:** Python 3.12+

## Naming Patterns

**Files:**
- snake_case for all Python files (e.g., `cache_manager.py`, `task_result.py`)
- Single-purpose modules with descriptive names

**Classes:**
- PascalCase for class names (e.g., `ProjectMapper`, `CacheManager`, `Summarizer`)
- Suffix with descriptive type when applicable (e.g., `ProjectMapperResult`, `FileSummary`)

**Functions:**
- snake_case for function names (e.g., `compute_file_hash`, `discover_python_files`)
- Descriptive, verb-based names that indicate action

**Variables:**
- snake_case for local variables (e.g., `module_summaries`, `current_hash`)
- Single-letter variables only for trivial loops (`f`, `p`)

**Constants:**
- SCREAMING_SNAKE_CASE for constants (e.g., `EXCLUDED_DIRS`, `MAX_RETRIES`, `HASHES_FILENAME`)

**Private Members:**
- Leading underscore for private attributes/methods (e.g., `_summarizer`, `_ensure_cache_dir`)

## Type Hints

**Style:** Python 3.12+ native syntax with built-in generics

**Examples from codebase:**
```python
def __init__(self, root: Path, llm: BaseChatModel) -> None:
    ...

def scan(self) -> Generator[TaskResult[ProjectMapperResult], Any, None]:
    ...

module_summaries: dict[Path, str] = {}
```

**Union Types:** Use `|` operator (Python 3.10+) instead of `Union[]`:
```python
cache_dir: Path | None = None
summary: str | None = None
```

## Code Structure

**Imports:**
1. Standard library imports
2. Third-party imports
3. Relative imports (grouped by depth)

```python
import logging
from pathlib import Path
from typing import Any, Generator
from langchain_core.messages import HumanMessage
from code_monkey.agents.project_librarian.cache_manager import CacheManager
```

**Relative Imports:** Use explicit relative imports with leading dots:
```python
from code_monkey.agents.project_librarian.utils import (
    compute_file_hash,
    discover_python_files,
)
```

**Module Structure:**
- Docstring at module top describing purpose
- Classes first, then functions
- `__all__` export list at bottom

## Class Design

**Base Classes:**
- Use `@dataclass` decorator for simple data containers
- Use `NamedTuple` for simple immutable records
- Inherit from `BaseModel` for Pydantic models (LangChain integration)

**Examples:**
```python
@dataclass
class TaskResult(Generic[T]):
    """Generic container for task result with progress tracking."""
    result: T
    progress: int
    progress_max: int

class CodeNode(NamedTuple):
    """Represents a node in the code structure tree."""
    name: str
    type: str
    children: list["CodeNode"] = []
```

**Properties:**
- Use `@property` decorator for computed attributes
- Keep side effects out of properties

**Private Members:**
- Prefix with single underscore: `_cache`, `_summarizer`
- No dunder (`__`) unless required by protocol

## Function Design

**Return Types:** Always specify return type annotations

**Docstrings:** Google-style docstrings for all public functions

```python
def compute_file_hash(filepath: Path | str) -> str:
    """Compute SHA-256 hash of a file for change detection.

    Args:
        filepath: Path to the file (Path object or string)

    Returns:
        Hexadecimal digest of the file's SHA-256 hash

    Raises:
        OSError: If the file cannot be read
    """
```

**Generator Functions:** Use `Generator` type for functions that yield:
```python
def scan(self) -> Generator[TaskResult[ProjectMapperResult], Any, None]:
    """Perform a full project scan.

    Yields:
        TaskResult containing ProjectMapperResult with progress tracking.
    """
```

## Error Handling

**Exceptions:**
- Use specific exception types
- Document exceptions in docstrings
- Catch only what you can handle

**Example:**
```python
try:
    with open(hashes_file, "r", encoding="utf-8") as f:
        return json.load(f)
except (json.JSONDecodeError, OSError):
    return {}
```

**Retry Logic:**
- Exponential backoff for external operations (see `Summarizer._summarize_with_retry`)
- Max retries constant defined as class attribute

## Logging

**Framework:** Python standard library `logging`

**Setup:**
```python
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)
```

**Usage:**
- Use `logger.info()`, `logger.error()`, `logger.debug()` appropriately
- Format messages as sentences (no leading capital in message)

## File Operations

**Path Handling:**
- Use `pathlib.Path` for all path operations
- Avoid string concatenation for paths
- Use `encoding="utf-8"` for text file operations

**Atomic Writes:**
- Use temp file + rename pattern for cache writes:
```python
with tempfile.NamedTemporaryFile(
    mode="w", suffix=".json", dir=self.cache_dir, delete=False
) as tmp:
    json.dump(hashes, tmp, indent=2)
    tmp_path = tmp.name
Path(tmp_path).rename(hashes_file)
```

## Comments

**When to Comment:**
- Complex algorithms or non-obvious logic
- TODO items (use `# TODO:` format)
- Why-not-what (code shows what, comment explains why)

**Inline Comments:**
- Avoid obvious comments
- Use sparingly, prefer self-documenting code
- Short, imperative style

## Async/Await

**Pattern:** Use `async def` for async operations

```python
async def create(cls, model, headless: bool = True):
    """Async factory method."""
    playwright_tools = await PlaywrightTools.initialize(headless=headless)
    ...
```

**Await Pattern:** Pass config via `RunnableConfig` for LangGraph:
```python
response = await self._agent.ainvoke(
    {"messages": messages},
    config=RunnableConfig(configurable={"thread_id": thread_id})
)
```

## Concurrency

**ThreadPoolExecutor:** For parallel I/O-bound operations

```python
with ThreadPoolExecutor() as executor:
    file_summaries = list(executor.map(self._summarize_single_file, files))
```

## String Formatting

**Style:** f-strings for all variable interpolation

```python
return f"ProjectMapperResult(modules={len(self.module_summaries)})"
```

## Deprecation Pattern

Not currently used in codebase, but pattern established in similar projects:
```python
import warnings
warnings.warn("Function name is deprecated", DeprecationWarning, stacklevel=2)
```

---

*Convention analysis: 2026-02-02*
