# Codebase Structure

**Analysis Date:** 2026-01-31

## Directory Layout

```
code-monkey/
├── code_monkey/            # Main source package
│   ├── main.py             # Application entry point
│   ├── agents/             # Agent implementations
│   │   └── web_researcher/ # Web researcher agent
│   │       ├── web_researcher.py  # Agent implementation
│   │       └── tools.py           # Tool definitions
│   ├── models/             # LLM model factories
│   │   └── models.py
│   └── utils/              # Utility functions
│       ├── langchain_utils.py
│       └── json_utils.py
├── tests/                  # Test suite
│   ├── conftest.py               # Pytest configuration
│   ├── test_google_search.py     # Google search tests
│   └── test_web_researcher.py    # Web researcher tests
├── pyproject.toml          # Project configuration
├── .env                    # Environment variables
└── .planning/              # GSD planning documents
    └── codebase/
        ├── ARCHITECTURE.md
        └── STRUCTURE.md
```

## Directory Purposes

**code_monkey/:**
- Purpose: Main Python package containing all application code
- Contains: All source code organized by functional area
- Key files: `main.py`, `agents/`, `models/`, `utils/`

**code_monkey/agents/:**
- Purpose: Specialized agent implementations
- Contains: Agent classes, agent-specific tools
- Structure: Per-agent subdirectories
- Key files: `web_researcher/web_researcher.py`, `web_researcher/tools.py`

**code_monkey/models/:**
- Purpose: LLM model configuration and factory functions
- Contains: Model initialization utilities
- Key files: `models.py`

**code_monkey/utils/:**
- Purpose: Shared utility functions
- Contains: Helpers used across multiple modules
- Key files: `langchain_utils.py`, `json_utils.py`

**tests/:**
- Purpose: Test suite
- Contains: pytest test files
- Structure: Mirrors source structure loosely

**.planning/:**
- Purpose: GSD framework planning documents
- Contains: Architecture and structure analysis
- Generated: Yes (by /gsd:map-codebase)
- Committed: Yes

## Key File Locations

**Entry Points:**
- `code_monkey/main.py`: CLI entry point with `main()` function

**Configuration:**
- `pyproject.toml`: Project metadata, dependencies, pytest settings
- `.env`: Environment variables (API keys, not committed)

**Core Logic:**
- `code_monkey/agents/web_researcher/web_researcher.py`: Main agent implementation
- `code_monkey/agents/web_researcher/tools.py`: Tool definitions (Playwright, Google search)
- `code_monkey/models/models.py`: LLM factory functions

**Testing:**
- `tests/conftest.py`: Pytest configuration and fixtures
- `tests/test_web_researcher.py`: Agent integration tests
- `tests/test_google_search.py`: Google search tool tests

## Naming Conventions

**Files:**
- snake_case.py: All Python files use snake_case
- Agent files: `<agent_name>.py` (e.g., `web_researcher.py`)
- Tool files: `tools.py` (for agent-specific tools)
- Utility files: Descriptive names (e.g., `langchain_utils.py`)

**Directories:**
- lowercase: All directories use lowercase
- Agent directories: Singular agent name (e.g., `web_researcher`)
- Utility directories: Plural (e.g., `utils`, `models`)

**Classes:**
- PascalCase: All classes use PascalCase (e.g., `WebResearcher`, `PlaywrightTools`, `SearchResult`)

**Functions:**
- snake_case: All functions use snake_case (e.g., `get_openai_model()`, `google_search_tool`)

**Variables:**
- snake_case: Instance variables and local variables use snake_case
- Private variables: Leading underscore (e.g., `_playwright_tools`, `_agent`)

**Constants:**
- UPPER_SNAKE_CASE: `NUM_GOOGLE_RESULTS`

## Where to Add New Code

**New Agent:**
- Agent implementation: `code_monkey/agents/<agent_name>/<agent_name>.py`
- Agent tools: `code_monkey/agents/<agent_name>/tools.py`
- Tests: `tests/test_<agent_name>.py`

**New Utility:**
- Implementation: `code_monkey/utils/<utility_name>.py`
- Tests: `tests/test_<utility_name>.py`

**New LLM Provider:**
- Implementation: `code_monkey/models/models.py` (add factory function)
- Tests: Add to existing test files or create new test

**New Test:**
- Test file: `tests/test_<feature>.py`
- Use conftest.py for shared fixtures

## Special Directories

**.venv/:**
- Purpose: Python virtual environment (uv managed)
- Generated: Yes (by uv)
- Committed: No (in .gitignore)

**.pytest_cache/:**
- Purpose: pytest cache directory
- Generated: Yes (by pytest)
- Committed: No

**.planning/codebase/:**
- Purpose: GSD codebase analysis documents
- Generated: Yes (by /gsd:map-codebase)
- Committed: Yes

---

*Structure analysis: 2026-01-31*
