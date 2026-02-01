---
phase: 02-project-mapper-class
plan: "01"
type: execute
wave: 1
depends_on: []
files_modified:
  - "code_monkey/agents/project_librarian/project_mapper.py"
autonomous: true
user_setup: []

must_haves:
  truths:
    - "ProjectMapper.scan() discovers all Python files, checks hashes, processes only changed files"
    - "ProjectMapper.update(paths) processes specific paths with parent module context"
    - "CacheManager handles atomic writes to .codemonkey/file_hashes.json and code_context/"
    - "Summarizer generates file/module/project summaries with retry logic"
    - "DirectoryProcessor traverses directories top-down, parallelizing file processing"
    - "Project context tree uses indentation format, showing module hierarchy"
  artifacts:
    - path: "code_monkey/agents/project_librarian/project_mapper.py"
      provides: "ProjectMapper class with scan(), update(), and internal composed classes"
      min_lines: 200
    - path: "code_monkey/agents/project_librarian/__init__.py"
      provides: "Public exports of ProjectMapper"
      exports: ["ProjectMapper"]
  key_links:
    - from: "ProjectMapper.scan()"
      to: "CacheManager.load_hashes()"
      via: "hash-based change detection"
    - from: "DirectoryProcessor"
      to: "Summarizer.summarize_file()"
      via: "LLM file summarization"
    - from: "DirectoryProcessor"
      to: "Summarizer.summarize_module()"
      via: "parent module context propagation"
    - from: "ProjectMapper"
      to: "Summarizer.get_project_context()"
      via: "indentation tree format output"
---

<objective>
Build the `ProjectMapper` class that orchestrates file discovery, hash-based change detection, LLM summarization, and hierarchical context generation for the Project Librarian agent.

Purpose: This class enables efficient incremental updates to project context by only reprocessing modified files. It's called programmatically by the Lead Developer agent.

Output: `project_mapper.py` containing ProjectMapper, CacheManager, Summarizer, and DirectoryProcessor classes with Pydantic models.
</objective>

<execution_context>
@/Users/omergilad/.claude/get-shit-done/workflows/execute-plan.md
@/Users/omergilad/workspace/AI/code-monkey/CLAUDE.md
</execution_context>

<context>
@/Users/omergilad/workspace/AI/code-monkey/.planning/STATE.md
@/Users/omergilad/workspace/AI/code-monkey/.planning/phases/02-project-mapper-class/02-CONTEXT.md
@/Users/omergilad/workspace/AI/code-monkey/.planning/phases/02-project-mapper-class/02-RESEARCH.md

# Phase 01 utilities (already exist)
@/Users/omergilad/workspace/AI/code-monkey/code_monkey/agents/project_librarian/utilities/__init__.py
@/Users/omergilad/workspace/AI/code-monkey/code_monkey/agents/project_librarian/utilities/file_discovery.py
@/Users/omergilad/workspace/AI/code-monkey/code_monkey/agents/project_librarian/utilities/code_parser.py
@/Users/omergilad/workspace/AI/code-monkey/code_monkey/agents/project_librarian/utilities/hash_utils.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create Pydantic models and CacheManager class</name>
  <files>code_monkey/agents/project_librarian/project_mapper.py (lines 1-120)</files>
  <action>
    Create the first section of `project_mapper.py` containing:

    1. **Pydantic models** at module top (before any classes):
       - `FileSummary(NamedTuple or pydantic model)`: filepath (Path), summary (str)
       - `ModuleSummary(NamedTuple or pydantic model)`: directory (Path), files (list[FileSummary]), module_summary (str), parent_summary (str | None)

    2. **CacheManager class** with methods:
       - `__init__(self, root: Path)` - stores root, sets cache_dir to root/.codemonkey
       - `load_hashes(self) -> dict[str, str]` - loads from .codemonkey/file_hashes.json, returns empty dict if missing
       - `save_hashes(self, hashes: dict[str, str])` - atomic write: write to temp file, then rename to .codemonkey/file_hashes.json
       - `get_file_summary_path(self, filepath: Path) -> Path` - returns .codemonkey/code_context/{rel_path}.md
       - `save_file_summary(self, filepath: Path, summary: str)` - creates parent dirs, atomic write
       - `load_file_summary(self, filepath: Path) -> str | None` - returns None if missing
       - `get_module_summary_path(self, directory: Path) -> Path` - returns .codemonkey/code_context/{rel_dir}/_module.md
       - `save_module_summary(self, directory: Path, summary: str)` - atomic write
       - `load_module_summary(self, directory: Path) -> str | None`
       - `save_project_context(self, context: str)` - writes to .codemonkey/project_context.json

    Use imports: `json`, `tempfile`, `pathlib.Path`, `pydantic.BaseModel`

    Cache file structure:
    - `.codemonkey/file_hashes.json` - {"/absolute/path": "hash", ...}
    - `.codemonkey/code_context/{rel_path}.md` - per-file summaries
    - `.codemonkey/project_context.json` - project-wide context
  </action>
  <verify>
    `uv run python -c "from code_monkey.agents.project_librarian.project_mapper import CacheManager; cm = CacheManager(Path('.')); print('CacheManager imports OK')"`
  </verify>
  <done>
    Pydantic models defined, CacheManager handles atomic cache reads/writes
  </done>
</task>

