# Phase 02: Project Mapper Class - Research

**Researched:** 2026-02-01
**Domain:** LLM-augmented project structure analysis and context generation
**Confidence:** HIGH

## Summary

Phase 02 implements a `ProjectMapper` class that orchestrates file discovery, change detection, and LLM-powered summarization to generate project context files. The class builds directly on Phase 01 utilities (`discover_python_files`, `parse_python_code`, `compute_file_hash`) and adds hierarchical, top-down directory scanning with LLM summarization at each level.

**Primary recommendation:** Implement a depth-first, top-down traversal pattern where each directory's files are summarized, then a module-level summary is generated combining file summaries. Use LangChain's structured output patterns for LLM interactions. Store results in the planned `.codemonkey/` cache structure.

## Standard Stack

### Core Dependencies (Already Available)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `langchain` | 0.3.x | LLM orchestration | Already in dependencies |
| `langchain-openai` / `langchain-anthropic` | 0.3.x | Model integrations | Already in dependencies |
| `pathlib` | Python 3.4+ | Directory traversal | Built-in, Phase 01 already uses |
| `hashlib` | Python 3.11+ | Change detection | Built-in, Phase 01 already uses |
| `ast` | Python 3.8+ | Code parsing | Built-in, Phase 01 already uses |

### Supporting (Already in Dependencies)

| Library | Purpose | When to Use |
|---------|---------|-------------|
| `pydantic` | Schema validation for LLM output | Structured LLM responses |

### Dependencies to Add

None required. All capabilities are available in existing dependencies.

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Custom traversal | `os.walk()` | `pathlib` is more Pythonic, integrates with Phase 01 |
| Custom LLM calls | Raw API requests | LangChain provides structured output, retry logic, model abstraction |
| Custom caching | SQLite database | JSON files in `.codemonkey/` are simpler for this use case |

## Architecture Patterns

### Recommended Project Structure

```
code_monkey/
├── agents/
│   └── project_librarian/
│       ├── __init__.py
│       ├── utilities/              # Phase 01 - already exists
│       │   ├── __init__.py
│       │   ├── file_discovery.py
│       │   ├── code_parser.py
│       │   └── hash_utils.py
│       ├── project_mapper.py       # NEW: Phase 02
│       └── cache/                  # NEW: Cache infrastructure
│           ├── file_hashes.json
│           ├── code_context/       # Per-file summaries
│           └── project_context/    # Global context
```

### Pattern 1: Top-Down Directory Traversal with Change Detection

**What:** Scan directories depth-first, only processing modified files/directories based on hash comparison.

**When to use:** For efficient incremental updates to project context.

**Example:**
```python
from pathlib import Path
from .utilities import discover_python_files, compute_file_hash

class ProjectMapper:
    def __init__(self, root: Path, llm, cache_dir: Path):
        self.root = root
        self.llm = llm
        self.cache_dir = cache_dir
        self.file_hashes = self._load_file_hashes()

    def _load_file_hashes(self) -> dict[str, str]:
        """Load stored file hashes from cache."""
        hashes_file = self.cache_dir / "file_hashes.json"
        if hashes_file.exists():
            return json.loads(hashes_file.read_text())
        return {}

    def _get_modified_files(self) -> list[Path]:
        """Return files that have changed since last scan."""
        modified = []
        for filepath in discover_python_files(self.root):
            current_hash = compute_file_hash(filepath)
            stored_hash = self.file_hashes.get(str(filepath))
            if stored_hash != current_hash:
                modified.append(filepath)
        return modified

    def _scan_directory_top_down(self, directory: Path) -> list[dict]:
        """Get directory structure, processing parents before children."""
        results = []
        for item in sorted(directory.iterdir()):
            if item.is_dir() and not self._is_excluded(item):
                # Process children first (recursive)
                child_results = self._scan_directory_top_down(item)
                results.extend(child_results)
                # Then process this directory
                if self._directory_modified(item):
                    results.append(self._process_directory(item))
        return results
```

**Source:** Phase 01 file discovery patterns, LangChain structured output

### Pattern 2: LLM-Powered File Summarization

**What:** Prompt an LLM to summarize a code file's purpose using its structure.

**When to use:** For generating per-file context that feeds into module summaries.

