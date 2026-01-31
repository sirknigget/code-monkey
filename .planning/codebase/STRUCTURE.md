# Codebase Structure

**Analysis Date:** 2026-01-31

## Directory Layout

```
code-monkey/
├── code_monkey/              # Main source code
│   ├── agents/               # Agent implementations
│   │   ├── web_researcher/   # Web research agent
│   │   └── project_librarian/ # Project analysis agent
│   │       └── utilities/    # File system utilities
│   ├── models/               # LLM model configuration
│   ├── utils/                # Shared utilities
│   └── main.py               # Entry point
├── tests/                    # Test suite
│   └── agents/               # Agent tests (mirrors source structure)
│       ├── web_researcher/
│       └── project_librarian/
├── .planning/codebase/       # Architecture documentation
├── pyproject.toml            # Project configuration
├── .env                      # Environment variables
└── uv.lock                   # Dependency lockfile
```

## Directory Purposes

**`code_monkey/`:**
- Purpose: Main source code package
- Contains: All application code
- Key files: `main.py` (entry point)

**`code_monkey/agents/`:**
- Purpose: Agent implementations
- Contains: Specialized agents with tools
- Key files:
  - `web_researcher/web_researcher.py` (WebResearcher agent)
  - `web_researcher/tools.py` (Playwright + Google search tools)

**`code_monkey/agents/project_librarian/utilities/`:**
- Purpose: File system and code analysis utilities
- Contains:
  - `file_discovery.py` (Python file discovery)
  - `hash_utils.py` (SHA-256 hashing)
  - `code_parser.py` (AST code extraction)
  - `__init__.py` (barrel exports)

**`code_monkey/models/`:**
- Purpose: LLM model factory functions
- Contains: `models.py` (get_openai_model, get_minimax_model)

**`code_monkey/utils/`:**
- Purpose: Shared utility functions
- Contains:
  - `langchain_utils.py` (LangChain helpers)
  - `json_utils.py` (JSON serialization)

**`tests/`:**
- Purpose: Test suite
- Contains: Unit and integration tests
- Structure: Mirrors agent directory structure

**`.planning/codebase/`:**
- Purpose: Architecture and convention documentation
- Contains: ARCHITECTURE.md, STRUCTURE.md, CONVENTIONS.md, etc.

## Key File Locations

**Entry Points:**
- `/Users/omergilad/workspace/AI/code-monkey/main.py`: Application bootstrap, loads .env

**Configuration:**
- `/Users/omergilad/workspace/AI/code-monkey/pyproject.toml`: Project metadata, dependencies, pytest config

**Core Logic:**
- `/Users/omergilad/workspace/AI/code-monkey/code_monkey/agents/web_researcher/web_researcher.py`: WebResearcher agent
- `/Users/omergilad/workspace/AI/code-monkey/code_monkey/agents/project_librarian/utilities/`: Project analysis utilities

**Testing:**
- `/Users/omergilad/workspace/AI/code-monkey/tests/agents/project_librarian/`: Project Librarian tests
- `/Users/omergilad/workspace/AI/code-monkey/tests/agents/web_researcher/`: Web Researcher tests

## Naming Conventions

**Files:**
- snake_case.py: All Python files use lowercase with underscores
- Example: `file_discovery.py`, `hash_utils.py`, `langchain_utils.py`

**Directories:**
- snake_case: All directories use lowercase with underscores
- Example: `code_monkey`, `web_researcher`, `project_librarian`

**Classes:**
- PascalCase: All classes use capitalized words
- Example: `WebResearcher`, `PlaywrightTools`, `SearchResult`, `CodeExtractor`

**Functions:**
- snake_case: All functions use lowercase with underscores
- Example: `discover_python_files`, `compute_file_hash`, `parse_python_code`

**Variables:**
- snake_case: Local variables and parameters
- Example: `playwright_tools`, `thread_id`, `root_path`

**Constants:**
- UPPER_SNAKE_CASE: Module-level constants
- Example: `EXCLUDED_DIRS`, `NUM_GOOGLE_RESULTS`

**Types:**
- PascalCase: NamedTuple and Pydantic models
- Example: `ParsedCode`, `SearchResult`

**Imports:**
- Absolute imports from package root: `from code_monkey.agents.web_researcher.tools import ...`

## Where to Add New Code

**New Agent:**
- Primary code: `code_monkey/agents/<agent_name>/`
- Tests: `tests/agents/<agent_name>/`
- Initialize module with `__init__.py` if needed

**New Utility for Existing Agent:**
- Implementation: `code_monkey/agents/<agent>/<utility_name>.py`
- Export from: `code_monkey/agents/<agent>/__init__.py` (create if needed)
- Tests: `tests/agents/<agent>/test_<utility_name>.py`

**New Shared Utility:**
- Implementation: `code_monkey/utils/<utility_name>.py`
- Export from: `code_monkey/utils/__init__.py` (create if needed)

**New Model Function:**
- Implementation: `code_monkey/models/models.py`
- Add factory function returning appropriate LangChain model

**New Test:**
- Unit tests: `tests/agents/<agent>/test_<module>.py`
- Pattern: Follow existing test file structure (imports, test class/functions)

## Special Directories

**`.planning/codebase/`:**
- Purpose: Architecture and convention documentation
- Generated: Yes (by /gsd:map-codebase)
- Committed: Yes (version controlled)

**`.pytest_cache/`:**
- Purpose: Pytest cache directory
- Generated: Yes
- Committed: No (.gitignored)

**`.venv/`:**
- Purpose: Virtual environment
- Generated: Yes (by uv)
- Committed: No (.gitignored)

**`.git/`:**
- Purpose: Git repository data
- Generated: Yes (by git init)
- Committed: No

---

*Structure analysis: 2026-01-31*
