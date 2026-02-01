# Phase 02: Project Mapper class - Context

**Gathered:** 2026-02-01
**Status:** Ready for planning

<domain>
## Phase Boundary

Build `ProjectMapper` class for project context file generation. The class orchestrates:
1. Full project scan OR targeted path updates
2. Hash-based change detection using Phase 01 utilities
3. LLM-powered file and module summarization
4. Hierarchical top-down directory processing
5. Project context tree generation

This infrastructure is called programmatically by the Lead Developer agent — it's not a user-facing feature.

</domain>

<decisions>
## Implementation Decisions

### LLM Chain Configuration
- Use LangChain LLM abstraction with direct calls for summarization
- Prompt style: Detailed technical summary, limited to 10 lines (configurable constant `MAX_SUMMARY_LINES`)
- Temperature: 0.0 for deterministic output
- Model: Any LangChain chat model supported
- Templates: 3 distinct templates (file, module, project)
- Use LangChain's structured output capabilities for output length enforcement

### Cache Serialization Format
- Structure: Hierarchical in `.codemonkey/`
  - `.codemonkey/file_hashes.json` — hash cache
  - `.codemonkey/code_context/{dir}/{file}.md` — per-file summaries
  - `.codemonkey/project_context.json` — project context
- Hash cache stores: absolute path, hash, mtime, file size (for debugging)
- Write strategy: Write to temp file, then rename (atomic)
- Cache keys: Relative paths to project root (portable)

### Error Handling Strategy
- LLM failures: Retry 3 times with exponential backoff, then fail entire operation
- Partial failures: Final save only (all or nothing)
- Syntax errors: Use predefined constant string indicating parse failure
  - Add `parse_error: bool` flag to ParsedCode (Phase 01 update required)
  - Store error indicator in file summary cache

### Output Format & Concurrency
- Project context tree: Indentation-based tree format
- File processing: Parallel within directories
- Subdirectory processing: Parallel (each submodule is independent)
- Rate limiting: Use LangChain's built-in mechanisms

### Class Structure & Separation of Responsibilities
- External API: Single file (`project_mapper.py`) for clean import
- Internal architecture: Composed classes with separated responsibilities
- Data structures: Pydantic models for validation and serialization
- Cache separation: `CacheManager` class handles all persistence
- Processing separation: `Summarizer` class handles all LLM interactions
- Traversal: `DirectoryProcessor` class handles file/directory processing
- Public methods:
  - `scan()` — full traversal with hash comparison, detects first run
  - `update(paths)` — update specific paths (hashes already known)
- Internal: Both methods delegate to shared `_run(changed_dirs)` for deterministic behavior

### Claude's Discretion
- Exact Pydantic model field definitions
- Specific retry backoff timing
- Progress logging verbosity
- Error message formatting

</decisions>

<specifics>
## Specific Ideas

- Cache structure uses `.md` extension for file summaries (not `.txt`)
- CacheManager handles all file I/O operations
- DirectoryProcessor uses parent module context when summarizing child modules
- Project context uses indentation-based tree format similar to `llm_friendly_string()` output

</specifics>

<deferred>
## Deferred Ideas

- Phase 01 update: Add `parse_error: bool` flag to ParsedCode NamedTuple (required for syntax error handling)
- Async/await support for concurrent processing (future enhancement)

</deferred>

---

*Phase: 02-project-mapper-class*
*Context gathered: 2026-02-01*
