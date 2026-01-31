# Codebase Concerns

**Analysis Date:** 2026-01-31

## Critical Issues

### Import Path Mismatch in Test Files

**Issue:** Test files use outdated `src/` import paths that do not exist.

**Files:**

- `/Users/omergilad/workspace/AI/code-monkey/tests/test_google_search.py`
- `/Users/omergilad/workspace/AI/code-monkey/tests/test_playwright_tools.py`

**Problem:**

```python
# test_google_search.py - Line 4
from src.agents.web_researcher.tools import google_search_tool, NUM_GOOGLE_RESULTS

# test_playwright_tools.py - Lines 4-5
from src.agents.web_researcher.tools import PlaywrightTools
from src.utils.json_utils import dump_object
```

The actual module location is `code_monkey/`, not `src/`. The `src/` directory does not exist.

**Impact:** These tests will fail with `ModuleNotFoundError` when run.

**Fix approach:** Update import statements to use `code_monkey.` prefix:

```python
from code_monkey.agents.web_researcher.tools import google_search_tool
from code_monkey.utils.json_utils import dump_object
```

## Tech Debt

### Async Code in Synchronous Constructor

**Issue:** `WebResearcher.__init__` runs async `PlaywrightTools.initialize()` synchronously using `run_until_complete()` in a constructor

**File:** `/Users/omergilad/workspace/AI/code-monkey/code_monkey/agents/web_researcher/web_researcher.py`

**Impact:** This anti-pattern can cause issues in certain async contexts and makes the class harder to use in async codebases

**Fix approach:** Make `__init__` async, or use a factory pattern with async initialization

---

### Async Teardown in Synchronous Context

**Issue:** `WebResearcher.teardown()` uses the same async-in-sync pattern as the constructor

**File:** `/Users/omergilad/workspace/AI/code-monkey/code_monkey/agents/web_researcher/web_researcher.py`

**Impact:** Potential event loop issues, especially in long-running processes

**Fix approach:** Convert to async method or use proper async context manager pattern

---

### Thread ID Type Inconsistency

**Issue:** When `thread_id` is None, `uuid.uuid4()` returns a UUID object, but the type annotation says `str`

**File:** `/Users/omergilad/workspace/AI/code-monkey/code_monkey/agents/web_researcher/web_researcher.py`

**Impact:** Type violations, potential serialization issues

**Fix approach:** Convert to string: `str(uuid.uuid4())`

---

### Shadowed Built-in Parameter Name

**Issue:** `dump_object()` uses `object` as parameter name, shadowing Python's built-in

**File:** `/Users/omergilad/workspace/AI/code-monkey/code_monkey/utils/json_utils.py`

**Impact:** Bad practice, can cause confusion and subtle bugs

**Fix approach:** Rename parameter to `obj` or `data`

---

### Unused Import

**Issue:** `import langchain.chat_models.base` appears unused

**File:** `/Users/omergilad/workspace/AI/code-monkey/code_monkey/agents/web_researcher/web_researcher.py`

**Impact:** Minor, but adds unnecessary import overhead

**Fix approach:** Remove unused import

---

### Missing Type Hints

**Issue:** `query` parameter in `search()` method lacks type annotation

**File:** `/Users/omergilad/workspace/AI/code-monkey/code_monkey/agents/web_researcher/web_researcher.py`

**Impact:** Reduced type safety and IDE support

**Fix approach:** Add `str` type hint to query parameter

---

### LangChain create_agent Deprecation

**File:** `/Users/omergilad/workspace/AI/code-monkey/code_monkey/agents/web_researcher/web_researcher.py`

**Code:**

```python
agent = create_agent(
    model=model,
    tools=tools,
    checkpointer=InMemorySaver(),
    system_prompt=system_prompt)
```

**Issue:** `langchain.agents.create_agent` is a legacy API. LangGraph recommends using LangGraph's agent patterns directly.

**Impact:** May break in future LangChain/LangGraph updates.

**Fix approach:** Migrate to LangGraph's prebuilt agent patterns or use `langgraph.prebuilt` components

---

### InMemorySaver with No Persistence

**File:** `/Users/omergilad/workspace/AI/code-monkey/code_monkey/agents/web_researcher/web_researcher.py`

**Issue:** Checkpointer uses `InMemorySaver()` which loses all state on restart.

**Impact:** No conversation persistence across application restarts.

**Fix approach:** Implement persistent checkpointer (e.g., `PostgresSaver`, `RedisSaver`) for production use

---

### Unsafe JSON Serialization

**File:** `/Users/omergilad/workspace/AI/code-monkey/code_monkey/utils/json_utils.py`

**Code:**

```python
def dump_object(object):
    return json.dumps(object, default=lambda o: o.__dict__, indent=2)
```

**Issues:**

- Uses Python reserved word `object` as parameter name
- No error handling for non-serializable objects
- Exposing `__dict__` may leak internal state

**Impact:** Runtime errors and potential information disclosure.

