# Architecture

**Analysis Date:** 2026-01-31

## Pattern Overview

**Overall:** Multi-Agent LangGraph Orchestration

**Key Characteristics:**
- LangGraph-based agent orchestration with stateful graph workflows
- Specialized agents with distinct responsibilities (Web Researcher, Project Librarian)
- Async-first design for I/O-bound operations (web requests, file discovery)
- Modular utility layer supporting agent operations
- In-memory checkpointer for state persistence within sessions

## Layers

**Entry Layer:**
- Purpose: Application entry point and initialization
- Location: `/Users/omergilad/workspace/AI/code-monkey/main.py`
- Contains: `main()` function, environment loading via dotenv
- Depends on: No internal modules (bootstrap only)
- Used by: CLI invocation

**Models Layer:**
- Purpose: LLM model configuration and instantiation
- Location: `/Users/omergilad/workspace/AI/code-monkey/code_monkey/models/models.py`
- Contains: Model factory functions (`get_openai_model`, `get_minimax_model`)
- Depends on: langchain-openai, langchain-anthropic
- Used by: Agent initialization

**Agents Layer:**
- Purpose: Specialized autonomous agents with tool access
- Location: `/Users/omergilad/workspace/AI/code-monkey/code_monkey/agents/`
- Contains:
  - `web_researcher/`: WebResearcher agent with Playwright + Google search tools
  - `project_librarian/`: Project analysis utilities (file discovery, hash computation, code parsing)
- Depends on: Models layer, Tools layer, Utilities layer
- Used by: Entry layer (future orchestration)

**Tools Layer:**
- Purpose: Reusable tool implementations for agents
- Location: `/Users/omergilad/workspace/AI/code-monkey/code_monkey/agents/web_researcher/tools.py`
- Contains: PlaywrightTools class, google_search_tool function
- Depends on: playwright, langchain-community, serper-api
- Used by: WebResearcher agent

**Utilities Layer:**
- Purpose: Shared helper functions and utilities
- Location: `/Users/omergilad/workspace/AI/code-monkey/code_monkey/utils/`
- Contains:
  - `langchain_utils.py`: LangChain helper functions
  - `json_utils.py`: JSON serialization utilities
- Depends on: Standard library only (where possible)
- Used by: All layers

**Project Librarian Utilities:**
- Purpose: File system and code analysis operations
- Location: `/Users/omergilad/workspace/AI/code-monkey/code_monkey/agents/project_librarian/utilities/`
- Contains:
  - `file_discovery.py`: Python file discovery with exclusions
  - `hash_utils.py`: SHA-256 file hashing for change detection
  - `code_parser.py`: AST-based code structure extraction
- Depends on: pathlib, hashlib, ast
- Used by: Project Librarian agent, integration tests

## Data Flow

**Web Research Flow:**

1. User invokes application with query
2. Entry layer initializes models via models.py
3. WebResearcher agent is created with PlaywrightTools
4. Query is passed to agent with thread_id for session tracking
5. Agent uses tools (Google search, Playwright browsing) to gather information
6. Response is extracted from agent state via last_message_content()
7. Result returned with thread_id for potential continuation

**Project Analysis Flow:**

1. Project Librarian receives project root path
2. File discovery scans for Python files (excluding venv, node_modules, .git)
3. For each file:
   - Hash computed for change detection
   - Code parsed via AST to extract classes, functions, imports
4. Aggregated results returned as structured data

**State Management:**
- LangGraph InMemorySaver checkpointer for agent state persistence
- Thread-based session isolation via configurable thread_id
- No persistent storage between sessions (in-memory only)

## Key Abstractions

**Agent Abstraction:**
- Purpose: Encapsulates LLM agent with tools and state
- Examples:
  - `/Users/omergilad/workspace/AI/code-monkey/code_monkey/agents/web_researcher/web_researcher.py` (WebResearcher class)
- Pattern: Factory method (create) + async instance methods (search, teardown)

**Tool Abstraction:**
- Purpose: Provides reusable capabilities to agents
- Examples:
  - `/Users/omergilad/workspace/AI/code-monkey/code_monkey/agents/web_researcher/tools.py` (PlaywrightTools, google_search_tool)
- Pattern: Class-based lifecycle management + decorated functions

**Utility Abstraction:**
- Purpose: Stateless helper functions for common operations
- Examples:
  - `/Users/omergilad/workspace/AI/code-monkey/code_monkey/agents/project_librarian/utilities/file_discovery.py`
  - `/Users/omergilad/workspace/AI/code-monkey/code_monkey/agents/project_librarian/utilities/hash_utils.py`
  - `/Users/omergilad/workspace/AI/code-monkey/code_monkey/agents/project_librarian/utilities/code_parser.py`
- Pattern: Pure functions with typed signatures, NamedTuple for result structures

**Data Model Abstraction:**
- Purpose: Structured response types with validation
- Examples:
  - `/Users/omergilad/workspace/AI/code-monkey/code_monkey/agents/web_researcher/web_researcher.py` (SearchResult)
  - `/Users/omergilad/workspace/AI/code-monkey/code_monkey/agents/project_librarian/utilities/code_parser.py` (ParsedCode)
- Pattern: Pydantic BaseModel and typing.NamedTuple

## Entry Points

**main():**
- Location: `/Users/omergilad/workspace/AI/code-monkey/main.py`
- Triggers: `python main.py` or `uv run python main.py`
- Responsibilities: Environment loading, application bootstrap (currently stub)

**Test Suite:**
- Location: `/Users/omergilad/workspace/AI/code-monkey/tests/`
- Triggers: `pytest` or `uv run pytest`
- Responsibilities: Unit and integration tests for agents and utilities

## Error Handling

**Strategy:** Try-except with graceful degradation

**Patterns:**
- Syntax errors in code parsing return empty ParsedCode (no exception propagation)
- File read errors propagate as OSError
- Agent errors via LangChain exception handling

## Cross-Cutting Concerns

**Logging:** Print statements only (no structured logging framework)

**Validation:** Pydantic BaseModel for response types, typed signatures throughout

**Authentication:** Environment variables via dotenv for API keys (ANTHROPIC_API_KEY, OPENAI_API_KEY, SERPER_API_KEY)

**Async Operations:** Async/await pattern for I/O-bound work (Playwright, file operations)

---

*Architecture analysis: 2026-01-31*
