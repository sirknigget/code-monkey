import pytest
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.tools import tool as lc_tool
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import ToolNode

from code_monkey.graph.agent_graph import AgentGraph
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

    def map_project_node(self, state: ChatbotState) -> dict:
        return {
            "messages": [AIMessage(content="[mock] project mapped")],
            "needs_mapping": False,
        }

    def orchestrator_node(self, state: ChatbotState) -> dict:
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

    def tool_node(self, state: ChatbotState) -> dict:
        return self._tool_node.invoke(state)


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
# invoke
# ---------------------------------------------------------------------------


def test_first_invocation_maps_project(agent):
    result = agent.invoke("hi")
    contents = [m.content for m in result["messages"]]
    assert contents == ["hi", "[mock] project mapped", "[mock] orchestrator decision"]


def test_subsequent_invocation_skips_mapping(agent):
    agent.invoke("hi")
    result = agent.invoke("hello")
    contents = [m.content for m in result["messages"]]
    assert contents == [
        "hi",
        "[mock] project mapped",
        "[mock] orchestrator decision",
        "hello",
        "[mock] orchestrator decision",
    ]


def test_force_mapping_remaps_after_first_run(agent):
    agent.invoke("hi")
    result = agent.invoke("hello", force_mapping=True)
    contents = [m.content for m in result["messages"]]
    assert contents == [
        "hi",
        "[mock] project mapped",
        "[mock] orchestrator decision",
        "hello",
        "[mock] project mapped",
        "[mock] orchestrator decision",
    ]


def test_tool_routing_subsequent_invoke_skips_tool_call(agent_with_tool_call):
    agent_with_tool_call.invoke("hi")
    result = agent_with_tool_call.invoke("hello")
    contents = [m.content for m in result["messages"]]
    assert contents == [
        "hi",
        "[mock] project mapped",
        "[mock] tool call",
        "[mock] tool result",
        "[mock] orchestrator decision",
        "hello",
        "[mock] orchestrator decision",
    ]


def test_mermaid_diagram_contains_all_nodes(agent):
    diagram = agent.get_mermaid_diagram()
    assert "map_project_node" in diagram
    assert "orchestrator_node" in diagram
    assert "tools" in diagram


# ---------------------------------------------------------------------------
# stream
# ---------------------------------------------------------------------------


def test_stream_first_invocation_yields_map_then_orchestrator(agent):
    contents = list(agent.stream("hi"))
    assert contents == ["[mock] project mapped", "[mock] orchestrator decision"]


def test_stream_subsequent_invocation_yields_orchestrator_only(agent):
    list(agent.stream("hi"))
    contents = list(agent.stream("hello"))
    assert contents == ["[mock] orchestrator decision"]


def test_stream_force_mapping_yields_map_then_orchestrator(agent):
    list(agent.stream("hi"))
    contents = list(agent.stream("hello", force_mapping=True))
    assert contents == ["[mock] project mapped", "[mock] orchestrator decision"]


def test_stream_tool_routing_skips_tool_call_messages(agent_with_tool_call):
    contents = list(agent_with_tool_call.stream("hi"))
    assert contents == [
        "[mock] project mapped",
        "[mock] tool result",
        "[mock] orchestrator decision",
    ]


# ---------------------------------------------------------------------------
# get_history
# ---------------------------------------------------------------------------


def test_get_history_empty_when_no_checkpoint(agent):
    assert list(agent.get_history()) == []


def test_get_history_returns_interleaved_user_and_assistant_messages(agent):
    agent.invoke("hi")
    history = list(agent.get_history())
    assert history == [
        ("user", "hi"),
        ("assistant", "[mock] project mapped"),
        ("assistant", "[mock] orchestrator decision"),
    ]


def test_get_history_accumulates_across_turns(agent):
    agent.invoke("hi")
    agent.invoke("hello")
    history = list(agent.get_history())
    assert history == [
        ("user", "hi"),
        ("assistant", "[mock] project mapped"),
        ("assistant", "[mock] orchestrator decision"),
        ("user", "hello"),
        ("assistant", "[mock] orchestrator decision"),
    ]


def test_get_history_omits_tool_call_messages(agent_with_tool_call):
    agent_with_tool_call.invoke("hi")
    history = list(agent_with_tool_call.get_history())
    assert history == [
        ("user", "hi"),
        ("assistant", "[mock] project mapped"),
        ("assistant", "[mock] tool result"),
        ("assistant", "[mock] orchestrator decision"),
    ]


# ---------------------------------------------------------------------------
# Real ToolNode execution with mock tools
# ---------------------------------------------------------------------------


def test_tool_node_executes_mock_tool_and_returns_result(agent_with_real_tool_node):
    result = agent_with_real_tool_node.invoke("search for something")

    tool_messages = [m for m in result["messages"] if isinstance(m, ToolMessage)]
    assert len(tool_messages) == 1
    assert tool_messages[0].content == "results for: test query"


def test_tool_node_result_feeds_back_to_orchestrator(agent_with_real_tool_node):
    result = agent_with_real_tool_node.invoke("search for something")

    contents = [m.content for m in result["messages"] if m.content]
    assert contents[-1] == "final answer"


def test_tool_node_tool_call_id_matches_tool_message(agent_with_real_tool_node):
    result = agent_with_real_tool_node.invoke("search for something")

    ai_msg = next(
        m for m in result["messages"] if isinstance(m, AIMessage) and m.tool_calls
    )
    tool_msg = next(m for m in result["messages"] if isinstance(m, ToolMessage))
    assert tool_msg.tool_call_id == ai_msg.tool_calls[0]["id"]
