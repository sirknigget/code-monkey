from contextlib import AsyncExitStack
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.tools import load_mcp_tools

from code_monkey.mcp.config import DEFAULT_MCP_CONFIG_PATH, load_mcp_config


@dataclass(frozen=True)
class MCPServerSessionHandle:
    server_name: str
    tools: list[BaseTool]
    session: Any


@dataclass(frozen=True)
class MCPClientContext:
    errors: list[str] = field(default_factory=list)
    sessions: list[MCPServerSessionHandle] = field(default_factory=list)
    _exit_stack: AsyncExitStack = field(default_factory=AsyncExitStack)

    async def __aenter__(self) -> "MCPClientContext":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self._exit_stack.aclose()


class MCPLoader:
    def __init__(self, config_path: Path = DEFAULT_MCP_CONFIG_PATH) -> None:
        self._config_path = config_path

    async def __call__(self) -> MCPClientContext:
        try:
            connections = load_mcp_config(self._config_path)
        except Exception as e:
            return MCPClientContext(
                errors=[f"Failed to load MCP config at {self._config_path}: {e}"]
            )

        client = MultiServerMCPClient(connections=connections)
        errors: list[str] = []
        sessions: list[MCPServerSessionHandle] = []
        aggregate_exit_stack = AsyncExitStack()

        for server_name in connections:
            # Keep each server session on its own temporary stack until that
            # server finishes loading tools successfully. If tool loading fails
            # after the session opens, we need to close only that session
            # immediately without touching already-successful servers.
            server_exit_stack = AsyncExitStack()
            try:
                session_cm = client.session(server_name)
                session = await server_exit_stack.enter_async_context(session_cm)
                tools = await load_mcp_tools(session, server_name=server_name)
            except Exception as e:
                await server_exit_stack.aclose()
                errors.append(f"Failed to initialize MCP server '{server_name}': {e}")
                continue

            # Transfer ownership of this server's cleanup only after the full
            # per-server setup succeeds, so the aggregate context owns only
            # live sessions that should remain open for graph execution.
            aggregate_exit_stack.push_async_exit(server_exit_stack.pop_all())
            sessions.append(
                MCPServerSessionHandle(
                    server_name=server_name,
                    tools=tools,
                    session=session,
                )
            )

        return MCPClientContext(
            errors=errors,
            sessions=sessions,
            _exit_stack=aggregate_exit_stack,
        )
