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


def test_mermaid_diagram_contains_all_nodes(agent):
    diagram = agent.get_mermaid_diagram()
    assert "map_project_node" in diagram
    assert "orchestrator_node" in diagram
    assert "tools" in diagram
