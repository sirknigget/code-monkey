from abc import ABC, abstractmethod

from code_monkey.graph.nodes.map_project_node import map_project_node
from code_monkey.graph.nodes.orchestrator_node import orchestrator_node
from code_monkey.graph.nodes.tool_node import tool_node
from code_monkey.graph.state import ChatbotState


class NodesProvider(ABC):
    @abstractmethod
    def map_project_node(self, state: ChatbotState) -> dict:
        """Analyze and map the project structure."""

    @abstractmethod
    def orchestrator_node(self, state: ChatbotState) -> dict:
        """Route or coordinate between other nodes."""

    @abstractmethod
    def tool_node(self, state: ChatbotState) -> dict:
        """Execute tool calls from the last AI message."""

class DefaultNodesProvider(NodesProvider):
    def map_project_node(self, state: ChatbotState) -> dict:
        return map_project_node(state)

    def orchestrator_node(self, state: ChatbotState) -> dict:
        return orchestrator_node(state)

    def tool_node(self, state: ChatbotState) -> dict:
        return tool_node(state)
