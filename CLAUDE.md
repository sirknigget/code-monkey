# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

code-monkey is a LangGraph-based coding assistant with project context awareness. It uses a multi-agent architecture where specialized agents collaborate on development tasks.

## Architecture

The system uses three specialized LangGraph agents:

1. **Web Researcher** - Handles research tasks using Google search and Playwright, produces summaries
2. **Project Librarian** - Scans project files, computes file hashes for caching, and generates context summaries
3. **Lead Developer** - Core developer agent with file system access and CLI tools; file writes pass through a security reviewer first

### Cache Infrastructure (planned)
- `.codemonkey/file-hashes` - File hash cache for change detection
- `.codemonkey/code-context` - Per-file summaries (signatures, classes)
- `.codemonkey/project-context` - Global project context summary

## Development Commands

```bash
# Install dependencies
uv sync

# Run the application
uv run python main.py

# Add new dependencies
uv add <package>

# Run tests (when added)
uv run pytest
```

## Dependencies

The project uses LangChain and LangGraph for LLM orchestration:
- `langchain` - LLM framework
- `langchain-anthropic` - Anthropic integration
- `langchain-openai` - OpenAI integration
- `langgraph` - Agent orchestration

## Key Implementation Details

- Python 3.12+ required
- Uses `uv` for package management
- Entry point: `main.py`
