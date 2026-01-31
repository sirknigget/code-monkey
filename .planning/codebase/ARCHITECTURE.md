# Architecture

**Analysis Date:** 2026-01-31

## Pattern Overview

**Overall:** Multi-Agent LangGraph Orchestration

**Key Characteristics:**
- Agent-based architecture with specialized, composable agents
- LangChain/LangGraph framework for LLM orchestration
- Tool-augmented agents that can interact with external systems (web, APIs)
- Checkpoint-based state management for conversation continuity
- Async/await patterns for I/O-bound operations (browser, network)

## Layers

**Application Layer:**
- Purpose: Entry point and top-level orchestration
- Location: `code_monkey/main.py`
- Contains: `main()` function, environment loading
- Depends on: Agent layer, utilities
- Used by: CLI invocation

**Agent Layer:**
- Purpose: Specialized LLM-powered agents with domain-specific capabilities
- Location: `code_monkey/agents/`
- Contains: Agent implementations, tool definitions
- Depends on: LangChain/LangGraph, external service clients
- Used by: Application layer, tests

**Tool Layer:**
- Purpose: Reusable capabilities exposed to agents
- Location: `code_monkey/agents/web_researcher/tools.py`
- Contains: Playwright browser tools, Google search wrapper
- Depends on: Playwright, LangChain community toolkits
- Used by: Agent layer

**Models Layer:**
- Purpose: LLM model configuration and factory functions
- Location: `code_monkey/models/models.py`
- Contains: `get_openai_model()`, `get_minimax_model()` factory functions
- Depends on: OpenAI, Anthropic/MiniMax SDKs
- Used by: Agent layer

**Utilities Layer:**
- Purpose: Shared helper functions
- Location: `code_monkey/utils/`
- Contains: JSON utilities, LangChain helpers
- Used by: All layers

## Data Flow

**Web Research Query Flow:**

1. User invokes `main()` or directly instantiates `WebResearcher`
2. `WebResearcher.create()` initializes PlaywrightTools asynchronously
3. `search(query)` is called with optional thread_id
4. LangChain agent receives query and decides which tool to use
5. Either `google_search_tool` or Playwright tools are invoked
6. Results are captured and returned as `SearchResult`
7. `teardown()` closes browser resources

**State Management:**
- `InMemorySaver` checkpointer maintains conversation state per thread_id
- Thread-based isolation using `RunnableConfig(configurable={"thread_id": ...})`
- State dict with "messages" key holds conversation history

## Key Abstractions

**WebResearcher Agent:**
- Purpose: Specialized agent for web research tasks
- Examples: `code_monkey/agents/web_researcher/web_researcher.py`
- Pattern: LangChain agent factory with custom tools and checkpointer

**PlaywrightTools:**
- Purpose: Manages async Playwright browser lifecycle
- Examples: `code_monkey/agents/web_researcher/tools.py`
- Pattern: Async class methods (initialize, get_tools, teardown)

**SearchResult:**
- Purpose: Typed response object for search operations
- Examples: `code_monkey/agents/web_researcher/web_researcher.py` (line 14-16)
- Pattern: Pydantic BaseModel for validation

**LLM Factory Functions:**
- Purpose: Centralized model configuration
- Examples: `code_monkey/models/models.py`
- Pattern: Factory functions returning configured model instances

## Entry Points

**Primary Entry Point:**
- Location: `code_monkey/main.py`
- Triggers: `python -m code_monkey.main` or `uv run python code_monkey/main.py`
- Responsibilities: Load environment variables, invoke main logic

**Test Entry Point:**
- Location: `tests/`
- Triggers: `pytest` or `uv run pytest`
- Responsibilities: Run test suite

**Agent Direct Usage:**
- Location: `code_monkey/agents/web_researcher/web_researcher.py`
- Triggers: Direct instantiation with LLM model
- Responsibilities: Execute web research tasks

## Error Handling

**Strategy:** Propagate exceptions through LangChain agent execution

**Patterns:**
- Async initialization errors bubble up from `PlaywrightTools.initialize()`
- Tool execution errors are caught and returned by LangChain agent framework
- Teardown errors in `teardown()` are not explicitly caught

## Cross-Cutting Concerns

**Logging:** Standard print statements, no structured logging framework

**Validation:** Pydantic BaseModel for typed responses (SearchResult)

**Authentication:** Environment variables via dotenv (loaded in main.py and tests)

**Async Management:** `async_playwright` lifecycle in PlaywrightTools

---

*Architecture analysis: 2026-01-31*
