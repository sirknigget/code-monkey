# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

`code-monkey` is a CLI coding assistant built around a LangGraph workflow. It operates on a target project root, incrementally maps that codebase into cached project context, and uses that context to answer coding requests. The runtime has three distinct layers of persistence:

- LangGraph conversation checkpoints in SQLite
- Project-librarian cache files under the target project's `.codemonkey/`
- A running chat summary used to compress older conversation history without losing the latest turn

The root `README.md` contains the main user-facing overview. There are no `.cursorrules`, `.cursor/rules/`, or `.github/copilot-instructions.md` files in this repo.

## Development Commands

```bash
# Install dependencies
uv sync

# Run the CLI against the current directory
uv run python -m code_monkey.main

# Run the CLI against an explicit project root
uv run python -m code_monkey.main --path /path/to/project

# Run the full test suite
uv run pytest

# Run a single test file
uv run pytest tests/graph/test_agent_graph.py -v

# Run a focused test module/directory
uv run pytest tests/agents/project_librarian/ -v

# Lint / format / type-check
uv run ruff check .
uv run ruff format .
uv run pyright
```

## Runtime Behavior

- `code_monkey/main.py` is the composition root: it loads `.env`, creates the checkpointer, opens MCP sessions via `MCPLoader`, builds `AgentGraph`, and hands it to `Controller`.
- The CLI defaults to `cwd` as the target project root; `--path` overrides it.
- Conversation checkpoints live in `~/.codemonkey/checkpoints.db` by default and can be overridden with `CODEMONKEY_DB_PATH`.
- MCP server definitions are loaded from `~/.codemonkey/mcp.json`; missing config means no MCP tools are added, while load/init failures are surfaced to the UI as startup errors.
- The checkpoint thread ID is the absolute target project path, so each mapped project gets its own persisted chat history even though the DB is global.
- On startup, each successfully initialized MCP server is announced to the UI with the loaded tool names before the controller loop begins.
- The controller handles `/clear`, `/map`, and `/exit` at the UI layer:
  - `/clear` deletes the current thread's checkpointed conversation
  - `/map` forces project remapping on the next user turn
  - `/exit` ends the session

## Architecture

The main flow is **UI → Controller → AgentGraph → Nodes/Tools/Agents**.

### UI and controller

`ChatbotUI` is a protocol in `code_monkey/ui/protocol.py`; the controller depends only on that interface. `Controller` owns the interactive loop, replays prior history when a checkpoint exists, interprets slash commands, and streams graph output back to the UI.

There are two UI implementations:
- `ui/impl/cli_simple.py` — the current default used by `main.py`
- `ui/impl/cli_prompt_toolkit.py` — richer terminal UX with slash-command completion

### LangGraph workflow

`AgentGraph` compiles a `StateGraph` with this flow:

`START → (map_project_node?) → orchestrator_node ↔ tools → summarizer_node → tester_node → review_router_node → END|orchestrator_node`

Key behavior:
- `map_project_node` runs only for a new session or after `/map`
- `orchestrator_node` builds the system prompt from the cached project context plus any review feedback from a failed verification pass
- `tools` executes tool calls and loops back into the orchestrator until the model returns a plain assistant response
- `summarizer_node` compresses older chat history while keeping the most recent user turn intact in `last_messages`
- `tester_node` evaluates whether the assistant actually satisfied the user's request
- `review_router_node` either ends the turn or sends the workflow back through the orchestrator with failure feedback; review retries are capped by `MAX_REVIEW_CYCLES = 3`

`ChatbotState` in `code_monkey/graph/state.py` is the contract across nodes. Besides `messages`, it carries `needs_mapping`, `chat_summary`, `last_messages`, `tester_result`, `review_feedback`, and the counters that control retry loops.

### Tooling available to the orchestrator

`DefaultNodesProvider.create()` wires four tool groups into the orchestrator:
- file read/write tools scoped to the target project root
- a bash tool scoped to the target project root
- a web researcher tool
- any MCP tools loaded from configured external servers

Important details:
- MCP tools are flattened from per-server sessions and appended to the main orchestrator tool list.
- The bash tool is created with `ask_human_input=True`, so shell commands require explicit user approval.

### Project Librarian

The project librarian is the repo-specific subsystem that makes the assistant "project-aware." `ProjectMapper` incrementally refreshes a hierarchical module summary tree instead of re-summarizing the whole codebase every turn.

High-level mapping flow:
1. Discover tracked Python files and compute current hashes
2. Diff against stored hashes to identify added/changed/deleted files
3. Rebuild only the affected branches of the `ModuleContext` tree
4. Summarize changed files and modules bottom-up
5. Generate a project-wide context document from both the module summaries and a filesystem structure snapshot
6. Persist cache outputs with hashes written last

Cache files live under the target project's `.codemonkey/`:

```text
.codemonkey/file_hashes.json
.codemonkey/code_context.json
.codemonkey/project_context.md
```

The write order matters: code context and project context are saved before file hashes so an interrupted mapping run will re-summarize instead of falsely treating stale cache as current.

### MCP integration

MCP support lives under `code_monkey/mcp/`:
- `config.py` loads and validates the JSON config at `~/.codemonkey/mcp.json`
- `loader.py` opens one session per configured server, loads each server's tools through `langchain-mcp-adapters`, keeps successful sessions alive for graph execution, and reports per-server failures without aborting the whole startup path

This means MCP is optional and additive: the app still starts if the config file is missing or one server fails, but only successfully initialized MCP tools are available to the orchestrator.

### Supporting agents

- `agents/chat_summarizer/` maintains a rolling summary of older conversation history so checkpoints stay useful without forcing every turn to replay the full transcript.
- `agents/tester/` is a separate verification agent that checks whether the assistant completed the user's request, not just whether code compiles.
- `agents/web_researcher/` is an async research agent that combines Google Serper search results with Playwright browser tools.

## Models

`ModelConfig` is the central place that decides which model each role uses:

- orchestrator: `gpt-4.1`
- tester: `gpt-4.1`
- project summarizer: `gpt-4o-mini`
- chat summarizer: `gpt-4o-mini`
- web researcher: `gpt-4o-mini`

`code_monkey/models/models.py` also exposes helpers for Ollama and MiniMax-compatible models, but the default app wiring currently uses OpenAI chat models.

## Testing

Tests mirror the source tree under `tests/`. Useful anchors:

- `tests/conftest.py` defines the mock-project fixtures used by Project Librarian tests
- `tests/graph/` covers graph composition and node behavior
- `tests/e2e/` exercises end-to-end flows like mapping, persistence, web research, coding tasks, and MCP tool execution
- `tests/mcp/` covers MCP config parsing and loader lifecycle behavior
- `tests/main/test_setup_mcp.py` verifies that startup forwards loaded MCP sessions into `AgentGraph` and reports them to the UI

Project Librarian integration tests use the real filesystem and cache flow but mock the LLM at the boundary with deterministic summaries. That makes them the best reference when changing incremental mapping behavior.

Do not include `tests/agents/project_librarian/test_project_mapper_real_llm.py` in routine test runs; it is explicitly for manual real-LLM validation.