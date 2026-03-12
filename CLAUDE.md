# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

code-monkey is a coding assistant with project context awareness. It has two specialized agents: a web researcher (LangGraph/LangChain-based) and a project librarian (direct orchestrator pattern, no graph). The web researcher uses LangGraph's `InMemorySaver` checkpointer for stateful execution; the project librarian does not use LangGraph.

## Development Commands

```bash
# Install dependencies
uv sync

# Run tests
uv run pytest

# Run a specific test file
uv run pytest tests/agents/project_librarian/test_project_mapper.py -v

# Run tests for a module
uv run pytest tests/agents/project_librarian/ -v

# Lint
uv run ruff check .
uv run ruff format .

# Type check
uv run pyright

# Add new dependencies
uv add <package>
```

## Architecture

Two active agents under `code_monkey/agents/`:

### Web Researcher (`agents/web_researcher/`)

Performs web research using Google Serper API and Playwright browser automation. Async agent built on LangChain tool-calling.

### Project Librarian (`agents/project_librarian/`)

Analyzes a project's codebase incrementally and builds a context summary tree. Key flow:

1. Discover Python files and compute SHA-256 hashes
2. Compare against cached hashes to find changed files
3. Parse changed files with AST to extract classes/functions
4. Re-summarize changed files → modules → parent modules (bottom-up)
5. Persist updated hashes and context to `.codemonkey/`

Key classes:

- `ProjectMapper` — orchestrates the full scan-diff-summarize cycle
- `Summarizer` — LLM-based summarization at file, module, and project levels
- `CacheManager` — atomic reads/writes of `.codemonkey/` cache files
- `CodeExtractor` — AST-based extraction of classes and functions (2 levels deep)
- `ProjectFileHashes` — tracks per-file SHA-256 hashes with change detection

**Cache save order is enforced**: `code_context.json` → `project_context.md` → `file_hashes.json` (hashes last, so an interrupted run re-summarizes rather than skipping changed files).

### Cache Layout (`.codemonkey/`)

```
file_hashes.json     # {relative_path: sha256_hash}
code_context.json    # ModuleContext tree (summaries per file/module)
project_context.md   # Full project overview text
```

### Shared Utilities (`code_monkey/utils/`)

- `task_result.py` — generic `TaskResult` for progress tracking across agents
- `langchain_utils.py` — LangChain helpers shared between agents
- `json_utils.py` — JSON parsing utilities

File discovery exclusions are governed by `IGNORED_DIRS` in `agents/project_librarian/utils/constants.py` (covers `.git`, `venv`, `__pycache__`, IDE dirs, `.codemonkey`, etc.).

## Models

`code_monkey/models/models.py` provides `get_openai_model()` (default `gpt-4o`) and `get_minimax_model()` (MiniMax via Anthropic-compatible API).

## Testing

Tests mirror source structure under `tests/`. Key fixtures in `tests/conftest.py`:
- `mock_project_template_root` (session-scoped) — points to `mock_project/template/crewai_trading_strategy/`
- `mock_project_working_copy` (function-scoped) — isolated copy of the template for each test

Integration tests (`test_project_mapper_integration.py`) use real filesystem and real utilities but mock the LLM at the boundary. The mock LLM returns deterministic strings encoding the summarized names so tests can assert on exact outputs.
