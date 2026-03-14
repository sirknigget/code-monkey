import pytest
from langgraph.checkpoint.memory import MemorySaver

from code_monkey.graph.agent_graph import AgentGraph
from tests.graph.mock_nodes_provider import MockNodesProvider


@pytest.fixture
def agent():
    return AgentGraph(MockNodesProvider(), checkpointer=MemorySaver())


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


@pytest.fixture
def agent_with_tool_call():
    return AgentGraph(
        MockNodesProvider(emit_tool_call=True), checkpointer=MemorySaver()
    )


def test_tool_routing_routes_through_tools_node(agent_with_tool_call):
    result = agent_with_tool_call.invoke("hi")
    contents = [m.content for m in result["messages"]]
    assert contents == [
        "hi",
        "[mock] project mapped",
        "[mock] tool call",
        "[mock] tool result",
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


def test_stream_tool_routing_yields_all_messages(agent_with_tool_call):
    contents = list(agent_with_tool_call.stream("hi"))
    assert contents == [
        "[mock] project mapped",
        "[mock] tool call",
        "[mock] tool result",
        "[mock] orchestrator decision",
    ]
