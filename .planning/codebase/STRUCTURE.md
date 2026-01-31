# Codebase Structure

**Analysis Date:** 2026-01-31

## Directory Layout

```
code-monkey/
├── src/
│   ├── main.py              # Application entry point
│   ├── agents/
│   │   └── web_researcher/
│   │       ├── web_researcher.py  # Agent implementation
│   │       └── tools.py           # Tool definitions
│   └── utils/
│       └── json_utils.py          # Helper utilities
├── tests/
│   ├── conftest.py               # Pytest configuration
│   ├── test_google_search.py     # Google search tests
│   ├── test_playwright_tools.py  # Playwright tests
│   └── test_web_researcher.py    # Web researcher tests
├── pyproject.toml                # Project configuration
└── .env                          # Environment variables
```

## Directory Purposes

**src/**:
- Purpose: All application source code
- Contains: Python modules, packages
- Key files: `main.py`, `__init__.py` (implied)

**src/agents/**:
- Purpose: Specialized agent implementations
- Contains: Agent classes, agent-specific tools
- Structure: Per-agent subdirectories

**src/agents/web_researcher/**:
- Purpose: Web research agent implementation
- Contains: Agent logic, browser tools, search tools
- Key files: `web_researcher.py`, `tools.py`

**src/utils/**:
- Purpose: Shared utility functions
- Contains: Helpers used across multiple modules
- Key files: `json_utils.py`

**tests/**:
- Purpose: Test suite
- Contains: pytest test files
- Structure: Mirrors source structure loosely

## Key File Locations

**Entry Points:**
- `src/main.py`: CLI entry point with main() function

**Configuration:**
- `pyproject.toml`: Project metadata and dependencies
- `.env`: Environment variables (not committed)

**Core Logic:**
- `src/agents/web_researcher/web_researcher.py`: Main agent implementation
- `src/agents/web_researcher/tools.py`: Tool definitions

**Testing:**
- `tests/conftest.py`: Pytest configuration and fixtures
- `tests/test_web_researcher.py`: Agent integration tests

## Naming Conventions

**Files:**
- snake_case.py: All Python files use snake_case
- Agent files: `<agent_name>.py` (e.g., `web_researcher.py`)
- Tool files: `tools.py` (for agent-specific tools)

**Directories:**
- lowercase: All directories use lowercase
- Agent directories: Singular agent name (e.g., `web_researcher`)
- Utility directories: Plural or descriptive (e.g., `utils`)

**Classes:**
- PascalCase: All classes use PascalCase (e.g., `WebResearcher`, `PlaywrightTools`)

**Functions:**
- snake_case: All functions use snake_case (e.g., `google_search_tool`)

**Variables:**
- snake_case: Instance variables and local variables use snake_case
- Private variables: Leading underscore (e.g., `_playwright_tools`)

## Where to Add New Code

**New Agent:**
- Agent implementation: `src/agents/<agent_name>/<agent_name>.py`
- Agent tools: `src/agents/<agent_name>/tools.py`
- Tests: `tests/test_<agent_name>.py`

**New Utility:**
- Implementation: `src/utils/<utility_name>.py`

**New Test:**
- Test file: `tests/test_<feature>.py`
- Use conftest.py for shared fixtures

## Special Directories

**.venv/**:
- Purpose: Python virtual environment (uv managed)
- Generated: Yes (by uv)
- Committed: No (in .gitignore)

**.pytest_cache/**:
- Purpose: pytest cache directory
- Generated: Yes (by pytest)
- Committed: No

**.git/**:
- Purpose: Git repository data
- Generated: Yes (by git)
- Committed: No

---

*Structure analysis: 2026-01-31*
