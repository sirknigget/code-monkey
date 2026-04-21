from pathlib import Path
from types import SimpleNamespace

import pytest

from code_monkey.mcp.loader import MCPLoader


class _FakeClient:
    def __init__(self, connections):
        self.connections = connections

    def session(self, server_name: str):
        return _FakeSessionContext(server_name)


class _FakeSessionContext:
    def __init__(self, server_name: str) -> None:
        self.server_name = server_name

    async def __aenter__(self):
        _events.append(("enter", self.server_name))
        if self.server_name in _session_failures:
            raise RuntimeError(_session_failures[self.server_name])
        return SimpleNamespace(server_name=self.server_name)

    async def __aexit__(self, exc_type, exc, tb):
        _events.append(("exit", self.server_name))


_events: list[tuple[str, str]] = []
_session_failures: dict[str, str] = {}
_tool_failures: dict[str, str] = {}


async def _fake_load_mcp_tools(session, *, server_name: str, **kwargs):
    _events.append(("load", server_name))
    if server_name in _tool_failures:
        raise RuntimeError(_tool_failures[server_name])
    return [SimpleNamespace(name=f"{server_name}_tool")]


@pytest.fixture(autouse=True)
def reset_state(monkeypatch: pytest.MonkeyPatch) -> None:
    _events.clear()
    _session_failures.clear()
    _tool_failures.clear()
    monkeypatch.setattr("code_monkey.mcp.loader.MultiServerMCPClient", _FakeClient)
    monkeypatch.setattr("code_monkey.mcp.loader.load_mcp_tools", _fake_load_mcp_tools)


@pytest.mark.asyncio
async def test_loader_opens_one_session_per_configured_server(tmp_path: Path) -> None:
    loader = MCPLoader(_write_config(tmp_path, {
        "alpha": {"transport": "stdio", "command": "python", "args": ["alpha.py"]},
        "beta": {"transport": "stdio", "command": "python", "args": ["beta.py"]},
    }))

    async with await loader() as context:
        assert [handle.server_name for handle in context.sessions] == ["alpha", "beta"]

    assert _events == [
        ("enter", "alpha"),
        ("load", "alpha"),
        ("enter", "beta"),
        ("load", "beta"),
        ("exit", "beta"),
        ("exit", "alpha"),
    ]


@pytest.mark.asyncio
async def test_loader_aggregates_per_server_tools(tmp_path: Path) -> None:
    loader = MCPLoader(_write_config(tmp_path, {
        "alpha": {"transport": "stdio", "command": "python", "args": ["alpha.py"]},
        "beta": {"transport": "stdio", "command": "python", "args": ["beta.py"]},
    }))

    async with await loader() as context:
        tool_names = [tool.name for handle in context.sessions for tool in handle.tools]

    assert tool_names == ["alpha_tool", "beta_tool"]


@pytest.mark.asyncio
async def test_loader_teardown_closes_all_sessions(tmp_path: Path) -> None:
    loader = MCPLoader(_write_config(tmp_path, {
        "alpha": {"transport": "stdio", "command": "python", "args": ["alpha.py"]},
        "beta": {"transport": "stdio", "command": "python", "args": ["beta.py"]},
    }))

    async with await loader():
        pass

    assert _events[-2:] == [("exit", "beta"), ("exit", "alpha")]


@pytest.mark.asyncio
async def test_loader_surfaces_partial_failures_without_swallowing_them(tmp_path: Path) -> None:
    _tool_failures["beta"] = "tool load failed"
    loader = MCPLoader(_write_config(tmp_path, {
        "alpha": {"transport": "stdio", "command": "python", "args": ["alpha.py"]},
        "beta": {"transport": "stdio", "command": "python", "args": ["beta.py"]},
    }))

    async with await loader() as context:
        assert [handle.server_name for handle in context.sessions] == ["alpha"]
        assert context.errors == ["Failed to initialize MCP server 'beta': tool load failed"]

    assert _events == [
        ("enter", "alpha"),
        ("load", "alpha"),
        ("enter", "beta"),
        ("load", "beta"),
        ("exit", "beta"),
        ("exit", "alpha"),
    ]


def _write_config(tmp_path: Path, payload: dict) -> Path:
    path = tmp_path / "mcp.json"
    path.write_text(__import__("json").dumps(payload))
    return path
