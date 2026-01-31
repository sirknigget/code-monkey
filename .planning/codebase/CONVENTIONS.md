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
- Snake_case: `web_researcher.py`, `json_utils.py`, `test_google_search.py`

**Classes:**
- PascalCase: `SearchResult`, `WebResearcher`, `PlaywrightTools`

**Functions:**
- snake_case: `dump_object`, `google_search_tool`, `teardown`
- Public methods: `search()`, `get_tools()`, `initialize()`

**Variables:**
- snake_case: `thread_id`, `playwright_tools`, `google_serper`
- Private attributes: Leading underscore `_playwright`, `_browser`, `_tools`

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
1. Standard library imports (`asyncio`, `uuid`, `json`)
2. Third-party imports (`langchain`, `pydantic`, `playwright`)
3. Relative imports (`from src.agents.web_researcher.tools import ...`)

**Examples from codebase:**
```python
import asyncio
import uuid
from typing import Any

import langchain.chat_models.base
from langchain.agents import create_agent
from langchain_core.language_models import BaseChatModel
from pydantic import Field, BaseModel

from src.agents.web_researcher.tools import PlaywrightTools, google_search_tool
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
- Default values for optional parameters
- Type hints for all parameters

**Return Values:**
- Explicit return types in type hints
- Pydantic models for structured returns

## Module Design

**Exports:**
- Direct function/tool exports using `@tool` decorator
- Classes exported for instantiation

**No barrel files** - Imports use full paths

## Environment Configuration

**Pattern:**
```python
from dotenv import load_dotenv

load_dotenv(override=True)
```

**Placement:** At top of files that need environment variables

## Async Patterns

**Async/Await:**
- Use `async def` for async functions
- Use `asyncio.get_running_loop().run_until_complete()` for initialization in sync context
- Class method pattern for async factory: `@classmethod async def initialize(cls, ...)`

## LangChain/LangGraph Patterns

**Tool Definition:**
```python
from langchain_core.tools import tool

@tool
def google_search_tool(query: str) -> List[Dict[str, str]]:
    """Search Google for the given query using Serper API."""
    ...
```

**Agent Creation:**
```python
from langchain.agents import create_agent

self._agent = create_agent(
    model=model,
    tools=tools,
    checkpointer=InMemorySaver(),
    system_prompt=self.system_prompt)
```

---

*Convention analysis: 2026-01-31*
