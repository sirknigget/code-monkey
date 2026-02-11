# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

code-monkey is a LangGraph-based coding assistant with project context awareness. It uses a multi-agent architecture where specialized agents collaborate on development tasks.

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

### Cache Layout (`.codemonkey/`)

```
file_hashes.json     # {relative_path: sha256_hash}
code_context.json    # ModuleContext tree (summaries per file/module)
project_context.md   # Full project overview text
```

## Models

`code_monkey/models/models.py` provides `get_openai_model()` (default `gpt-4o`) and `get_minimax_model()` (MiniMax via Anthropic-compatible API).

## Testing

Tests mirror source structure under `tests/`. Fixtures for temporary directories and mock project templates are in `tests/conftest.py`. The `mock_project/` directory contains sample Python files used for integration-style tests.
