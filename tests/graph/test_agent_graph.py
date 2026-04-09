import pytest
from langchain_core.messages import AIMessage
from langchain_core.tools import tool as lc_tool
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import ToolNode

from langchain_core.runnables import RunnableConfig
from langgraph.types import StreamWriter

from code_monkey.agents.tester.tester import TesterResult
from code_monkey.graph.agent_graph import AgentGraph, StreamChunk
from code_monkey.graph.nodes.tester_node import MAX_REVIEW_CYCLES
from code_monkey.graph.nodes_provider import NodesProvider
from code_monkey.graph.state import ChatbotState
from tests.graph.mock_nodes_provider import MockNodesProvider


# ---------------------------------------------------------------------------
# Tool-call integration helpers
# ---------------------------------------------------------------------------


@lc_tool
def _mock_search(query: str) -> str:
    """Search for information."""
    return f"results for: {query}"


class _RealToolNodeProvider(NodesProvider):
    """Mock orchestrator + real ToolNode with _mock_search. Used to test tool execution."""

    def __init__(self) -> None:
        self._tool_node = ToolNode([_mock_search])
        self._tool_call_emitted = False

    async def map_project_node(
        self, state: ChatbotState, config: RunnableConfig
    ) -> dict:
        return {
            "messages": [AIMessage(content="[mock] project mapped")],
            "needs_mapping": False,
        }

    async def orchestrator_node(
        self, state: ChatbotState, config: RunnableConfig
    ) -> dict:
        if not self._tool_call_emitted:
            self._tool_call_emitted = True
            return {
                "messages": [
                    AIMessage(
                        content="",
                        tool_calls=[
                            {
                                "name": "_mock_search",
                                "args": {"query": "test query"},
                                "id": "call_test_1",
                                "type": "tool_call",
                            }
                        ],
                    )
                ]
            }
        return {"messages": [AIMessage(content="final answer")]}

    async def tool_node(self, state: ChatbotState) -> dict:
        return await self._tool_node.ainvoke(state)

    async def summarizer_node(
        self, state: ChatbotState, config: RunnableConfig
    ) -> dict:
        return {
            "chat_summary": state.get("chat_summary", ""),
            "last_messages": state.get("messages", []),
            "chat_summary_span": state.get("chat_summary_span", 0),
        }

    async def tester_node(
        self, state: ChatbotState, config: RunnableConfig, *, writer: StreamWriter
    ) -> dict:
        return {
            "tester_result": TesterResult(status="passed", reason=""),
            "tester_iteration_count": state.get("tester_iteration_count", 0) + 1,
            "review_feedback": None,
        }


@pytest.fixture
def agent():
    return AgentGraph(MockNodesProvider(), checkpointer=MemorySaver())


@pytest.fixture
def agent_with_tool_call():
    return AgentGraph(
        MockNodesProvider(emit_tool_call=True), checkpointer=MemorySaver()
    )


@pytest.fixture
def agent_with_real_tool_node():
    return AgentGraph(_RealToolNodeProvider(), checkpointer=MemorySaver())


# ---------------------------------------------------------------------------
# astream
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_first_invocation_maps_project(agent):
    chunks = []
    async for c in agent.astream("hi"):
        chunks.append(c)
    assert chunks == [
        StreamChunk(content="[mock] project mapped", kind="assistant"),
        StreamChunk(content="[mock] orchestrator decision", kind="assistant"),
    ]


@pytest.mark.asyncio
async def test_subsequent_invocation_skips_mapping(agent):
    async for _ in agent.astream("hi"):
        pass
    chunks = []
    async for c in agent.astream("hello"):
        chunks.append(c)
    assert chunks == [StreamChunk(content="[mock] orchestrator decision", kind="assistant")]


@pytest.mark.asyncio
async def test_trigger_mapping_remaps_after_first_run(agent):
    async for _ in agent.astream("hi"):
        pass
    await agent.trigger_mapping()
    chunks = []
    async for c in agent.astream("hello"):
        chunks.append(c)
    assert chunks == [
        StreamChunk(content="[mock] project mapped", kind="assistant"),
        StreamChunk(content="[mock] orchestrator decision", kind="assistant"),
    ]


@pytest.mark.asyncio
async def test_tool_routing_yields_tool_result_then_orchestrator(agent_with_tool_call):
    chunks = []
    async for c in agent_with_tool_call.astream("hi"):
        chunks.append(c)
    assert chunks == [
        StreamChunk(content="[mock] project mapped", kind="assistant"),
        StreamChunk(content="[mock] tool result", kind="assistant"),
        StreamChunk(content="[mock] orchestrator decision", kind="assistant"),
    ]


@pytest.mark.asyncio
async def test_tool_routing_subsequent_invocation_skips_tool_call(agent_with_tool_call):
    async for _ in agent_with_tool_call.astream("hi"):
        pass
    chunks = []
    async for c in agent_with_tool_call.astream("hello"):
        chunks.append(c)
    assert chunks == [StreamChunk(content="[mock] orchestrator decision", kind="assistant")]


