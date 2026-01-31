# Codebase Concerns

**Analysis Date:** 2026-01-31

## Tech Debt

### Async Code in Synchronous Constructor
- **Issue:** `WebResearcher.__init__` runs async `PlaywrightTools.initialize()` synchronously using `run_until_complete()` in a constructor
- **File:** `/Users/omergilad/workspace/AI/code-monkey/src/agents/web_researcher/web_researcher.py`
- **Line:** 31
- **Impact:** This anti-pattern can cause issues in certain async contexts and makes the class harder to use in async codebases
- **Fix approach:** Make `__init__` async, or use a factory pattern with async initialization

### Async Teardown in Synchronous Context
- **Issue:** `WebResearcher.teardown()` uses the same async-in-sync pattern as the constructor
- **File:** `/Users/omergilad/workspace/AI/code-monkey/src/agents/web_researcher/web_researcher.py`
- **Line:** 50
- **Impact:** Potential event loop issues, especially in long-running processes
- **Fix approach:** Convert to async method or use proper async context manager pattern

### Thread ID Type Inconsistency
- **Issue:** When `thread_id` is None, `uuid.uuid4()` returns a UUID object, but the type annotation says `str`
- **File:** `/Users/omergilad/workspace/AI/code-monkey/src/agents/web_researcher/web_researcher.py`
- **Lines:** 42-43
- **Impact:** Type violations, potential serialization issues
- **Fix approach:** Convert to string: `str(uuid.uuid4())`

### Shadowed Built-in Parameter Name
- **Issue:** `dump_object()` uses `object` as parameter name, shadowing Python's built-in
- **File:** `/Users/omergilad/workspace/AI/code-monkey/src/utils/json_utils.py`
- **Line:** 3
- **Impact:** Bad practice, can cause confusion and subtle bugs
- **Fix approach:** Rename parameter to `obj` or `data`

### Unused Import
- **Issue:** `import langchain.chat_models.base` appears unused
- **File:** `/Users/omergilad/workspace/AI/code-monkey/src/agents/web_researcher/web_researcher.py`
- **Line:** 5
- **Impact:** Minor, but adds unnecessary import overhead
- **Fix approach:** Remove unused import

### Missing Type Hints
- **Issue:** `query` parameter in `search()` method lacks type annotation
- **File:** `/Users/omergilad/workspace/AI/code-monkey/src/agents/web_researcher/web_researcher.py`
- **Line:** 39
- **Impact:** Reduced type safety and IDE support
- **Fix approach:** Add `str` type hint to query parameter

## Known Bugs

### Missing Error Handling in Google Search
- **Issue:** Direct dictionary access on `result["organic"]` without checking if key exists
- **File:** `/Users/omergilad/workspace/AI/code-monkey/src/agents/web_researcher/tools.py`
- **Line:** 17
- **Trigger:** When GoogleSerperAPIWrapper returns unexpected response format or API error
- **Workaround:** None - will raise KeyError

### Empty Result Assertion Failure
- **Issue:** Test asserts `len(results) > 0` but search might return no results
- **File:** `/Users/omergilad/workspace/AI/code-monkey/tests/test_google_search.py`
- **Line:** 22
- **Trigger:** API returns empty list, network issues, rate limiting
- **Workaround:** Check API keys and network connectivity

## Security Considerations

### No Input Validation
- **Risk:** User-provided queries are passed directly to external APIs without sanitization
- **Files:** `/Users/omergilad/workspace/AI/code-monkey/src/agents/web_researcher/tools.py`, `/Users/omergilad/workspace/AI/code-monkey/src/agents/web_researcher/web_researcher.py`
- **Current mitigation:** None
- **Recommendations:** Add input validation/sanitization before passing to search APIs

### Environment Variables in Version Control
- **Risk:** `.env` file exists in repository
- **File:** `/Users/omergilad/workspace/AI/code-monkey/.env`
- **Current mitigation:** `.gitignore` likely present
- **Recommendations:** Verify `.gitignore` excludes `.env`, use `.env.example` template

## Performance Bottlenecks

