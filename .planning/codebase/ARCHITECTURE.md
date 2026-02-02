# Architecture

**Analysis Date:** 2026-02-02

## Pattern Overview

**Overall:** Multi-Agent LangGraph Orchestration with Hierarchical Cache-Based Context

**Key Characteristics:**
- LangChain/LangGraph-based multi-agent architecture for coding assistance
- Two specialized agents: Web Researcher (web tasks) and Project Librarian (code analysis)
- Incremental processing using hash-based change detection and hierarchical caching
- Generator-based progress tracking for long-running operations
- Clear separation between agent logic, data models, and utilities

## Layers

**Agents Layer (`code_monkey/agents/`):**
- Purpose: Contains specialized LangGraph agents for different tasks
- Location: `code_monkey/agents/`
- Contains: Agent implementations, tools, and agent-specific utilities
- Depends on: Models layer (data structures), Utils layer (common utilities)
- Used by: Entry point and external callers

**Models Layer (`code_monkey/models/`):**
- Purpose: Defines data models and LLM factory functions
- Location: `code_monkey/models/models.py`
- Contains: Pydantic BaseModels, LangChain model factory functions
- Depends on: External LLM libraries (langchain-openai, langchain-anthropic)
- Used by: Agents layer for LLM instances

**Utils Layer (`code_monkey/utils/`):**
- Purpose: Shared utilities across all agents
- Location: `code_monkey/utils/`
- Contains: TaskResult generic container, JSON utilities, LangChain helpers
- Depends on: Standard library only (minimized dependencies)
- Used by: All layers

## Data Flow

**Project Mapping Flow:**

1. `ProjectMapper.scan()` is called with project root path
2. `_compute_file_hashes()` discovers Python files and computes SHA-256 hashes
3. `CacheManager.load_hashes()` loads cached hashes from `.codemonkey/file_hashes.json`
4. Changed files are detected via hash comparison
5. `DirectoryProcessor.process_changed_directories()` processes changed directories top-down
6. Each directory:
   - `discover_python_files()` finds Python files in directory
   - `parse_python_code()` extracts AST structure (classes, functions, imports)
   - `Summarizer.summarize_file()` generates LLM-based file summary
   - `Summarizer.summarize_module()` generates module-level summary with parent context
   - Cache saves file/module summaries to `.codemonkey/code_context/`
7. `Summarizer.generate_project_context()` creates project-wide context
8. `ProjectMapperResult` yielded with progress tracking via `TaskResult`

**Web Research Flow:**

1. `WebResearcher.create()` initializes Playwright browser and LangChain agent
2. `WebResearcher.search()` invokes agent with query
3. Agent uses `google_search_tool` and Playwright tools
4. `SearchResult` returned with result and thread_id for session continuity

**State Management:**
- Generator functions yield `TaskResult[T]` with `progress` and `progress_max` for progress tracking
- Cached state stored in `.codemonkey/` directory hierarchy
- Agent state persisted via LangGraph checkpointer (InMemorySaver for Web Researcher)

## Key Abstractions

**TaskResult[T] (`code_monkey/utils/task_result.py`):**
- Purpose: Generic container for task results with progress tracking
- Examples: `TaskResult[ProjectMapperResult]`, `TaskResult[dict]`
- Pattern: Generic dataclass with `result`, `progress`, `progress_max` properties

**CacheManager (`code_monkey/agents/project_librarian/cache_manager.py`):**
- Purpose: Atomic cache reads/writes for project mapping data
- Cache structure:
  - `.codemonkey/file_hashes.json` - file hash cache
  - `.codemonkey/code_context/{rel_path}.md` - per-file summaries
  - `.codemonkey/project_context.json` - project-wide context
- Pattern: Temp file + rename for atomic writes

**Summarizer (`code_monkey/agents/project_librarian/summarizer.py`):**
- Purpose: LLM-based file, module, and project summarization
- Pattern: LangChain RunnableSequence with exponential backoff retry
- Three chain types: file, module, project summarization

**Code Parser (`code_monkey/agents/project_librarian/utils/code_parser.py`):**
- Purpose: AST-based code structure extraction
- Pattern: Visitor pattern using Python ast module
- Extracts: classes, functions, methods, imports in LLM-friendly format

## Entry Points

**main.py (`code_monkey/main.py`):**
- Location: `code_monkey/main.py`
- Triggers: `python main.py` or `uv run python main.py`
- Responsibilities: Initializes logging, loads .env, calls `main()`

**Test Configuration (`tests/conftest.py`):**
- Location: `tests/conftest.py`
- Provides fixtures for template-based testing
- Creates isolated working copies of mock projects

## Error Handling

**Strategy:** Exponential backoff with retries

**Patterns:**
- `Summarizer._summarize_with_retry()`: Retries up to MAX_RETRIES (3) with exponential backoff
- `CacheManager`: Returns empty/default values on cache read failures
- `parse_python_code()`: Returns empty `ParsedCode` on syntax errors
- Logging via Python standard `logging` module

## Cross-Cutting Concerns

**Logging:** Python standard `logging` with basic configuration in `main.py`

**Validation:** Pydantic BaseModel for structured data (e.g., `SearchResult`)

**Authentication:** Environment variables loaded via `dotenv` for API keys

---

*Architecture analysis: 2026-02-02*
