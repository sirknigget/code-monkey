# Testing Patterns

**Analysis Date:** 2026-01-31

## Test Framework

**Runner:**
- pytest 8.0.0+
- Config: `pyproject.toml`

**Async Support:**
- pytest-asyncio 1.3.0+
- Use `@pytest.mark.asyncio` decorator for async tests

**Run Commands:**
```bash
uv run pytest              # Run all tests
uv run pytest -v           # Verbose output
uv run pytest tests/       # Run specific directory
uv run pytest test_file.py # Run specific file
```

## Test File Organization

**Location:**
- Separate `tests/` directory at project root
- Not co-located with source files

**Naming:**
- Pattern: `test_*.py`
- Examples: `test_google_search.py`, `test_playwright_tools.py`, `test_web_researcher.py`

**Structure:**
```
tests/
├── conftest.py           # Shared fixtures
├── test_google_search.py # Google search tool tests
├── test_playwright_tools.py  # PlaywrightTools class tests
└── test_web_researcher.py    # WebResearcher agent tests
```

## Test Structure

**Fixture Setup (conftest.py):**
```python
import pytest
import sys
from pathlib import Path

# Add the src directory to Python path
src_path = Path(__file__).parent.parent
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))
```

**Test Function Pattern:**
```python
import pytest
from dotenv import load_dotenv

from src.agents.web_researcher.tools import google_search_tool, NUM_GOOGLE_RESULTS

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

from src.agents.web_researcher.tools import PlaywrightTools

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

## Assertions

**Common Patterns:**
- `assert isinstance(results, list)`
- `assert len(results) > 0`
- `assert result is not None`
- `assert "title" in result`
- `assert True` (for tests that verify no exceptions)

## Mocking

**Framework:** Python built-in `unittest.mock` (not heavily used yet)

**Manual Mocks:**
- No mocking framework configured
- Tests make real API calls (Google Serper, Playwright browser)

**What is Tested:**
- Real tool invocations
- Full Playwright browser initialization
- Actual WebResearcher agent calls

## Fixtures

**conftest.py Purpose:**
- Adds `src/` to Python path for imports
- No custom pytest fixtures defined yet

## Coverage

**Requirements:** None enforced

**View Coverage:**
```bash
uv run pytest --cov=src --cov-report=term-missing
```

## Test Types

**Unit Tests:**
- Test individual functions like `google_search_tool.invoke()`
- Verify tool outputs have expected structure

**Integration Tests:**
- Test `PlaywrightTools` class lifecycle (initialize, get_tools, teardown)
- Test browser navigation
- Test `WebResearcher` agent end-to-end

**E2E Tests:**
- Not explicitly separated
- `test_web_researcher.py` performs full agent test

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
# LangChain tool invocation
results = google_search_tool.invoke(query)

# Single tool from list
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
from src.utils.json_utils import dump_object
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
- `SERPER_API_KEY` - For Google search (or `SERPER_API_KEY` env var)

---

*Testing analysis: 2026-01-31*
