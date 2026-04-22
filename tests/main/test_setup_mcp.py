from pathlib import Path
from types import SimpleNamespace
from typing import cast

import pytest
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from code_monkey.graph.checkpointer import CheckpointerResult
from code_monkey.main import setup
from code_monkey.mcp.loader import MCPClientContext
from tests.e2e.conftest import FakeModelConfig, MockUI


class _FakeConn:
    def __init__(self) -> None:
        self.closed = False

    async def close(self) -> None:
        self.closed = True


class _FakeCheckpointer:
    def __init__(self) -> None:
        self.conn = _FakeConn()


class _FakeMCPContext(MCPClientContext):
    def __init__(self, sessions, errors=None) -> None:
        super().__init__(sessions=sessions, errors=errors or [])
        self.entered = False
        self.exited = False

    async def __aenter__(self):
        self.entered = True
        return self

    async def __aexit__(self, exc_type, exc, tb):
        self.exited = True


@pytest.mark.asyncio
async def test_setup_uses_mcp_factory_and_forwards_sessions(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    captured = {}
    checkpointer = _FakeCheckpointer()
    mcp_sessions = [
        SimpleNamespace(
            server_name="alpha",
            tools=[
                SimpleNamespace(name="first_tool"),
                SimpleNamespace(name="second_tool"),
            ],
        )
    ]
    mcp_context = _FakeMCPContext(mcp_sessions)
    graph = SimpleNamespace(teardown=_async_noop)

    async def fake_checkpointer_factory() -> CheckpointerResult:
        return CheckpointerResult(checkpointer=cast(AsyncSqliteSaver, checkpointer))

    async def fake_mcp_factory():
        return mcp_context

    async def fake_graph_create(
        *, checkpointer, project_root, model_config, mcp_sessions, thread_id
    ):
        captured["checkpointer"] = checkpointer
        captured["project_root"] = project_root
        captured["mcp_sessions"] = mcp_sessions
        captured["thread_id"] = thread_id
        return graph

    async def fake_controller_run(self):
        return None

    monkeypatch.setattr("code_monkey.main.AgentGraph.create", fake_graph_create)
    monkeypatch.setattr("code_monkey.main.Controller.run", fake_controller_run)

    ui = MockUI([])
    await setup(
        project_root=str(tmp_path),
        ui=ui,
        checkpointer_factory=fake_checkpointer_factory,
        mcp_client_factory=fake_mcp_factory,
        model_config=FakeModelConfig(),
    )

    assert captured == {
        "checkpointer": checkpointer,
        "project_root": str(tmp_path),
        "mcp_sessions": mcp_sessions,
        "thread_id": str(tmp_path.resolve()),
    }
    assert mcp_context.entered is True
    assert mcp_context.exited is True
    assert checkpointer.conn.closed is True
    assert ui.system_messages() == [
        "Loaded MCP server: alpha\n\tTools: first_tool, second_tool",
        "Shutting down...",
    ]


async def _async_noop() -> None:
    return None
