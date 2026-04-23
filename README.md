# code-monkey

`code-monkey` is a CLI coding assistant that runs against a target project directory and uses cached project context to answer requests.

It is built on LangGraph and LangChain, with a graph-based workflow that combines project mapping, tool use, conversation summarization, and a verification step.

## What it can do

- scan a target project and build cached codebase context
- reuse that context across later requests
- read and write files inside the target project
- run shell commands with human approval
- perform web research through a separate research agent
- persist conversation history across runs
- load additional tools from configured MCP servers

## Framework and architecture

At a high level, the runtime is:

`UI → Controller → LangGraph workflow → tools / helper agents`

The workflow includes:

- project mapping for codebase summarization and caching
- orchestration for the main assistant turn and tool calls
- conversation summarization for older chat history
- a tester/review pass that can ask the assistant to retry

Project context is cached in the target project's `.codemonkey/` directory. Conversation checkpoints are stored separately in SQLite.

## Known limitations

- Project mapping is primarily designed for Python codebases.
- Project context depends on LLM-generated summaries and may be incomplete or imperfect.
- The review loop is lightweight and does not provide strong correctness guarantees.
- Shell commands require explicit approval, which makes the agent less autonomous.
- Web research and MCP support are practical integrations, not a deeply developed platform layer.

## Setup

Requirements:

- Python 3.12+
- [`uv`](https://docs.astral.sh/uv/)
- API credentials for the models and services you want to use

Install dependencies:

```bash
uv sync
```

The app loads environment variables from `.env`.

Optional MCP servers can be configured in `~/.codemonkey/mcp.json`, for example:

```json
{
  "local-tools": {
    "transport": "stdio",
    "command": "python",
    "args": ["/absolute/path/to/local_mcp_server.py"],
    "cwd": "/absolute/path/to/project"
  },
  "remote-tools": {
    "transport": "http",
    "url": "https://your-mcp-host.example.com/mcp",
    "headers": {
      "Authorization": "Bearer your-token-here"
    }
  }
}
```

Environment variable interpolation is not currently supported in the MCP config.

## Usage

Run against the current directory:

```bash
uv run python -m code_monkey.main
```

Run against a different project:

```bash
uv run python -m code_monkey.main --path /path/to/project
```

Available slash commands:

- `/map` — force project remapping on the next turn
- `/clear` — clear the saved conversation for the current target project
- `/exit` — exit the CLI

## Development

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

Lint, format, and type-check:

```bash
uv run ruff check .
uv run ruff format .
uv run pyright
```
