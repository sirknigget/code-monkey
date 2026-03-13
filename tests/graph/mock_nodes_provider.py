from langchain_core.messages import AIMessage

from code_monkey.graph.nodes_provider import NodesProvider
from code_monkey.graph.state import ChatbotState


class MockNodesProvider(NodesProvider):
    def map_project_node(self, state: ChatbotState) -> dict:
        return {
            "messages": [AIMessage(content="[mock] project mapped")],
            "needs_mapping": False,
        }

    def orchestrator_node(self, state: ChatbotState) -> dict:
        return {"messages": [AIMessage(content="[mock] orchestrator decision")]}

    def tool_node(self, state: ChatbotState) -> dict:
        return {"messages": [AIMessage(content="[mock] tool result")]}
