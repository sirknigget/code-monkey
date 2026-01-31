# Testing Patterns

**Analysis Date:** 2026-01-31

## Test Framework

**Runner:**
- **Framework:** pytest 8.0.0+
- **Async Support:** pytest-asyncio 1.3.0+
- **Config:** `pyproject.toml`
  ```toml
  [tool.pytest.ini_options]
  pythonpath = ["."]
  ```

**Assertion Library:**
- Standard pytest assertions (`assert`, `isinstance`, etc.)

**Run Commands:**
```bash
uv run pytest              # Run all tests
uv run pytest -v           # Verbose output
uv run pytest tests/       # Run specific directory
uv run pytest test_file.py # Run specific file
```

## Test File Organization

**Location:**
- Separate `tests/` directory at project root: `/Users/omergilad/workspace/AI/code-monkey/tests/`

**Naming:**
- Pattern: `test_*.py`
- Examples: `test_google_search.py`, `test_playwright_tools.py`, `test_web_researcher.py`

**Structure:**
```
tests/
├── test_google_search.py       # Google search tool tests
├── test_playwright_tools.py    # PlaywrightTools class tests
└── test_web_researcher.py      # WebResearcher agent tests
```

## Test Structure

**Test Function Pattern (sync):**
```python
import pytest
from dotenv import load_dotenv

from code_monkey.agents.web_researcher.tools import google_search_tool, NUM_GOOGLE_RESULTS

load_dotenv(override=True)

def test_google_search_tool():
    """Test the Google Search tool."""
    query = "LangChain"
    results = google_search_tool.invoke(query)

    print(f"\n=== Google Search Results for '{query}' ===\n")
    for i, result in enumerate(results, 1):
        print(f"{i}. {result['title']}")
        print(f"   Link: {result['link']}")
        print(f"   Snippet: {result['snippet']}")
        print()

    assert isinstance(results, list)
    assert len(results) > 0 and len(results) <= NUM_GOOGLE_RESULTS
    for result in results:
        assert "title" in result
        assert "link" in result
        assert "snippet" in result
```

**Async Test Pattern:**
```python
import pytest
from dotenv import load_dotenv

from code_monkey.agents.web_researcher.tools import PlaywrightTools

load_dotenv(override=True)

@pytest.mark.asyncio
async def test_playwright_tools_initialize():
    """Test PlaywrightTools initialization."""
    pt = await PlaywrightTools.initialize(headless=True)

    assert pt._playwright is not None
    assert pt._browser is not None
    assert pt._tools is not None
    assert len(pt._tools) > 0

    await pt.teardown()
```

**WebResearcher Integration Test:**
```python
import pytest
from dotenv import load_dotenv

from code_monkey.agents.web_researcher.web_researcher import WebResearcher
from code_monkey.models.models import get_minimax_model

load_dotenv(override=True)

@pytest.mark.asyncio
async def test_web_researcher_search():
    """Test the WebResearcher agent with a query about LangChain."""
    model = get_minimax_model()
    researcher = await WebResearcher.create(model=model, headless=True)

    query = "What is the latest price of BTC and its recent trend?"
    result = await researcher.search(query)

    print(f"\n=== Web Researcher Result for '{query}' ===")
    print(f"Thread ID: {result.thread_id}")
    print(f"Result: {result.result}")
    print()

    assert result is not None
    assert result.thread_id is not None
    assert isinstance(result.thread_id, str)
    assert len(result.thread_id) > 0
    assert result.result is not None
    assert isinstance(result.result, str)
    assert len(result.result) > 0

    await researcher.teardown()
```

## Assertions

**Common Patterns:**
- `assert isinstance(results, list)`
- `assert len(results) > 0`
- `assert result is not None`
- `assert "title" in result`
- `assert True` (for tests that verify no exceptions)
- Multiple assertions per test for comprehensive verification

## Mocking

**Framework:** Python built-in `unittest.mock` (not explicitly configured)

**Manual Mocks:**
- No mocking framework configured
- Tests make real API calls (Google Serper, Playwright browser)

**What is Tested (Real Integrations):**
- Real tool invocations: `google_search_tool.invoke(query)`
- Full Playwright browser initialization: `await PlaywrightTools.initialize()`
- Actual WebResearcher agent calls with LLM

**What to Mock (for unit tests):**
- External APIs (Google Serper, LLM providers)
- Browser operations for faster unit tests
- Network calls in isolation

## Fixtures and Factories

**conftest.py:** Not present in tests directory

**Test Data:**
- Constants imported from source modules: `NUM_GOOGLE_RESULTS`
- Inline test data: `query = "LangChain"`

**Resource Cleanup:**
```python
pt = await PlaywrightTools.initialize(headless=True)
# ... test actions ...
await pt.teardown()  # Always clean up browser resources
```

## Coverage

**Requirements:** None enforced

**View Coverage:**
```bash
uv run pytest --cov=code_monkey --cov-report=term-missing
```

## Test Types

**Unit Tests:**
- Minimal in current codebase
- Test individual functions like `google_search_tool.invoke()`
- Verify tool outputs have expected structure

**Integration Tests:**
- Test `PlaywrightTools` class lifecycle (initialize, get_tools, teardown)
- Test browser navigation with real Playwright
- Test `WebResearcher` agent end-to-end

**E2E Tests:**
- Not explicitly separated from integration tests
- `test_web_researcher.py` performs full agent workflow test with real LLM

## Common Patterns

**Async Testing:**
```python
@pytest.mark.asyncio
async def test_name():
    # Setup
    pt = await PlaywrightTools.initialize(headless=True)

    # Test action
    tools = pt.get_tools()

    # Assertions
    assert tools is not None

    # Cleanup
    await pt.teardown()
```

**Tool Invocation:**
```python
# LangChain tool invocation (sync)
results = google_search_tool.invoke(query)

# Tool from toolkit list
navigate_tool = [tool for tool in pt.get_tools() if tool.name == "navigate_browser"]
result = await navigate_tool.ainvoke("https://example.com")
```

**Debug Output:**
```python
print(f"\n=== Web Researcher Result for '{query}' ===")
print(f"Thread ID: {result.thread_id}")
print(f"Result: {result.result}")
```

**Structured Output:**
```python
from code_monkey.utils.json_utils import dump_object
print(f"Navigation result:\n {dump_object(result)}")
```

## Environment in Tests

**Pattern:**
```python
from dotenv import load_dotenv
load_dotenv(override=True)
```

**Required in `.env`:**
- `ANTHROPIC_API_KEY` - For ChatAnthropic model
- `SERPER_API_KEY` - For Google search via Serper API

---

*Testing analysis: 2026-01-31*
