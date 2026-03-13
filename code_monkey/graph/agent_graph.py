from typing import cast

from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import tools_condition

from code_monkey.graph.nodes_provider import NodesProvider
from code_monkey.graph.state import ChatbotState


class AgentGraph:
    _THREAD_CONFIG: RunnableConfig = {"configurable": {"thread_id": "session"}}

    def __init__(
        self, nodes_provider: NodesProvider, checkpointer: BaseCheckpointSaver
    ) -> None:
        self._checkpointer = checkpointer
        self._graph = self._build(nodes_provider, checkpointer)

    def invoke(self, message: str, force_mapping: bool = False) -> dict:
        is_new_session = self._checkpointer.get(self._THREAD_CONFIG) is None
        state: ChatbotState = {
            "messages": [HumanMessage(content=message)],
            "needs_mapping": force_mapping or is_new_session,
            "review_feedback": None,
            "iteration_count": 0,
        }
        return self._graph.invoke(state, config=self._THREAD_CONFIG)

    def get_mermaid_diagram(self) -> str:
        return self._graph.get_graph().draw_mermaid()

    @staticmethod
    def _build(
        nodes_provider: NodesProvider, checkpointer: BaseCheckpointSaver
    ) -> CompiledStateGraph:
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

        return graph.compile(checkpointer=checkpointer)
