# Phase 01: Build Project Librarian Agent Utilities - Research

**Researched:** 2026-01-31
**Domain:** Python file discovery, code parsing, and change detection utilities
**Confidence:** HIGH

## Summary

This phase implements utility functions for the Project Librarian agent to discover files, parse Python code structure, and compute hashes for change detection. The approach uses Python's standard library (pathlib, ast, hashlib) where possible, with tree-sitter available for more advanced use cases. All utilities are local-only with no external dependencies beyond the existing LangGraph stack.

**Primary recommendation:** Use Python's standard library (pathlib, ast, hashlib) for all core utilities. Tree-sitter is available as an optional enhancement for more robust parsing with query support.

## Standard Stack

### Core Libraries

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `pathlib` | Python 3.4+ | File discovery with glob patterns | Built-in, intuitive, cross-platform |
| `ast` | Python 3.8+ | Parse Python code structure | Built-in, accurate for Python |
| `hashlib` | Python 3.11+ (file_digest) | SHA-256 file hashing | Built-in, secure, efficient |

### Supporting (Already in Dependencies)

| Library | Purpose | When to Use |
|---------|---------|-------------|
| `dotenv` | Environment variable loading | Already in pyproject.toml |

### Dependencies to Add

None required for core functionality. The standard library provides all needed capabilities.

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `pathlib` | `glob` / `os.walk` | `pathlib` is more object-oriented and integrates better |
| `ast` | `py-tree-sitter` | `ast` is built-in and sufficient for Python; tree-sitter for advanced queries |
| `hashlib` | `xxhash` | `xxhash` is faster but requires adding dependency; SHA-256 is standard |

## Architecture Patterns

### Recommended Project Structure

```
code_monkey/
├── agents/
│   └── project_librarian/
│       ├── __init__.py
│       ├── utilities/           # NEW: Phase 01 utilities
│       │   ├── __init__.py
│       │   ├── file_discovery.py
│       │   ├── code_parser.py
│       │   └── hash_utils.py
│       ├── project_librarian.py
│       └── tools.py
```

### Pattern 1: File Discovery with pathlib

**What:** Recursively find files matching patterns while excluding venv, .git, pytest_cache, etc.

**When to use:** For discovering Python source files across a project

**Example:**
```python
from pathlib import Path

EXCLUDED_DIRS = {'.git', 'venv', '.venv', '__pycache__', 'pytest_cache', 'node_modules', '.tox', 'dist', 'build'}

def discover_python_files(root: Path, pattern: str = "**/*.py") -> list[Path]:
    """Discover Python files matching pattern, excluding common directories."""
    all_files = root.glob(pattern)
    return sorted([
        f for f in all_files
        if f.is_file() and not any(excluded in f.parts for excluded in EXCLUDED_DIRS)
    ])

# Usage
root = Path("/path/to/project")
python_files = discover_python_files(root)
```