**Fix approach:**

```python
def dump_object(obj):
    return json.dumps(obj, default=str, indent=2)
```

---

### Type Safety Gap in last_message_content

**File:** `/Users/omergilad/workspace/AI/code-monkey/code_monkey/utils/langchain_utils.py`

**Code:**

```python
def last_message_content(state) -> str:
    return state["messages"][-1].text
```

**Issues:**

- No type hints for `state` parameter
- No validation that `state["messages"]` exists
- No validation that `state["messages"]` is non-empty
- No validation that last message has `text` attribute

**Impact:** Runtime errors if state structure is unexpected.

**Fix approach:** Add type hints and validation

---

## Known Bugs

### Missing Error Handling in Google Search

**Issue:** Direct dictionary access on `result["organic"]` without checking if key exists

**File:** `/Users/omergilad/workspace/AI/code-monkey/code_monkey/agents/web_researcher/tools.py`

**Trigger:** When GoogleSerperAPIWrapper returns unexpected response format or API error

**Workaround:** None - will raise KeyError

---

### Empty Result Assertion Failure

**Issue:** Test asserts `len(results) > 0` but search might return no results

**File:** `/Users/omergilad/workspace/AI/code-monkey/tests/test_google_search.py`

**Trigger:** API returns empty list, network issues, rate limiting

**Workaround:** Check API keys and network connectivity

---

## Security Considerations

### API Key Exposure

**File:** `/Users/omergilad/workspace/AI/code-monkey/.env`

**Risk:** API keys are committed to repository history.

**Current mitigation:** None detected.

**Recommendations:**

1. Rotate all exposed keys immediately
2. Add `.env` to `.gitignore`
3. Use GitHub Secrets or similar for CI/CD
4. Audit git history for key exposure

---

### No Input Validation

**Files:**

- `/Users/omergilad/workspace/AI/code-monkey/code_monkey/agents/web_researcher/tools.py`
- `/Users/omergilad/workspace/AI/code-monkey/code_monkey/agents/web_researcher/web_researcher.py`

**Risk:** User input passed directly to external APIs (Google Serper, Playwright).

**Potential issues:**

- Prompt injection via search queries
- Malicious URL navigation
- Unvalidated data storage

**Current mitigation:** None detected.

**Recommendations:** Add input sanitization and validation for all external-facing functions.

---

## Performance Bottlenecks

### Playwright Browser Per Instance

**Problem:** Each `WebResearcher` instantiation launches a new Playwright browser

**File:** `/Users/omergilad/workspace/AI/code-monkey/code_monkey/agents/web_researcher/web_researcher.py`

**Cause:** Browser initialized in constructor, no reuse pattern

**Improvement path:** Use connection pooling or shared browser instance pattern

---

### In-Memory Checkpointer

**Problem:** `InMemorySaver()` provides no persistence across restarts

**File:** `/Users/omergilad/workspace/AI/code-monkey/code_monkey/agents/web_researcher/web_researcher.py`

**Impact:** All conversation state lost on restart

**Improvement path:** Add Redis or SQLite-based checkpointer for production

---

## Fragile Areas

### Test Resource Leaks

**Files:**

- `/Users/omergilad/workspace/AI/code-monkey/tests/test_google_search.py`
- `/Users/omergilad/workspace/AI/code-monkey/tests/test_web_researcher.py`

**Why fragile:** Tests initialize Playwright/browser resources but have no try/finally cleanup if assertions fail

**Safe modification:** Use pytest fixtures with proper setup/teardown, or context managers

**Test coverage:** Tests call teardown at end but exceptions could skip cleanup

---

### No Mocking in Tests

**Files:**

- `/Users/omergilad/workspace/AI/code-monkey/tests/test_google_search.py`
- `/Users/omergilad/workspace/AI/code-monkey/tests/test_web_researcher.py`

**Why fragile:** Tests depend on live external APIs (Google Serper, Anthropic)

**Safe modification:** Add pytest-mock or unittest.mock for external service mocking

**Impact:** Tests are slow, flaky due to network/API issues, require API keys

---

### Agent State Management

**File:** `/Users/omergilad/workspace/AI/code-monkey/code_monkey/agents/web_researcher/web_researcher.py`

**Why fragile:** `InMemorySaver` checkpointer stores state in memory only. Any exception during `teardown()` could leave browser processes running.

**Safe modification:** Always use context manager or try/finally for teardown

**Test coverage:** No tests verify cleanup under error conditions

---

### Playwright Tool List Access

**File:** `/Users/omergilad/workspace/AI/code-monkey/tests/test_playwright_tools.py`

**Why fragile:** Line 43 uses string matching to find tools:

```python
navigate_tool = [tool for tool in pt.get_tools() if tool.name == "navigate_browser"]
```

**Risk:** Breaks if tool names change in LangChain/LangGraph updates

**Fix approach:** Use more robust tool identification or mock tools directly

---

## Scaling Limits

