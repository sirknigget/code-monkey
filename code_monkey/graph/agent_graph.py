from typing import cast

from langchain_core.messages import HumanMessage
from langgraph.graph import START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import tools_condition

from code_monkey.graph.nodes_provider import NodesProvider
from code_monkey.graph.state import ChatbotState


class AgentGraph:
    def __init__(self, nodes_provider: NodesProvider) -> None:
        self._graph = self._build(nodes_provider)

    def invoke(self, message: str, needs_mapping: bool = False) -> dict:
        state: ChatbotState = {
            "messages": [HumanMessage(content=message)],
            "needs_mapping": needs_mapping,
            "review_feedback": None,
            "iteration_count": 0,
        }
        return self._graph.invoke(state)

    def get_mermaid_diagram(self) -> str:
        return self._graph.get_graph().draw_mermaid()

    @staticmethod
    def _build(nodes_provider: NodesProvider) -> CompiledStateGraph:
        graph = StateGraph(ChatbotState)

        graph.add_node("map_project_node", nodes_provider.map_project_node)
        graph.add_node("orchestrator_node", nodes_provider.orchestrator_node)
        graph.add_node("tools", nodes_provider.tool_node)

        graph.add_conditional_edges(
            START,
            lambda state: (
                "map_project_node"
                if cast(ChatbotState, state)["needs_mapping"]
                else "orchestrator_node"
            ),
        )
        graph.add_edge("map_project_node", "orchestrator_node")
        graph.add_conditional_edges("orchestrator_node", tools_condition)
        graph.add_edge("tools", "orchestrator_node")

        return graph.compile()