**Source:** [Python pathlib documentation](https://docs.python.org/3/library/pathlib.html)

### Pattern 2: Code Structure Extraction with AST

**What:** Parse Python source code to extract classes, functions, and imports.

**When to use:** For understanding code structure in Python files

**Example:**
```python
import ast
from dataclasses import dataclass, field
from typing import NamedTuple

class ParsedCode(NamedTuple):
    classes: list[str]
    functions: list[str]
    imports: list[str]

class CodeExtractor(ast.NodeVisitor):
    def __init__(self):
        self.classes: list[str] = []
        self.functions: list[str] = []
        self.imports: list[str] = []

    def visit_ClassDef(self, node):
        self.classes.append(node.name)
        self.generic_visit(node)

    def visit_FunctionDef(self, node):
        self.functions.append(node.name)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node):
        self.functions.append(f"async {node.name}")
        self.generic_visit(node)

    def visit_Import(self, node):
        for alias in node.names:
            self.imports.append(alias.name)

    def visit_ImportFrom(self, node):
        module = node.module or ''
        for alias in node.names:
            self.imports.append(f"{module}.{alias.name}")

def parse_python_code(source: str) -> ParsedCode:
    """Extract classes, functions, and imports from Python source."""
    tree = ast.parse(source)
    extractor = CodeExtractor()
    extractor.visit(tree)
    return ParsedCode(
        classes=extractor.classes,
        functions=extractor.functions,
        imports=extractor.imports
    )
```

**Source:** [Python ast module documentation](https://docs.python.org/3/library/ast.html)

### Pattern 3: SHA-256 File Hashing for Change Detection

**What:** Compute cryptographic hash of file contents to detect changes.

**When to use:** For caching and detecting when files have been modified

**Example:**
```python
import hashlib
from pathlib import Path

def compute_file_hash(filepath: Path) -> str:
    """Compute SHA-256 hash of a file for change detection."""
    with open(filepath, "rb") as f:
        digest = hashlib.file_digest(f, "sha256")
    return digest.hexdigest()

def detect_file_change(filepath: Path, stored_hash: str | None) -> tuple[bool, str]:
    """Check if file has changed from stored hash."""
    current_hash = compute_file_hash(filepath)
    has_changed = stored_hash is None or stored_hash != current_hash
    return has_changed, current_hash
```

**Source:** [Python hashlib documentation](https://docs.python.org/3/library/hashlib.html)

### Anti-Patterns to Avoid

- **Don't use string parsing** for code analysis - use ast or tree-sitter for accurate parsing
- **Don't hardcode exclusion patterns** - make them configurable for different project types
- **Don't hash on every access** - cache hashes and only recompute when mtime changes

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| File pattern matching | Custom recursive search | `pathlib.Path.glob()` | Handles symlinks, edge cases, cross-platform |
| Python code parsing | Regex or string analysis | `ast` module | Accurate AST, handles all Python syntax |
| File hashing | MD5 or custom algorithm | `hashlib.sha256()` | Cryptographically secure, efficient |
| Directory exclusion | Hardcoded conditionals | Set-based filtering | Clear, maintainable, extensible |

**Key insight:** Python's standard library is mature and battle-tested. Custom implementations for file discovery and hashing are error-prone and rarely necessary.

## Common Pitfalls

### Pitfall 1: Hidden Directory Inclusion

**What goes wrong:** `Path.glob("**/*.py")` includes files in `.git/`, `venv/`, etc.

**Why it happens:** Patterns match all directories; filtering must be explicit.

**How to avoid:** Filter by checking `f.parts` for excluded directory names:

```python
EXCLUDED_DIRS = {'.git', 'venv', '__pycache__', '.venv'}
python_files = [
    f for f in root.glob("**/*.py")
    if f.is_file() and not any(part in EXCLUDED_DIRS for part in f.parts)
]
```

**Warning signs:** Finding unexpected files in `.git/objects/`, `venv/lib/`, etc.

### Pitfall 2: Syntax Errors Blocking AST Parsing

**What goes wrong:** `ast.parse()` raises SyntaxError on files with invalid Python.

**Why it happens:** Not all `.py` files contain valid Python code.

**How to avoid:** Wrap parsing in try-except and handle gracefully:

```python
def safe_parse_python_file(filepath: Path) -> ParsedCode | None:
    """Parse Python file, returning None on syntax errors."""
    try:
        with open(filepath) as f:
            source = f.read()
        return parse_python_code(source)
    except (SyntaxError, ValueError):
        return None
```

**Warning signs:** Process crashes on a single malformed file.

### Pitfall 3: Hashing Large Files Inefficiently

**What goes wrong:** Reading entire file into memory for hashing on every check.

**Why it happens:** Naive implementation loads full file content.

**How to avoid:** Use `hashlib.file_digest()` which handles streaming efficiently:

```python
# Inefficient - loads entire file
with open(filepath, "rb") as f:
    content = f.read()
    hash = hashlib.sha256(content).hexdigest()

# Efficient - streams through file
with open(filepath, "rb") as f:
    digest = hashlib.file_digest(f, "sha256")
    hash = digest.hexdigest()
```

**Warning signs:** High memory usage on projects with large files.

## Code Examples

### File Discovery Utility

```python
from pathlib import Path
from typing import Iterator

EXCLUDED_DIRS = frozenset({
    '.git', '.svn', '.hg',
    'venv', '.venv', 'env', '.env',
    '__pycache__', '.pytest_cache', '.tox',
    'node_modules', 'bower_components',
    'dist', 'build', '.egg-info',
    '.tox', '.nox', '.mypy_cache',
})

def discover_files(
    root: Path,
    pattern: str = "**/*.py",
    exclude_dirs: frozenset[str] = EXCLUDED_DIRS
) -> Iterator[Path]:
    """Discover files matching pattern, excluding specified directories."""
    for path in root.glob(pattern):
        if path.is_file():
            parts = set(path.parts)
            if not parts & exclude_dirs:
                yield path
```

### Complete Code Parser

```python
import ast
from dataclasses import dataclass, field
from pathlib import Path
from typing import NamedTuple, Optional

class ParsedFile(NamedTuple):
    filepath: Path
    classes: list[str]
    functions: list[str]
    imports: list[str]

class CodeExtractor(ast.NodeVisitor):
    def __init__(self):
        self.classes: list[str] = []
        self.functions: list[str] = []
        self.imports: list[str] = []

    def visit_ClassDef(self, node):
        self.classes.append(node.name)
        self.generic_visit(node)

    def visit_FunctionDef(self, node):
        self.functions.append(node.name)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node):
        self.functions.append(f"async {node.name}")
        self.generic_visit(node)

    def visit_Import(self, node):
        for alias in node.names:
            self.imports.append(alias.name)

    def visit_ImportFrom(self, node):
        module = node.module or ''
        for alias in node.names:
            self.imports.append(f"{module}.{alias.name}")

def parse_python_file(filepath: Path) -> Optional[ParsedFile]:
    """Parse a Python file and extract structure information."""
    try:
        with open(filepath) as f:
            source = f.read()
        tree = ast.parse(source, filename=str(filepath))
        extractor = CodeExtractor()
        extractor.visit(tree)
        return ParsedFile(
            filepath=filepath,
            classes=extractor.classes,
            functions=extractor.functions,
            imports=extractor.imports
        )
    except (SyntaxError, OSError):
        return None
```

### Hash-based Change Detection

```python
import hashlib
from pathlib import Path
from dataclasses import dataclass

@dataclass
class FileHash:
    filepath: Path
    hash: str

def compute_file_hash(filepath: Path) -> str:
    """Compute SHA-256 hash of a file."""
    with open(filepath, "rb") as f:
        digest = hashlib.file_digest(f, "sha256")
    return digest.hexdigest()

def check_changes(
    filepath: Path,
    previous_hash: str | None = None
) -> tuple[bool, str]:
    """Check if file has changed since last hash."""
    current_hash = compute_file_hash(filepath)
    changed = previous_hash is None or previous_hash != current_hash
    return changed, current_hash
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `hashlib.md5()` | `hashlib.sha256()` | 2004+ | SHA-256 is collision-resistant, recommended |
| `hashlib.sha1()` | `hashlib.sha256()` | 2017+ | SHA-1 broken for collisions |
| Manual file read + hash | `hashlib.file_digest()` | Python 3.11+ | More efficient, less error-prone |
| `os.walk()` | `pathlib.Path.glob()` | Python 3.4+ | More Pythonic, integrates Path API |
| Regex parsing | `ast` module | Always | `ast` is the standard approach |

### Deprecated/Outdated
- `fnmatch` for pattern matching - use pathlib.glob directly
- `glob.glob()` / `glob.walk()` - use pathlib equivalents
- Custom exception handling for file discovery - pathlib handles errors

## Open Questions

1. **Tree-sitter integration timing**
   - What we know: tree-sitter-py provides more robust parsing with query support
   - What's unclear: Whether the added complexity is needed for initial phase
   - Recommendation: Start with ast, add tree-sitter as future enhancement if needed for multilanguage support or complex queries

2. **Caching strategy details**
   - What we know: Hash-based change detection is needed
   - What's unclear: Cache file format and location (`.codemonkey/file-hashes` per CLAUDE.md)
   - Recommendation: Design cache infrastructure in a follow-up phase after core utilities work

## Sources

### Primary (HIGH confidence)
- [pathlib.Path.glob() documentation](https://docs.python.org/3/library/pathlib.html) - File discovery patterns
- [ast module documentation](https://docs.python.org/3/library/ast.html) - Python code parsing with AST
- [hashlib.file_digest() documentation](https://docs.python.org/3/library/hashlib.html) - SHA-256 file hashing
- [/tree-sitter/py-tree-sitter](https://context7.com/tree-sitter/py-tree-sitter/llms.txt) - Tree-sitter Python bindings

### Secondary (MEDIUM confidence)
- Existing code patterns in `/code_monkey/agents/web_researcher/tools.py` - LangChain tool conventions

### Tertiary (LOW confidence)
- Community patterns for directory exclusion (verified via standard library docs)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Python standard library is well-documented and stable
- Architecture: HIGH - Patterns are well-established and documented
- Pitfalls: HIGH - Common issues are well-known and documented in official docs

**Research date:** 2026-01-31
**Valid until:** 2027-01-31 (standard library APIs are stable)
