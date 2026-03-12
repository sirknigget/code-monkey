import pytest

from code_monkey.graph.agent_graph import AgentGraph
from tests.graph.mock_nodes_provider import MockNodesProvider


@pytest.fixture
def agent():
    return AgentGraph(MockNodesProvider())


def test_routes_to_orchestrator_when_needs_mapping_false(agent):
    result = agent.invoke("hi", needs_mapping=False)
    contents = [m.content for m in result["messages"]]
    assert contents == ["hi", "[mock] orchestrator decision"]


def test_routes_to_map_project_then_orchestrator_when_needs_mapping_true(agent):
    result = agent.invoke("hi", needs_mapping=True)
    contents = [m.content for m in result["messages"]]
    assert contents == ["hi", "[mock] project mapped", "[mock] orchestrator decision"]


def test_mermaid_diagram_contains_all_nodes(agent):
    diagram = agent.get_mermaid_diagram()
    assert "map_project_node" in diagram
    assert "orchestrator_node" in diagram
    assert "tools" in diagram