<task type="auto">
  <name>Task 2: Create Summarizer class with LLM chains and retry logic</name>
  <files>code_monkey/agents/project_librarian/project_mapper.py (lines 121-250)</files>
  <action>
    Create the `Summarizer` class after CacheManager:

    Constants at class level:
    - `MAX_SUMMARY_LINES = 10` - limit for all summaries
    - `MAX_RETRIES = 3` - retry count for LLM failures
    - `BACKOFF_BASE = 2.0` - exponential backoff multiplier
    - `INITIAL_DELAY = 1.0` - initial delay in seconds

    Class `Summarizer`:
    - `__init__(self, llm: BaseChatModel)` - stores llm, creates 3 chain instances
    - `_create_file_summary_chain(self) -> Chain` - LangChain chain for file summaries
    - `_create_module_summary_chain(self) -> Chain` - LangChain chain for module summaries
    - `_create_project_summary_chain(self) -> Chain` - LangChain chain for project context

    Prompt TEMPLATES (3 distinct templates):
    1. **File summary template** - concise purpose, 2-3 sentences, mentions key classes/functions
    2. **Module summary template** - combines file summaries, shows relationships, 3-5 sentences
    3. **Project summary template** - indentation tree format, shows directory hierarchy

    Methods:
    - `_summarize_with_retry(self, chain: Chain, input: dict, max_lines: int) -> str` - retry 3x with exponential backoff, raises on final failure
    - `summarize_file(self, filepath: Path, structure: str, parent_context: str | None = None) -> str` - uses file chain
    - `summarize_module(self, directory: Path, file_summaries: list[str], parent_context: str | None = None) -> str` - uses module chain
    - `generate_project_context(self, module_summaries: dict[Path, str]) -> str` - uses project chain, indentation tree format

    Import: `from langchain_core.language_models import BaseChatModel`, `from langchain_core.output_parsers import StrOutputParser`, `from langchain_core.prompts import ChatPromptTemplate`, `from langchain_core.runnables import RunnableSequence`
  </action>
  <verify>
    `uv run python -c "from code_monkey.agents.project_librarian.project_mapper import Summarizer; print('Summarizer class OK')"`
  </verify>
  <done>
    Summarizer class with 3 templates, retry logic, LLM chain abstraction
  </done>
</task>

<task type="auto">
  <name>Task 3: Create DirectoryProcessor and ProjectMapper main class</name>
  <files>code_monkey/agents/project_librarian/project_mapper.py (lines 251-end)</files>
  <action>
    Create `DirectoryProcessor` and `ProjectMapper` classes:

    **DirectoryProcessor class** (internal):
    - `__init__(self, root: Path, cache: CacheManager, summarizer: Summarizer)` - stores dependencies
    - `_get_all_directories(self) -> list[Path]` - sorted list of all directories containing Python files
    - `_get_files_in_directory(self, directory: Path) -> list[Path]` - sorted list of .py files
    - `_process_directory_top_down(self, directory: Path, parent_summary: str | None = None) -> str` - processes directory, returns module summary for parent
      - Step 1: Get files, parallelize file summarization (concurrent.futures.ThreadPoolExecutor)
      - Step 2: Generate module summary with parent context
      - Step 3: Save to cache
      - Step 4: Recursively process child directories (in order)
      - Returns module summary for parent context
    - `process_changed_directories(self, changed_dirs: set[Path]) -> dict[Path, str]` - processes only changed dirs, returns module summaries

    **ProjectMapper class** (main, public API):
    - `__init__(self, root: Path, llm: BaseChatModel, cache_dir: Path | None = None)` - initializes all internal classes
    - `_run(self, changed_dirs: set[Path] | None = None)` - internal method shared by scan() and update()
      - Loads cached hashes
      - If changed_dirs provided: process only those directories
      - If None: compute changed files via hash comparison, derive changed_dirs
      - Calls DirectoryProcessor.process_changed_directories()
      - Generates project context from module summaries
      - Saves project context to cache
    - `scan(self) -> dict[Path, str]` - full project scan, returns module summaries dict
      - Calls _run() with None, returns results
    - `update(self, paths: list[Path]) -> dict[Path, str]` - update specific paths
      - Computes changed directories from paths
      - Calls _run(changed_dirs)
      - Returns results
    - `get_project_context(self) -> str` - returns cached or generates project context

    Public exports in __all__: ["ProjectMapper"]

    Constants: MAX_FILES_PER_SUMMARY = 20 (for chunking large directories)
  </action>
  <verify>
    `uv run python -c "from code_monkey.agents.project_librarian import ProjectMapper; print('ProjectMapper imports OK')"`
  </verify>
  <done>
    ProjectMapper class with scan(), update() methods, DirectoryProcessor with top-down traversal
  </done>
</task>

</tasks>

<verification>
1. All imports resolve without errors
2. CacheManager handles atomic writes correctly
3. Summarizer chains use 3 distinct prompt templates
4. Retry logic implements exponential backoff
5. DirectoryProcessor processes directories top-down
6. Parallel file processing within directories
7. ProjectMapper.scan() and update() have consistent behavior via _run()
</verification>

<success_criteria>
- ProjectMapper class instantiated with root Path and LLM
- scan() returns dict[Path, str] of module summaries
- update(paths) processes only specified paths
- Hash-based change detection uses Phase 01 compute_file_hash()
- Parent module context passed during child summarization
- Project context uses indentation tree format
- Atomic writes prevent cache corruption
- Retry 3x with exponential backoff for LLM failures
</success_criteria>

<output>
After completion, create `.planning/phases/02-project-mapper-class/02-01-SUMMARY.md` with:
- Brief description of what was built
- File structure created
- Key class/method summary
- Notes for Phase 03 (if any)
</output>
