from types import SimpleNamespace

import pytest
from langchain_core.tools import tool

from code_monkey.graph.default_nodes_provider import DefaultNodesProvider
from code_monkey.mcp.loader import MCPServerSessionHandle
from code_monkey.models.model_config import ModelConfig
from tests.e2e.conftest import FakeChatModel


@tool
async def alpha_tool() -> str:
    """Return a deterministic MCP tool response."""
    return "ok"


class _StubModelConfig(ModelConfig):
    def orchestrator_model(self):
        return FakeChatModel(responses=["done"])

    def summarizer_model(self):
        return FakeChatModel(responses=["summary"])

    def web_researcher_model(self):
        return FakeChatModel(responses=["research"])

    def chat_summarizer_model(self):
        return FakeChatModel(responses=["chat summary"])

    def tester_model(self):
        return FakeChatModel(responses=["{\"status\": \"passed\", \"reason\": \"\"}"])


@pytest.mark.asyncio
async def test_create_appends_injected_mcp_tools(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    captured = {}

    async def fake_create_web_researcher(*, model):
        return SimpleNamespace(teardown=_async_noop)

    def fake_make_orchestrator_node(model, tools):
        captured["tool_names"] = [tool.name for tool in tools]

        async def node(state, config):
            return {"messages": []}

        return node

    monkeypatch.setattr(
        "code_monkey.graph.default_nodes_provider.WebResearcher.create",
        fake_create_web_researcher,
    )
    monkeypatch.setattr(
        "code_monkey.graph.default_nodes_provider.make_orchestrator_node",
        fake_make_orchestrator_node,
    )

    mcp_session = MCPServerSessionHandle(
        server_name="alpha",
        tools=[alpha_tool],
        session=SimpleNamespace(),
    )

    await DefaultNodesProvider.create(
        str(tmp_path),
        _StubModelConfig(),
        mcp_sessions=[mcp_session],
    )

    assert captured["tool_names"] == [
        "web_search",
        "read_file",
        "write_file",
        "terminal",
        "alpha_tool",
    ]


async def _async_noop() -> None:
    return None
