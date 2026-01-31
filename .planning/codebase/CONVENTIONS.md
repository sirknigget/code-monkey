# Coding Conventions

**Analysis Date:** 2026-01-31

## Languages

**Primary:**
- Python 3.12+ - All source code

## Code Style

**Formatting:**
- No explicit formatter configured (Black, Ruff, Prettier not detected)
- Follow PEP 8 conventions by default
- Use 4 spaces for indentation

**Linting:**
- No explicit linter configured (Ruff, Pylint, flake8 not detected)

## Naming Patterns

**Files:**
- Snake_case: `web_researcher.py`, `json_utils.py`, `langchain_utils.py`
- No `__init__.py` files in directories (no barrel files)

**Classes:**
- PascalCase: `SearchResult`, `WebResearcher`, `PlaywrightTools`
- Base model classes inherit from `pydantic.BaseModel`

**Functions:**
- snake_case: `dump_object`, `google_search_tool`, `teardown`, `last_message_content`
- Public methods: `search()`, `get_tools()`, `initialize()`
- Async functions: `async def search()`, `async def teardown()`

**Variables:**
- snake_case: `thread_id`, `playwright_tools`, `google_serper`
- Private attributes: Leading underscore `_playwright`, `_browser`, `_tools`, `_agent`

**Constants:**
- UPPER_SNAKE_CASE: `NUM_GOOGLE_RESULTS`

## Type Hints

**Usage:**
- Full type annotations preferred
- Common patterns:
  ```python
  from typing import List, Dict, Any

  def search(self, query, thread_id: str = None) -> SearchResult:
      ...
  ```

**Pydantic Models:**
- Use Pydantic `Field` for descriptions:
  ```python
  from pydantic import Field, BaseModel

  class SearchResult(BaseModel):
      result: str = Field(description="The result of the web search")
      thread_id: str = Field(description="The thread ID for this search session")
  ```

## Import Organization

**Order:**
1. Standard library imports (`uuid`, `json`, `typing`)
2. Third-party imports (`langchain`, `pydantic`, `playwright`)
3. Local application imports (`from code_monkey.agents.web_researcher.tools import ...`)

**Path Aliases:**
- Absolute imports using package root `code_monkey`
- Example from `web_researcher.py`:
  ```python
  from code_monkey.agents.web_researcher.tools import PlaywrightTools, google_search_tool
  from code_monkey.utils.langchain_utils import last_message_content
  ```

## Error Handling

**Patterns:**
- Exceptions propagated to callers (no try/except wrapping in current code)
- Pydantic models for validation via BaseModel
- No custom exception classes defined

## Docstrings

**When to Document:**
- All public classes: Add class docstring
- Public methods: Add method docstring with description and params
- Use """triple double quotes"""

**Example:**
```python
class PlaywrightTools:
    """Manages Playwright browser tools lifecycle."""

    @classmethod
    async def initialize(cls, headless: bool = False):
        """Initialize Playwright, browser, and tools."""
        ...

    async def teardown(self):
        """Gracefully close browser and playwright."""
        ...
```

## Function Design

**Parameters:**
- Default values for optional parameters: `headless: bool = True`
- Type hints for all parameters

**Return Values:**
- Explicit return types in type hints
- Pydantic models for structured returns: `-> SearchResult`
- Simple values for utilities

**Class Methods:**
- Factory pattern via `async classmethod create()`: `WebResearcher.create(model, headless)`

## Module Design

**Exports:**
- Direct function/tool exports using `@tool` decorator from langchain_core
- Classes exported for instantiation

**No barrel files** - No `__init__.py` files, imports use full module paths

## Environment Configuration

**Pattern:**
```python
from dotenv import load_dotenv

load_dotenv(override=True)
```

**Placement:** At top of files that need environment variables (main.py, test files)

## Async Patterns

**Async/Await:**
- Use `async def` for async functions
- Class method pattern for async factory:
  ```python
  @classmethod
  async def initialize(cls, headless: bool = False):
      """Initialize Playwright, browser, and tools."""
      playwright = await async_playwright().start()
      ...
      return cls(playwright, browser, tools)
  ```

## Logging

**Framework:** No logging framework configured

**Patterns:**
- Debug/info output via `print(f"...")` statements
- Test output includes formatted results

## LangChain/LangGraph Patterns

**Tool Definition:**
```python
from langchain_core.tools import tool

@tool
def google_search_tool(query: str) -> List[Dict[str, str]]:
    """Search Google for the given query using Serper API."""
    google_serper = GoogleSerperAPIWrapper()
    result = google_serper.results(query)
    return result["organic"][:NUM_GOOGLE_RESULTS]
```

**Agent Creation:**
```python
from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver

agent = create_agent(
    model=model,
    tools=tools,
    checkpointer=InMemorySaver(),
    system_prompt=system_prompt)
```

---

*Convention analysis: 2026-01-31*
