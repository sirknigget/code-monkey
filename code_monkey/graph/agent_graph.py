from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import tools_condition

from code_monkey.graph.nodes_provider import NodesProvider
from code_monkey.graph.state import ChatbotState


class AgentGraph:
    def __init__(self, nodes_provider: NodesProvider) -> None:
        self._nodes_provider = nodes_provider

    def build_graph(self) -> CompiledStateGraph:
        graph = StateGraph(ChatbotState)

        graph.add_node("orchestrator_node", self._nodes_provider.orchestrator_node)
        graph.add_node("tool_node", self._nodes_provider.tool_node)

        graph.add_edge(START, "orchestrator_node")
        graph.add_conditional_edges("orchestrator_node", tools_condition, {"tools": "tool_node", END: END})
        graph.add_edge("tool_node", "orchestrator_node")

        return graph.compile()