def test_mermaid_diagram_contains_all_nodes(agent):
    diagram = agent.get_mermaid_diagram()
    assert "map_project_node" in diagram
    assert "orchestrator_node" in diagram
    assert "tools" in diagram
    assert "summarizer_node" in diagram
    assert "tester_node" in diagram


# ---------------------------------------------------------------------------
# aget_history
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_history_empty_when_no_checkpoint(agent):
    history = []
    async for item in agent.aget_history():
        history.append(item)
    assert history == []


@pytest.mark.asyncio
async def test_get_history_returns_interleaved_user_and_assistant_messages(agent):
    async for _ in agent.astream("hi"):
        pass
    history = []
    async for item in agent.aget_history():
        history.append(item)
    assert history == [
        ("user", "hi"),
        ("assistant", "[mock] project mapped"),
        ("assistant", "[mock] orchestrator decision"),
    ]


@pytest.mark.asyncio
async def test_get_history_accumulates_across_turns(agent):
    async for _ in agent.astream("hi"):
        pass
    async for _ in agent.astream("hello"):
        pass
    history = []
    async for item in agent.aget_history():
        history.append(item)
    assert history == [
        ("user", "hi"),
        ("assistant", "[mock] project mapped"),
        ("assistant", "[mock] orchestrator decision"),
        ("user", "hello"),
        ("assistant", "[mock] orchestrator decision"),
    ]


@pytest.mark.asyncio
async def test_get_history_omits_tool_call_messages(agent_with_tool_call):
    async for _ in agent_with_tool_call.astream("hi"):
        pass
    history = []
    async for item in agent_with_tool_call.aget_history():
        history.append(item)
    assert history == [
        ("user", "hi"),
        ("assistant", "[mock] project mapped"),
        ("assistant", "[mock] tool result"),
        ("assistant", "[mock] orchestrator decision"),
    ]


# ---------------------------------------------------------------------------
# Real ToolNode execution with mock tools
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_tool_node_executes_mock_tool_and_returns_result(
    agent_with_real_tool_node,
):
    chunks = []
    async for c in agent_with_real_tool_node.astream("search for something"):
        chunks.append(c)
    assert chunks == [
        StreamChunk(content="[mock] project mapped", kind="assistant"),
        StreamChunk(content="final answer", kind="assistant"),
    ]


@pytest.mark.asyncio
async def test_tool_node_result_feeds_back_to_orchestrator(agent_with_real_tool_node):
    chunks = []
    async for c in agent_with_real_tool_node.astream("search for something"):
        chunks.append(c)
    assert chunks[-1] == StreamChunk(content="final answer", kind="assistant")


# ---------------------------------------------------------------------------
# Tester routing integration tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_orchestrator_finishes_routes_through_tester_to_end():
    agent = AgentGraph(MockNodesProvider(tester_fails_times=0), checkpointer=MemorySaver())
    chunks = []
    async for c in agent.astream("hello"):
        chunks.append(c)
    assistant_chunks = [c for c in chunks if c.kind == "assistant"]
    warning_chunks = [c for c in chunks if c.kind == "warning"]
    assert any(c.content == "[mock] orchestrator decision" for c in assistant_chunks)
    assert warning_chunks == []


@pytest.mark.asyncio
async def test_tester_fails_once_routes_back_to_orchestrator():
    agent = AgentGraph(
        MockNodesProvider(
            tester_fails_times=1,
            orchestrator_responses=["First attempt.", "Second attempt."],
        ),
        checkpointer=MemorySaver(),
    )
    chunks = []
    async for c in agent.astream("hello"):
        chunks.append(c)
    assistant_chunks = [c for c in chunks if c.kind == "assistant"]
    warning_chunks = [c for c in chunks if c.kind == "warning"]
    contents = [c.content for c in assistant_chunks]
    assert "First attempt." in contents
    assert "Second attempt." in contents
    assert warning_chunks == []


@pytest.mark.asyncio
async def test_tester_fails_max_cycles_graph_terminates():
    agent = AgentGraph(
        MockNodesProvider(tester_fails_times=MAX_REVIEW_CYCLES),
        checkpointer=MemorySaver(),
    )
    chunks = []
    async for c in agent.astream("hello"):
        chunks.append(c)
    checkpoint = await agent._checkpointer.aget(agent._thread_config)
    assert checkpoint is not None
    tester_iteration_count = checkpoint["channel_values"].get("tester_iteration_count", 0)
    assert tester_iteration_count >= MAX_REVIEW_CYCLES
    warning_chunks = [c for c in chunks if c.kind == "warning"]
    assert len(warning_chunks) == 1
    assert warning_chunks[0].content.startswith("Max review cycles")


@pytest.mark.asyncio
async def test_tool_call_path_tester_runs_after_final_orchestrator_response():
    agent = AgentGraph(
        MockNodesProvider(emit_tool_call=True, tester_fails_times=0),
        checkpointer=MemorySaver(),
    )
    chunks = []
    async for c in agent.astream("hello"):
        chunks.append(c)
    assistant_contents = [c.content for c in chunks if c.kind == "assistant"]
    assert "[mock] project mapped" in assistant_contents
    assert "[mock] tool result" in assistant_contents
    assert "[mock] orchestrator decision" in assistant_contents
