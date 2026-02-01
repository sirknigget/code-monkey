# Phase 02 Plan 01: ProjectMapper Class Summary

## Brief Description

Built the `ProjectMapper` class that orchestrates file discovery, hash-based change detection, LLM summarization, and hierarchical context generation for the Project Librarian agent. Enables efficient incremental updates to project context by only reprocessing modified files.

## File Structure Created

```
code_monkey/agents/project_librarian/
├── __init__.py                    # Public exports: ProjectMapper + utilities
└── project_mapper.py              # Main implementation (830 lines)
```

## Key Classes and Methods

### FileSummary & ModuleSummary (NamedTuple models)
- `FileSummary(filepath: Path, summary: str)` - Single file summary
- `ModuleSummary(directory: Path, files: list[FileSummary], module_summary: str, parent_summary: str | None)` - Module-level summary

### CacheManager
- `__init__(root: Path)` - Initializes cache at root/.codemonkey
- `load_hashes() / save_hashes()` - Atomic JSON hash cache management
- `save_file_summary() / load_file_summary()` - Per-file .md summaries
- `save_module_summary() / load_module_summary()` - Per-module _module.md
- `save_project_context() / load_project_context()` - Project-wide context

### Summarizer
- Constants: `MAX_SUMMARY_LINES=10`, `MAX_RETRIES=3`, `BACKOFF_BASE=2.0`, `INITIAL_DELAY=1.0`
- `_summarize_with_retry()` - Exponential backoff retry logic
- `summarize_file()` - File-level LLM summarization
- `summarize_module()` - Module-level summarization with parent context
- `generate_project_context()` - Indentation tree format project overview

### DirectoryProcessor
- `_get_all_directories()` - Discover all directories with Python files
- `_process_directory_top_down()` - Recursive processing with parent context propagation
- `process_changed_directories()` - Process only changed directories

### ProjectMapper (Main API)
- `__init__(root, llm, cache_dir=None)` - Initialize with LLM
- `scan()` - Full project scan, returns dict[Path, str] of module summaries
- `update(paths)` - Update specific paths, returns module summaries
- `get_project_context()` - Returns cached or generated indentation tree context

## Implementation Details

- **Hash-based change detection**: Uses Phase 01 `compute_file_hash()` to detect modified files
- **Atomic cache writes**: Temp file + rename pattern prevents cache corruption
- **Parallel file processing**: `ThreadPoolExecutor` for concurrent file summarization
- **Parent context propagation**: Child modules receive parent module summaries during processing
- **3 distinct LLM templates**: File summary (2-3 sentences), module summary (3-5 sentences), project context (indentation tree)
- **Retry logic**: 3 attempts with exponential backoff (2.0x base, 1.0s initial delay)

## Notes for Phase 03

Phase 03 should integrate ProjectMapper into the Project Librarian agent workflow:

1. **Lead Developer Agent Integration**: ProjectMapper.scan() will be called when the agent needs project context, ProjectMapper.update() for incremental changes
2. **get_project_context()**: Returns the indentation tree format for LLM context injection
3. **Module summaries dict**: `scan()` returns `dict[Path, str]` - agent can query specific module summaries by directory path
4. **Cache location**: `.codemonkey/` directory - ensure it's gitignored (already in .gitignore patterns from Phase 01)
5. **LLM Configuration**: ProjectMapper expects a LangChain `BaseChatModel` - any provider (Anthropic, OpenAI, etc.) works

## Deviations from Plan

None - plan executed exactly as written.