**Example:**
```python
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

class ProjectMapper:
    def __init__(self, llm):
        self.llm = llm
        self.file_summary_prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a code analyst. Summarize the purpose of this file."),
            ("human", "File: {filepath}\n\nStructure:\n{structure}\n\nExplain what this file does in 2-3 sentences.")
        ])
        self.file_summary_chain = self.file_summary_prompt | self.llm | StrOutputParser()

    def summarize_file(self, filepath: Path) -> str:
        """Generate LLM summary for a single file."""
        source = filepath.read_text()
        parsed = parse_python_code(source)
        return self.file_summary_chain.invoke({
            "filepath": str(filepath),
            "structure": parsed.llm_friendly_string()
        })
```

**Source:** LangChain RAG patterns, Phase 01 code_parser output

### Pattern 3: Hierarchical Module Summarization

**What:** After summarizing all files in a directory, generate a module-level summary combining them.

**When to use:** For creating parent context that feeds into child directory processing.

**Example:**
```python
class ProjectMapper:
    def summarize_module(self, directory: Path, file_summaries: list[dict], parent_summary: str | None = None) -> str:
        """Generate module summary combining file summaries with parent context."""
        module_prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a code analyst. Create a module summary."),
            ("human", """Parent module context: {parent_context}

Files in this module:
{file_summaries}

Provide a summary of this module's purpose and how it relates to the parent module.""")
        ])
        chain = module_prompt | self.llm | StrOutputParser()
        return chain.invoke({
            "parent_context": parent_summary or "This is the root module.",
            "file_summaries": "\n\n".join(f["summary"] for f in file_summaries)
        })
```

### Pattern 4: Incremental Cache Management

**What:** Store file hashes and summaries in JSON files, updating only changed entries.

**When to use:** For efficient re-scanning of large projects.

**Example:**
```python
class ProjectMapper:
    def save_cache(self):
        """Save updated hashes to cache."""
        hashes_file = self.cache_dir / "file_hashes.json"
        hashes_file.write_text(json.dumps(self.file_hashes, indent=2))

    def save_file_summary(self, filepath: Path, summary: str):
        """Save per-file summary to cache."""
        rel_path = filepath.relative_to(self.root)
        summary_file = self.cache_dir / "code_context" / f"{rel_path}.txt"
        summary_file.parent.mkdir(parents=True, exist_ok=True)
        summary_file.write_text(summary)
```

### Anti-Patterns to Avoid

- **Don't process all files on every run** - Always check hashes first for efficiency
- **Don't generate summaries without structure context** - Use `llm_friendly_string()` output from Phase 01
- **Don't skip parent context** - Module summaries must include parent module context for proper hierarchy
- **Don't mix parallel and sequential processing incorrectly** - Files within a directory can be parallelized, but directories must be sequential top-down

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| LLM orchestration | Raw API calls | LangChain chains | Structured output, retries, model swapping |
| Directory traversal | Custom recursive walk | `pathlib.Path.iterdir()` with sorting | Cross-platform, simple API |
| Structured LLM output | String parsing | Pydantic + `with_structured_output()` | Type-safe, validated |
| JSON caching | Custom file format | Python `json` module | Built-in, well-tested |

**Key insight:** LangChain's chain composition patterns (`|`) are ideal for this use case - compose file summarization, module summarization, and project summarization as separate chains.

## Common Pitfalls

### Pitfall 1: Circular Dependency in Module Hierarchy

**What goes wrong:** Child module summaries reference parent summaries that reference child summaries, creating infinite loops or context bloat.

**Why it happens:** Parent context should summarize relationships, not include full child content.

**How to avoid:** Pass only a brief "module purpose" summary to children, not the full parent context:

```python
# WRONG - too much context passed down
child_summary = summarize_module(directory, files, full_parent_summary)

# CORRECT - brief relationship context
child_summary = summarize_module(directory, files, f"This module provides {parent_purpose}")
```

**Warning signs:** Extremely long context being passed, LLM timeouts, or repetitive summaries.

### Pitfall 2: Hash Collision or Cache Invalidation Issues

**What goes wrong:** Modified files aren't detected, or unchanged files are re-processed.

**Why it happens:** Hash computed incorrectly, cache format mismatch, or file path changes.

**How to avoid:** Use absolute paths for cache keys, verify hash format:

```python
def _update_file_hash(self, filepath: Path):
    """Update hash with absolute path as key."""
    abs_path = filepath.absolute()
    self.file_hashes[str(abs_path)] = compute_file_hash(filepath)
```