### Playwright Browser Per Instance
- **Problem:** Each `WebResearcher` instantiation launches a new Playwright browser
- **File:** `/Users/omergilad/workspace/AI/code-monkey/src/agents/web_researcher/web_researcher.py`
- **Cause:** Browser initialized in constructor, no reuse pattern
- **Improvement path:** Use connection pooling or shared browser instance pattern

### In-Memory Checkpointer
- **Problem:** `InMemorySaver()` provides no persistence across restarts
- **File:** `/Users/omergilad/workspace/AI/code-monkey/src/agents/web_researcher/web_researcher.py`
- **Line:** 36
- **Impact:** All conversation state lost on restart
- **Improvement path:** Add Redis or SQLite-based checkpointer for production

## Fragile Areas

### Test Resource Leaks
- **Files:** `/Users/omergilad/workspace/AI/code-monkey/tests/test_google_search.py`, `/Users/omergilad/workspace/AI/code-monkey/tests/test_web_researcher.py`
- **Why fragile:** Tests initialize Playwright/browser resources but have no try/finally cleanup if assertions fail
- **Safe modification:** Use pytest fixtures with proper setup/teardown, or context managers
- **Test coverage:** Tests call teardown at end but exceptions could skip cleanup

### No Mocking in Tests
- **Files:** `/Users/omergilad/workspace/AI/code-monkey/tests/test_google_search.py`, `/Users/omergilad/workspace/AI/code-monkey/tests/test_web_researcher.py`
- **Why fragile:** Tests depend on live external APIs (Google Serper, Anthropic)
- **Safe modification:** Add pytest-mock or unittest.mock for external service mocking
- **Impact:** Tests are slow, flaky due to network/API issues, require API keys

## Scaling Limits

### Browser Process Memory
- **Resource:** Playwright Chromium browser
- **Current capacity:** One browser instance per WebResearcher (~100-200MB)
- **Limit:** Memory exhaustion with many concurrent instances
- **Scaling path:** Implement browser pooling, use browser context reuse, or consider headless alternatives

### In-Memory State Storage
- **Resource:** `InMemorySaver` checkpointer
- **Current capacity:** Single process memory only
- **Limit:** No horizontal scaling, state lost on restart
- **Scaling path:** Use Redis-backed checkpointer from LangGraph

## Dependencies at Risk

### LangChain/LangGraph Version Constraints
- **Risk:** Loose version constraints (`langchain>=1.2.0`, `langgraph>=1.0.5`) may allow breaking changes
- **File:** `/Users/omergilad/workspace/AI/code-monkey/pyproject.toml`
- **Impact:** API changes could break agent creation and tool usage
- **Migration plan:** Pin to specific minor versions, add integration tests to catch breaking changes

## Test Coverage Gaps

### No Unit Tests with Mocks
- **What's not tested:** Individual tool behavior without external API calls
- **Files:** `/Users/omergilad/workspace/AI/code-monkey/tests/`
- **Risk:** Logic bugs masked by API responses, hard to test error handling
- **Priority:** Medium

### No Integration Tests
- **What's not tested:** Full agent workflow with mocked responses
- **Files:** `/Users/omergilad/workspace/AI/code-monkey/tests/`
- **Risk:** Agent orchestration issues not caught until deployment
- **Priority:** Medium

### No Error Path Tests
- **What's not tested:** Behavior when APIs fail, return errors, or timeout
- **Files:** `/Users/omergilad/workspace/AI/code-monkey/tests/`
- **Risk:** Users see unhandled exceptions instead of graceful degradation
- **Priority:** High

## Missing Critical Features

### No Logging
- **Problem:** Application has no logging framework configured
- **Impact:** Debugging production issues extremely difficult
- **Recommendation:** Add Python logging with structured output (JSON format recommended)

### No Error Handling Decorators/Wrappers
- **Problem:** Tools and agents lack consistent error handling
- **Impact:** Failures propagate as raw exceptions
- **Recommendation:** Add error handling middleware or decorator pattern

### No Retry Logic
- **Problem:** External API calls have no retry mechanism
- **Impact:** Transient failures cause complete request failure
- **Recommendation:** Add exponential backoff retry for external API calls

---

*Concerns audit: 2026-01-31*