### Browser Process Memory

**Resource:** Playwright Chromium browser

**Current capacity:** One browser instance per WebResearcher (~100-200MB)

**Limit:** Memory exhaustion with many concurrent instances

**Scaling path:** Implement browser pooling, use browser context reuse, or consider headless alternatives

---

### In-Memory State Storage

**Resource:** `InMemorySaver` checkpointer

**Current capacity:** Single process memory only

**Limit:** No horizontal scaling, state lost on restart

**Scaling path:** Use Redis-backed checkpointer from LangGraph

---

## Dependencies at Risk

### LangChain/LangGraph Version Constraints

**Risk:** Loose version constraints (`langchain>=1.2.0`, `langgraph>=1.0.5`) may allow breaking changes

**File:** `/Users/omergilad/workspace/AI/code-monkey/pyproject.toml`

**Impact:** API changes could break agent creation and tool usage

**Migration plan:** Pin to specific minor versions, add integration tests to catch breaking changes

---

### langchain.agents.create_agent

**Risk:** Legacy API that may be deprecated

**Impact:** `web_researcher.py` will need refactoring

**Migration plan:** Migrate to LangGraph's prebuilt agent patterns:

- Use `langgraph.prebuilt.chat_agent_executor`
- Or implement custom node/edge graph

---

## Test Coverage Gaps

### Tests Use Incorrect Imports

**Files:**

- `/Users/omergilad/workspace/AI/code-monkey/tests/test_google_search.py`
- `/Users/omergilad/workspace/AI/code-monkey/tests/test_playwright_tools.py`

**What's not tested:** Integration tests cannot run due to import errors

**Risk:** Core functionality may be broken without detection

**Priority:** High - blocking all test execution

---

### No Unit Tests with Mocks

**What's not tested:** Individual tool behavior without external API calls

**Files:** `/Users/omergilad/workspace/AI/code-monkey/tests/`

**Risk:** Logic bugs masked by API responses, hard to test error handling

**Priority:** Medium

---

### No Integration Tests

**What's not tested:** Full agent workflow with mocked responses

**Files:** `/Users/omergilad/workspace/AI/code-monkey/tests/`

**Risk:** Agent orchestration issues not caught until deployment

**Priority:** Medium

---

### No Error Path Tests

**What's not tested:** Behavior when APIs fail, return errors, or timeout

**Files:** `/Users/omergilad/workspace/AI/code-monkey/tests/`

**Risk:** Users see unhandled exceptions instead of graceful degradation

**Priority:** High

---

### Missing Unit Tests for Utilities

**What's not tested:**

- `models.py` - model factory functions
- `json_utils.py` - dump_object function
- `langchain_utils.py` - last_message_content function

**Priority:** Medium

---

## Missing Critical Features

### Project Librarian Agent Not Implemented

**Issue:** According to `notes.md` and `CLAUDE.md`, a "Project Librarian" agent should exist but is not implemented.

**Planned functionality:**

- Scan project files and compute file hashes
- Compare against cache (`.codemonkey/file-hashes`)
- Generate per-file summaries (`.codemonkey/code-context`)
- Compose project context summary (`.codemonkey/project-context`)

**Impact:** Multi-agent architecture is incomplete; core functionality missing.

**Fix approach:** Implement `code_monkey/agents/project_librarian/` module following the specification in `notes.md`.

---

### Lead Developer Agent Not Implemented

**Issue:** The Lead Developer agent is referenced in architecture docs but not implemented.

**Planned functionality:**

- Core developer agent with file system access
- CLI tools integration
- Secure file writes (pass through security reviewer)

**Impact:** Cannot execute development tasks as designed.

**Fix approach:** Implement `code_monkey/agents/lead_developer/` module.

---

### main.py is a Stub

**Issue:** Entry point does nothing useful.

**File:** `/Users/omergilad/workspace/AI/code-monkey/code_monkey/main.py`

**Current content:**

```python
def main():
    print("Hello from code-monkey!")
```

**Impact:** Application cannot be run for its intended purpose.

**Fix approach:** Implement main entry point that initializes and runs the agent system.

---

### No Logging

**Problem:** Application has no logging framework configured

**Impact:** Debugging production issues extremely difficult

**Recommendation:** Add Python logging with structured output (JSON format recommended)

---

### No Error Handling Decorators/Wrappers

**Problem:** Tools and agents lack consistent error handling

**Impact:** Failures propagate as raw exceptions

**Recommendation:** Add error handling middleware or decorator pattern

---

### No Retry Logic

**Problem:** External API calls have no retry mechanism

**Impact:** Transient failures cause complete request failure

**Recommendation:** Add exponential backoff retry for external API calls

---

### No README Content

**File:** `/Users/omergilad/workspace/AI/code-monkey/README.md`

**Contents:** Only placeholder text - no actual documentation

**Impact:** New contributors cannot understand the project

**Priority:** Medium

---

*Concerns audit: 2026-01-31*