**Warning signs:** Same file processed repeatedly, or files never get processed after changes.

### Pitfall 3: Inconsistent Ordering Causing Non-Deterministic Output

**What goes wrong:** File order varies between runs, causing different LLM outputs.

**Why it happens:** `os.listdir()` or `Path.iterdir()` order is arbitrary.

**How to avoid:** Always sort results deterministically:

```python
# Always sort file and directory lists
for filepath in sorted(discover_python_files(root)):
    ...
for item in sorted(directory.iterdir()):
    ...
```

**Warning signs:** Different summaries on consecutive runs with no code changes.

### Pitfall 4: LLM Context Window Overflow on Large Projects

**What goes wrong:** Module summary includes too many files, exceeding LLM context.

**Why it happens:** No limit on files per module summary.

**How to avoid:** Chunk large directories, limit files per summary:

```python
MAX_FILES_PER_MODULE = 20

def summarize_module(self, directory: Path, files: list[Path], parent_summary: str | None = None):
    # Process in chunks if too large
    all_summaries = []
    for chunk in self._chunk_files(files, MAX_FILES_PER_MODULE):
        chunk_summaries = [self.summarize_file(f) for f in chunk]
        all_summaries.extend(chunk_summaries)
    # Then combine chunk summaries
```

**Warning signs:** LLM errors about context length, very slow processing.

## Code Examples

### Complete ProjectMapper Skeleton

