# Codebase Structure

**Analysis Date:** 2026-02-02

## Directory Layout

```
code-monkey/
├── code_monkey/               # Main application source
│   ├── main.py                # Entry point
│   ├── agents/                # Agent implementations
│   │   ├── project_librarian/ # Project analysis agent
│   │   │   ├── project_mapper.py
│   │   │   ├── directory_processor.py
│   │   │   ├── cache_manager.py
│   │   │   ├── summarizer.py
│   │   │   ├── models.py
│   │   │   ├── __init__.py
│   │   │   └── utils/         # Agent-specific utilities
│   │   │       ├── __init__.py
│   │   │       ├── code_parser.py
│   │   │       ├── file_discovery.py
│   │   │       └── hash_utils.py
│   │   └── web_researcher/    # Web research agent
│   │       ├── web_researcher.py
│   │       └── tools.py
│   ├── models/
│   │   └── models.py          # LLM factories, data models
│   └── utils/
│       ├── __init__.py
│       ├── task_result.py
│       ├── json_utils.py
│       └── langchain_utils.py
├── tests/                     # Test suite
│   ├── conftest.py
│   ├── testing_utils.py
│   └── agents/
│       ├── project_librarian/
│       │   └── test_*.py
│       │   └── utils/
│       │       └── test_*.py
│       └── web_researcher/
│           └── test_*.py
├── mock_project/              # Test fixtures
│   └── template/
├── .planning/codebase/        # Generated documentation
├── pyproject.toml
└── CLAUDE.md
```

## Directory Purposes

**code_monkey/ (`code_monkey/`):**
- Purpose: Main application source code
- Contains: All Python modules and packages
- Key files: `main.py` (entry point)

**code_monkey/agents/ (`code_monkey/agents/`):**
- Purpose: Agent implementations following LangGraph patterns
- Contains: Agent classes, tools, and agent-specific logic
- Key files: `project_mapper.py`, `web_researcher.py`, `tools.py`

**code_monkey/agents/project_librarian/ (`code_monkey/agents/project_librarian/`):**
- Purpose: Project analysis agent with caching and summarization
- Contains: ProjectMapper, DirectoryProcessor, CacheManager, Summarizer
- Key files: `project_mapper.py`, `directory_processor.py`, `cache_manager.py`, `summarizer.py`

**code_monkey/agents/project_librarian/utils/ (`code_monkey/agents/project_librarian/utils/`):**
- Purpose: Utilities specific to project librarian
- Contains: Code parsing, file discovery, hash computation
- Key files: `code_parser.py`, `file_discovery.py`, `hash_utils.py`

**code_monkey/agents/web_researcher/ (`code_monkey/agents/web_researcher/`):**
- Purpose: Web research agent with Playwright integration
- Contains: WebResearcher class, web tools
- Key files: `web_researcher.py`, `tools.py`

**code_monkey/models/ (`code_monkey/models/`):**
- Purpose: Data models and LLM factory functions
- Contains: Model definitions, ChatOpenAI/ChatAnthropic factories
- Key files: `models.py`

**code_monkey/utils/ (`code_monkey/utils/`):**
- Purpose: Shared utilities across all agents
- Contains: TaskResult, JSON helpers, LangChain helpers
- Key files: `task_result.py`, `json_utils.py`, `langchain_utils.py`

**tests/ (`tests/`):**
- Purpose: Test suite with pytest
- Contains: Unit tests, integration tests, fixtures
- Structure mirrors source structure under `agents/`

## Key File Locations

**Entry Points:**
- `/Users/omergilad/workspace/AI/code-monkey/code_monkey/main.py`: Application entry point

**Configuration:**
- `/Users/omergilad/workspace/AI/code-monkey/pyproject.toml`: Project configuration, dependencies, pytest settings

**Core Logic:**
- `/Users/omergilad/workspace/AI/code-monkey/code_monkey/agents/project_librarian/project_mapper.py`: Main project mapping orchestrator
- `/Users/omergilad/workspace/AI/code-monkey/code_monkey/agents/project_librarian/directory_processor.py`: Directory traversal and processing
- `/Users/omergilad/workspace/AI/code-monkey/code_monkey/agents/project_librarian/cache_manager.py`: Cache management
- `/Users/omergilad/workspace/AI/code-monkey/code_monkey/agents/web_researcher/web_researcher.py`: Web research agent

**Testing:**
- `/Users/omergilad/workspace/AI/code-monkey/tests/conftest.py`: Pytest fixtures
- `/Users/omergilad/workspace/AI/code-monkey/tests/agents/project_librarian/test_project_mapper.py`: Project mapper tests

## Naming Conventions

**Files:**
- Python modules: `lowercase_snake_case.py` (e.g., `cache_manager.py`, `hash_utils.py`)
- Test files: `test_<module_name>.py` (e.g., `test_project_mapper.py`)
- Utility modules: `lowercase_snake_case.py` (e.g., `code_parser.py`)

**Directories:**
- Package directories: `lowercase_snake_case` (e.g., `project_librarian`, `web_researcher`)
- Test subdirectories mirror source: `tests/agents/<agent_name>/`

**Classes:**
- PascalCase: `ProjectMapper`, `CacheManager`, `Summarizer`, `WebResearcher`
- NamedTuple models: PascalCase ending in Summary (e.g., `FileSummary`, `ModuleSummary`)

**Functions:**
- lowercase_snake_case: `compute_file_hash()`, `discover_python_files()`, `parse_python_code()`

## Where to Add New Code

**New Agent:**
- Primary code: `code_monkey/agents/<agent_name>/`
- Tools: `code_monkey/agents/<agent_name>/tools.py`
- Tests: `tests/agents/<agent_name>/`

**New Utility:**
- Shared utilities: `code_monkey/utils/`
- Agent-specific utilities: `code_monkey/agents/<agent>/utils/`

**New Data Model:**
- Agent-specific models: `code_monkey/agents/<agent>/models.py`
- Shared models: `code_monkey/models/models.py`

**New Test:**
- Unit tests: `tests/agents/<agent>/test_<component>.py`
- Integration tests: `tests/agents/<agent>/test_<feature>_integration.py`

## Special Directories

**.codemonkey/ (generated):**
- Purpose: Cache directory for file hashes and code summaries
- Location: `<project_root>/.codemonkey/`
- Generated: Yes (created by ProjectMapper)
- Committed: No (.gitignored)

**.planning/codebase/ (generated):**
- Purpose: Generated architecture documentation
- Location: `.planning/codebase/`
- Generated: Yes (by /gsd:map-codebase)
- Committed: Yes (version controlled)

**mock_project/:**
- Purpose: Template projects for testing
- Location: `mock_project/template/`
- Generated: No
- Committed: Yes (test fixtures)

---

*Structure analysis: 2026-02-02*
