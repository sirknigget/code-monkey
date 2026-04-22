# Context

The CLI currently wires built-in tools only (web research, file tools, bash). We need to add MCP-backed tools that are configured from JSON, loaded at startup, and torn down cleanly. The key constraint is that `MultiServerMCPClient` stateful sessions are per server, so the app must not treat MCP as one shared session; instead it should own an aggregate lifecycle that manages one session per configured server and passes the resulting tool sets into the graph.

# Recommended approach

## 1. Add a small MCP module for config and lifecycle

Create a dedicated `code_monkey/mcp/` package to keep MCP concerns out of `main.py` and the graph:

- `code_monkey/mcp/config.py`
  - Define `DEFAULT_MCP_CONFIG_PATH = Path("~/.codemonkey/mcp.json").expanduser()`.
  - Add JSON load/save helpers for the MCP config file.
  - Reuse the adapter-native connection/config types if they are importable from `langchain_mcp_adapters`; do not invent a parallel schema.
  - Treat missing config file as an empty config so MCP remains optional.

- `code_monkey/mcp/loader.py`
  - Add the default factory implementation `MCPLoader`.
  - Add thin handle types so the composition root can work with aggregated server sessions explicitly.
  - `MCPLoader` should parse the config and return an `MCPClientContext` object.
  - `MCPClientContext` should be the aggregate async context manager: entering it opens one stateful MCP session per configured server, loads that server’s tools, and stores the resulting per-server handles; exiting it closes all opened sessions.

Recommended shape:
- `MCPClientFactory` protocol in `main.py`, similar to `CheckpointerFactory`
- `MCPClientContext(errors: list[str], sessions: list[MCPServerSessionHandle])`
- `MCPServerSessionHandle(server_name: str, tools: list[BaseTool], session: Any)`
- `async with mcp_client_factory() as mcp_context:` in `main.py`

## 2. Keep lifecycle ownership in the composition root

Update `code_monkey/main.py`:

- Extend `setup(...)` to accept `mcp_client_factory: MCPClientFactory`.
- Have the factory return `MCPClientContext`, and use it directly with `async with` in `setup(...)`.
- After entering the context, surface any loader/entry errors via `ui.show_error(...)`, and continue if the config is empty or partially usable.
- Pass `mcp_context.sessions` into `AgentGraph.create(...)`.
- Let the `async with` block own MCP teardown, while `finally` still tears down the graph and checkpointer. `main.py` remains the only place that wires concrete MCP implementations.

## 3. Thread MCP handles into graph construction only

Update `code_monkey/graph/agent_graph.py`:

- Extend `AgentGraph.create(...)` to accept the loaded MCP session handles.
- Pass them into `DefaultNodesProvider.create(...)`.

Update `code_monkey/graph/default_nodes_provider.py`:

- Extend `create(...)` to accept MCP session handles.
- Flatten `handle.tools` into the existing `tools` list before constructing `ToolNode` and `make_orchestrator_node(...)`.
- Do not create or close MCP sessions here; this provider should only consume injected tools.

This keeps graph code simple: the graph receives ready-to-use tools and remains agnostic to MCP session lifecycle. The lifecycle boundary is fully represented by `MCPClientContext`, which is clearer than splitting result data from teardown ownership.

## 4. Tests

### Unit tests

Add focused tests for:

- `tests/mcp/test_config.py`
  - JSON round-trip for stdio/http server configs
  - missing file => empty config
  - explicit path overrides default path

- `tests/mcp/test_loader.py`
  - loader opens one session per configured server
  - loader aggregates per-server tools correctly
  - loader teardown closes all sessions
  - partial failures are surfaced as errors without silently swallowing them

- `tests/graph/test_default_nodes_provider.py` or an adjacent focused test
  - injected MCP tools are appended to the orchestrator/ToolNode tool list

- `tests/main/test_setup_mcp.py` or a focused existing-module test
  - `setup(...)` uses the MCP factory and forwards the loaded handles into `AgentGraph.create(...)`

### End-to-end test

Add a dedicated MCP e2e test with a real stdio server:

- Place a tiny MCP stdio server fixture under `tests/e2e/fixtures/` or `tests/e2e/mcp_servers/`.
- Expose exactly two tools with deterministic behavior.
- Write an MCP config JSON file in `tmp_path` pointing at that server.
- Extend `tests/e2e/conftest.py` helpers so `run_session(...)` can receive an injected MCP factory.
- Use `FakeModelConfig` to emit an MCP tool call followed by a final assistant message.
- Assert exact observable behavior: the tool result/side effect and the assistant messages.

Prefer filesystem side effects or exact returned text over internal call assertions.

## 5. Dependency and verification

Update `pyproject.toml` to add `langchain-mcp-adapters`.

Verification should stay focused:

- MCP unit tests only
- the new MCP e2e test
- any directly impacted graph/main tests
- `uv run ruff check .`
- `uv run pyright`

If the adapter API differs from the docs, verify these exact points during implementation:
- import path for connection/config types
- how to open per-server stateful sessions
- how to turn each session into LangChain tools
- exact exposed tool names for the real stdio e2e test

# Critical files

- `pyproject.toml`
- `code_monkey/main.py`
- `code_monkey/graph/agent_graph.py`
- `code_monkey/graph/default_nodes_provider.py`
- new files under `code_monkey/mcp/`
- `tests/e2e/conftest.py`
- new focused MCP unit tests
- new MCP e2e test and stdio server fixture