```python
"""ProjectMapper class for project context file generation."""

import json
from pathlib import Path
from typing import NamedTuple

from langchain_core.language_models import BaseChatModel
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from code_monkey.agents.project_librarian.utilities import (
    discover_python_files,
    parse_python_code,
    compute_file_hash,
)


class FileSummary(NamedTuple):
    """Summary result for a single file."""
    filepath: Path
    summary: str


class ModuleSummary(NamedTuple):
    """Summary result for a directory/module."""
    directory: Path
    files: list[FileSummary]
    module_summary: str


class ProjectMapper:
    """Generates project context through hierarchical LLM summarization.

    Traverse directories top-down:
    1. Scan project for Python files
    2. Check file hashes, only update modified files
    3. For each file, prompt LLM to summarize purpose
    4. For each directory, prompt LLM to create module summary
    5. Create project context summary from tree-formatted representations
    """

    def __init__(
        self,
        root: Path,
        llm: BaseChatModel,
        cache_dir: Path | None = None,
    ):
        """Initialize ProjectMapper.

        Args:
            root: Root directory of the project to map
            llm: LLM instance for generating summaries
            cache_dir: Directory for cache files (default: root/.codemonkey)
        """
        self.root = Path(root)
        self.llm = llm
        self.cache_dir = cache_dir or self.root / ".codemonkey"
        self.file_hashes: dict[str, str] = {}
        self._load_hashes()

    def _load_hashes(self):
        """Load stored file hashes from cache."""
        hashes_file = self.cache_dir / "file_hashes.json"
        if hashes_file.exists():
            self.file_hashes = json.loads(hashes_file.read_text())

    def _is_modified(self, filepath: Path) -> bool:
        """Check if file has been modified since last scan."""
        current_hash = compute_file_hash(filepath)
        stored_hash = self.file_hashes.get(str(filepath))
        return stored_hash != current_hash

    def run(self, paths_to_update: list[Path] | None = None) -> None:
        """Run project mapping, optionally updating only specific paths.

        Args:
            paths_to_update: Optional list of specific paths to update.
                           If None, scan entire project with change detection.
        """
        if paths_to_update:
            self._update_specific_paths(paths_to_update)
        else:
            self._scan_and_update_all()

    def _scan_and_update_all(self):
        """Scan entire project and update changed files."""
        modified_files = [
            f for f in discover_python_files(self.root)
            if self._is_modified(f)
        ]
        # Process directories top-down based on modified files
        self._process_modified_files(modified_files)
        self._save_hashes()

    def _process_modified_files(self, files: list[Path]):
        """Process modified files and their parent directories."""
        # Group by directory
        dirs_by_file = {}
        for f in files:
            parent = f.parent
            dirs_by_file.setdefault(parent, []).append(f)

        # Process directories top-down
        for directory in sorted(dirs_by_file.keys()):
            self._process_directory(directory, dirs_by_file[directory])

    def _process_directory(self, directory: Path, modified_files: list[Path]):
        """Process a single directory: summarize files, then create module summary."""
        file_summaries = [self._summarize_file(f) for f in sorted(modified_files)]
        module_summary = self._create_module_summary(directory, file_summaries)
        self._save_module_summary(directory, module_summary)

    def _summarize_file(self, filepath: Path) -> FileSummary:
        """Summarize a single file using LLM."""
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a code analyst. Summarize file purpose concisely."),
            ("human", "File: {filepath}\n\nStructure:\n{structure}\n\nWhat does this file do?")
        ])
        chain = prompt | self.llm | StrOutputParser()

        source = filepath.read_text()
        parsed = parse_python_code(source)

        summary = chain.invoke({
            "filepath": str(filepath.relative_to(self.root)),
            "structure": parsed.llm_friendly_string()
        })
        return FileSummary(filepath=filepath, summary=summary)

    def _create_module_summary(
        self,
        directory: Path,
        file_summaries: list[FileSummary],
        parent_summary: str | None = None
    ) -> str:
        """Create module summary combining file summaries."""
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a code analyst. Create module summaries."),
            ("human", """Module: {directory}
Parent context: {parent}

Files in this module:
{files}

Provide a 2-3 sentence summary of this module's purpose.""")
        ])
        chain = prompt | self.llm | StrOutputParser()

        return chain.invoke({
            "directory": str(directory.relative_to(self.root)),
            "parent": parent_summary or "This is the root module.",
            "files": "\n".join(f"[{f.filepath.name}] {f.summary}" for f in file_summaries)
        })

    def _save_hashes(self):
        """Save updated file hashes to cache."""
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        hashes_file = self.cache_dir / "file_hashes.json"
        hashes_file.write_text(json.dumps(self.file_hashes, indent=2))

    def _save_module_summary(self, directory: Path, summary: str):
        """Save module summary to cache."""
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        rel_path = directory.relative_to(self.root)
        summary_file = self.cache_dir / "code_context" / f"{rel_path}.txt"
        summary_file.parent.mkdir(parents=True, exist_ok=True)
        summary_file.write_text(summary)

    def get_project_context(self) -> str:
        """Generate final project context summary."""
        # Gather all module summaries and format as tree
        ...
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual code review | LLM-assisted summarization | 2023+ | Scalable, consistent context |
| Flat file summaries | Hierarchical module summaries | 2024+ | Better parent-child relationships |
| Full reprocessing | Hash-based change detection | 2024+ | Efficient incremental updates |
| No caching | `.codemonkey/` cache directory | This project | Enables incremental updates |

### Deprecated/Outdated
- Single-pass project scanning (replaced by incremental hash-based updates)
- Flat namespace for context files (replaced by hierarchical directory structure)

## Open Questions

1. **How to handle very large directories?**
   - What we know: Chunking strategy needed for files > 20 per directory
   - What's unclear: Optimal chunk size, whether to parallelize chunk processing
   - Recommendation: Start with sequential, add parallelization if profiling shows bottleneck

2. **Project context summary format**
   - What we know: Should use tree-formatted representations per requirements
   - What's unclear: Exact format (text tree vs. nested bullet points)
   - Recommendation: Use indentation-based tree format similar to `llm_friendly_string()`

3. **Error handling for LLM failures**
   - What we know: LLM calls can fail (rate limits, invalid responses)
   - What's unclear: Retry strategy, fallback behavior
   - Recommendation: Implement exponential backoff retry, skip failing files with warning

## Sources

### Primary (HIGH confidence)
- [LangChain Python Documentation](https://context7.com/langchain_oss_python/) - LLM chain patterns, structured output
- Phase 01 RESEARCH.md - File discovery, code parsing, hash utilities
- Existing codebase patterns in `/code_monkey/agents/project_librarian/utilities/`

### Secondary (MEDIUM confidence)
- LangChain structured output examples - Pydantic integration patterns
- Python pathlib documentation - Directory traversal

### Tertiary (LOW confidence)
- Community patterns for hierarchical code summarization (needs validation during implementation)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Uses existing LangChain dependencies, Python standard library
- Architecture: HIGH - Patterns are well-established from Phase 01 and LangChain docs
- Pitfalls: HIGH - Common issues identified from similar incremental processing systems

**Research date:** 2026-02-01
**Valid until:** 2027-02-01 (LangChain APIs are stable, Phase 01 patterns are proven)
