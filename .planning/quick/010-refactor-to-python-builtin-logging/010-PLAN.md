# Quick Plan: Refactor to Python Builtin Logging

**Task:** Refactor the whole project to use Python builtin logging instead of "print" statements.

## Tasks

### Task 1: Create logging config in code_monkey/main.py
**File:** `code_monkey/main.py`

Add basic logging configuration at the module level:
- Import logging module
- Configure basic logging with a standard format
- Create a logger for the main module
- Replace print statements with logging calls

### Task 2: Create logging config in tests/conftest.py
**File:** `tests/conftest.py`

Add basic logging configuration:
- Import logging module
- Configure basic logging with a standard format
- Replace print statements with logging calls

### Task 3: Replace print with logging in all other project .py files
**Files:** All .py files in the project (excluding main.py and conftest.py which are handled above)

For each .py file:
- Replace print() calls with appropriate logging calls (logging.info, logging.debug, logging.warning, etc.)
- Add `import logging` if not present
- Create a module-level logger: `logger = logging.getLogger(__name__)`
- Use logger.info/debug/warning/error instead of print

**Files to process:**
- code_monkey/agents/project_librarian/project_mapper.py
- code_monkey/agents/project_librarian/summarizer.py
- code_monkey/agents/project_librarian/cache.py
- code_monkey/agents/project_librarian/file_discovery.py
- code_monkey/agents/project_librarian/code_parser.py
- code_monkey/agents/project_librarian/hash_utils.py
- code_monkey/agents/project_librarian/__init__.py
- code_monkey/agents/__init__.py
- code_monkey/__init__.py
- tests/agents/project_librarian/test_project_mapper_integration.py
- tests/agents/project_librarian/test_project_mapper_unit.py
- tests/testing_utils.py
- Any other .py files in the project

### Task 4: Run integration test to verify logging works
**Command:** `uv run pytest tests/agents/project_librarian/test_project_mapper_integration.py -v`

Verify:
- Tests pass
- Logging output is visible during test execution
- Progress bars and log messages appear correctly

## Execution

Execute tasks 1-4 in order. Task 3 involves processing multiple files - subagents can work in parallel on different files as long as they don't conflict.
