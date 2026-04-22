# code-monkey

A small LangGraph/LangChain learning project for building a CLI coding assistant with project context.

This repo is mainly me trying to understand how to wire together:

- a persistent chat loop
- tool-calling
- project summarization / context caching
- a separate review step that can ask the assistant to try again

It is usable, but it is not presented here as a polished general-purpose coding agent.

## What it does

`code-monkey` runs a terminal chat interface against a target project directory.

On a new session, it can:

- scan the target project
- build a cached summary of the codebase
- use that summary as project context for later requests
- read and write files inside the target project
- run shell commands with human approval
- do web research through a separate web-research agent
- persist conversation history across runs

The main idea is that the assistant should not start every turn from scratch. It keeps two kinds of memory:

- **conversation memory** in SQLite checkpoints
- **project memory** in `.codemonkey/` cache files inside the target project

## Current scope

Despite the general name, the current project-mapping logic is mostly aimed at **Python codebases**.

The Project Librarian discovers Python files, hashes them, and incrementally re-summarizes only the parts of the tree that changed. That makes this repo a better fit for experimenting with Python-project context than for handling arbitrary repositories.

## How it works

At a high level, the runtime is:

`UI → Controller → LangGraph workflow → tools / helper agents`

The graph currently runs these stages:

1. **Project mapping** (only when needed)

   - scans the target project
   - updates cached code summaries
   - writes `.codemonkey/file_hashes.json`, `.codemonkey/code_context.json`, and `.codemonkey/project_context.md`
2. **Orchestration**

   - sends the user request plus project context to the main model
   - allows tool calls for file access, shell access, and web research
3. **Conversation summarization**

   - compresses older chat history while keeping the current turn visible
4. **Testing / review**

   - a separate tester agent checks whether the assistant actually satisfied the request
   - if not, the graph can route back to the orchestrator and let it try again

This structure is probably the most interesting part of the project for me: not the UI, but the graph-based workflow and the separation between execution, summarization, and review.

## Running it

### Prerequisites

- Python 3.12+
- [`uv`](https://docs.astral.sh/uv/)
- API credentials for the models / services you want to use

The app loads environment variables from `.env`.

### Install dependencies

```bash
uv sync
```

### Run against the current directory

```bash
uv run python -m code_monkey.main
```

### Run against a different project

```bash
uv run python -m code_monkey.main --path /path/to/project
```

## Common commands for development

### Tests

Run all tests:

```bash
uv run pytest
```

Run a single test file:

```bash
uv run pytest tests/graph/test_agent_graph.py -v
```

Run a focused area:

```bash
uv run pytest tests/agents/project_librarian/ -v
```

### Lint / format / type-check

```bash
uv run ruff check .
uv run ruff format .
uv run pyright
```

## MCP support

MCP support is optional and additive.

By default, the app looks for a JSON config at:

```text
~/.codemonkey/mcp.json
```

Each top-level key is a server name, and each value is a connection config understood by `langchain-mcp-adapters`. The loader currently accepts transports such as `stdio`, `sse`, `http`, `streamable_http`, `streamable-http`, and `websocket`.

Example stdio server config:

```json
{
  "fixture": {
    "transport": "stdio",
    "command": "python",
    "args": ["/absolute/path/to/server.py"],
    "cwd": "/absolute/path/to/project"
  }
}
```

## Session behavior

The CLI supports a few slash commands:

- `/map` — force project remapping on the next turn
- `/clear` — clear the saved conversation thread for the current target project
- `/exit` — exit the CLI

Conversation checkpoints are stored in:

```text
~/.codemonkey/checkpoints.db
```

The thread ID is the absolute target project path, so different target projects keep separate histories inside the same database.

## Project structure

Some of the more important areas:

- `code_monkey/main.py` — composition root / CLI entrypoint
- `code_monkey/controller/` — interactive run loop
- `code_monkey/graph/` — LangGraph workflow and node wiring
- `code_monkey/agents/project_librarian/` — incremental codebase mapping and cache generation
- `code_monkey/agents/web_researcher/` — web-research agent using Serper + Playwright
- `code_monkey/agents/tester/` — review agent that checks whether the assistant actually completed the task
- `code_monkey/agents/chat_summarizer/` — rolling summary of older conversation history
- `code_monkey/mcp/` — MCP config loading and session lifecycle management for external tool servers
- `tests/` — unit, integration, and e2e coverage

## Shortcomings

This is the part I care about being honest about.

### 1. It is still a learning project

The architecture is intentional, but it is also exploratory. Some parts exist because I wanted to learn how LangGraph and LangChain fit together, not because they are obviously the best design for a production assistant.

### 2. The project understanding is narrow

The Project Librarian currently scans Python files. That means the "project-aware coding assistant" story is much stronger for Python repos than for mixed-language or non-Python repos.

### 3. The generated project context is only as good as the summaries

A lot depends on LLM-produced summaries of files, modules, and the full project. That can work surprisingly well, but it can also be lossy or slightly wrong. This repo is experimenting with that tradeoff rather than solving it completely.

### 4. The review loop is simple

The tester can ask the assistant to retry, but this is still a lightweight review mechanism. It is not a substitute for strong program analysis, real task planning, or deep correctness guarantees.

### 5. The tool layer is intentionally limited

The assistant can read/write files and run shell commands, but shell use requires human approval. That is good for safety, but it also means the UX is slower and less autonomous than a fully trusted local agent.

### 6. Web research is practical, but not especially refined

The web-research path uses Serper plus Playwright, which is enough for experimentation, but it is not a deeply tuned research pipeline.

## Testing notes

The tests are one of the more useful parts of the repo because they exercise the graph structure directly.

A notable exception:

```bash
uv run pytest tests/agents/project_librarian/test_project_mapper_real_llm.py -v
```

That test uses a real LLM and is meant for manual validation, not routine runs.

## Why I built it

Mostly to learn by building.

I wanted a project that was a bit more realistic than toy LangChain demos, but still small enough that I could understand the full flow end to end: CLI input, graph execution, tool calls, cached project context, persistence, and a separate verification step.

So this repo is best read as a working notebook in code form: structured, tested, and useful, but still clearly a practice project rather than a finished product.
